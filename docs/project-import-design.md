# Project import: structure detection and reusable layouts

Status: draft proposal. Nothing here is implemented.

## 1. Problem

Phonlab currently opens a project directory by globbing `*` (non-recursive) for
`.wav` files and pairing each with a same-stem `.TextGrid`
(`MainWindow.select_project_to_open`). That handles exactly one layout: a flat
folder of `.wav` + `.TextGrid` pairs.

Real phonetics corpora are organized in many other ways:

- one folder per talker, or nested folders (split / dialect / talker);
- metadata packed into file names (`s0101a.wav`);
- audio and annotations in parallel trees (`audio/…`, `annotations/…`);
- legacy annotation formats (Buckeye `.words`/`.phones`, TIMIT `.WRD`/`.PHN`);
- several talkers in a single TextGrid.

We want to detect the structure of a project, ask the user a small number of
well-targeted questions while building `phonlab.db`, and **save a description of
the structure** so the project can be re-imported or extended later without
repeating the conversation.

### Goals

1. Recursive import of projects whose layout is a tree of folders, with audio
   and annotation files paired by rule.
2. Extract per-recording metadata ("fields", e.g. `talker`, `dialect`,
   `sentence`) from folder names, file names, and tier names.
3. Read legacy annotation formats (Buckeye, TIMIT first) into phonlab's existing
   tier model.
4. Infer as much as possible; ask only about what cannot be inferred; show
   evidence with every question.
5. Persist the confirmed layout in a human-readable file and re-validate it when
   the project is reopened or files are added.

### Non-goals

- Reproducing polyglotDB's linguistic hierarchy (word/phone containment, type vs
  token properties). Phonlab stores tiers of labeled intervals; that is enough.
- Importing annotations that have no audio.
- Supporting every format polyglotDB does on day one (ILG, plain text,
  LaBB-CAT). The reader interface should make them easy to add later.

## 2. What polyglotDB does

Source: `MontrealCorpusTools/PolyglotDB`, `polyglotdb/io/` (`parsers/`,
`inspect/`, `helper.py`). Every importer there is the combination of three
separable decisions, even though the classes blur them.

### 2.1 Format reader

`TextgridParser`, `BuckeyeParser`, `TimitParser`, `PartiturParser`, `IlgParser`,
text parsers, and the aligner dialects (`MfaParser`, `FaveParser`, `MausParser`,
`LabbCatParser`, all subclasses of `AlignerParser`, which is itself a
`TextgridParser`). Aligner dialects differ only in the tier-name conventions
they look for (`word_label` / `phone_label`) and where the speaker lives.

Legacy formats read sibling files by swapping the extension:

| Format  | Primary ext        | Companion       | Notes                                              |
| ------- | ------------------ | --------------- | -------------------------------------------------- |
| Buckeye | `.words`           | `.phones`, `.wav` | Header ends at `#`; times are end-of-interval only |
| TIMIT   | `.WRD` / `.wrd`    | `.PHN`, `.WAV`  | Times in samples; polyglotDB hardcodes 16 kHz      |
| Partitur| `.par,2`           | —               | Words and phones in one file                       |

### 2.2 Speaker rule

Only two schemes exist (`parsers/speaker.py`):

- `FilenameSpeakerParser(n, left=True)`: first/last *n* characters of the stem.
  Buckeye `s0101a` with n=3 gives `s01`.
- `DirectorySpeakerParser`: name of the immediate parent folder. Used for TIMIT,
  Partitur, LaBB-CAT and the aligner base class.

Plus a third source inside the file: multi-speaker aligner TextGrids name tiers
`Speaker - words` (or `words - Speaker` when `speaker_first=False`), and the
speaker can map to a channel of a multi-channel wav.

Gaps: only *one* field is ever extracted. Real TIMIT is
`TRAIN/DR1/FCJF0/SA1.WAV`; the dialect region (`DR1`) and the sentence ID are
lost. Buckeye's session number and part letter are lost.

### 2.3 Detection heuristics

- `inspect_directory`: walk the tree, count extensions, majority wins
  (`.textgrid`, `.txt`, `.words`, `.wrd`, `.par,2`).
- `guess_textgrid_format`: sniff tier names for aligner dialects
  (`word`/`phone`, the ` - ` separator, `transcript`/`segment`, `ort`/`mau`).
- `guess_tiers`: classify a tier as words or phones by mean interval duration
  against a Gaussian fitted to Buckeye (words ≈ 0.25 s, phones ≈ 0.083 s).
- `guess_type`: classify label content (numeric, delimiter-separated
  transcription, ToBI characters, morphemes, orthography).

### 2.4 Weaknesses to avoid

- The first file's structure is assumed for all files; tiers are matched by
  index; a file with a different tier count aborts the import.
- Duration priors are from English conversational speech.
- Hardcoded sample rate for TIMIT.
- Empty TextGrids are skipped silently.
- The inferred "spec" is a live parser object; it is never serialized, and there
  is no user-facing question step (it is a library API).
- Parallel-tree layouts (GlobalPhone's `spk/ adc/ trl/ rmn/` in the test data)
  have no parser at all.

## 3. Proposed design

Approach: **infer, preview, correct, persist.** The central UI is a *preview
table* rather than a series of abstract questions: one row per recording, one
column per derived field. The user edits column labels and split points and the
table updates live. Specific questions (§3.3) only appear when inference is
ambiguous.

### 3.1 Core model

All of this lives in `core/` as dataclasses plus use cases (see §5).

- **`ProjectScan`**: inventory of the tree: every file with relative path,
  case-folded extension, directory depth, size. Cheap; no parsing of contents.
- **`Recording`**: one logical item to import: an audio file plus zero or one
  annotation file group (e.g. `.words` + `.phones` is one group).
- **`FieldSource`**: where a field's value comes from: `folder(depth)`,
  `filename(span or template group)`, `tier_name(group)`, or `manual`.
- **`ProjectLayout`**: the confirmed description:
  - how audio and annotations are paired (`sibling`, `parallel_tree`, `by_id`);
  - annotation format (`textgrid`, `buckeye`, `timit`, …) and extensions;
  - folder-level roles (depth → field name, or `ignore`);
  - filename template and its compiled regex;
  - tier policy (which tiers to include, how to name them);
  - a *fingerprint* (shape clusters, tier signatures) used for validation.

### 3.2 Pipeline

#### Step 1: Scan and pair

Walk the tree recursively. Pair audio with annotations by trying, in order:

1. same directory, same stem;
2. same stem in a different directory (parallel trees);
3. normalized stem: case-folded, known extension variants (`.WRD`/`.wrd`);
4. join by an extracted ID (only after the user defines a filename template).

If pairing is incomplete, report counts and lists, e.g. "47 wavs have no
annotation; 3 annotations have no wav", and let the user proceed, exclude, or
change the pairing rule.

#### Step 2: Detect annotation format

Extension sets give a first guess (`.words`+`.phones` → Buckeye,
`.WRD`+`.PHN` → TIMIT, `.TextGrid` → TextGrid). For TextGrids, sniff tier names
for aligner dialects and multi-speaker (` - `) conventions. Recognized corpora
load a **preset** (a prebuilt `ProjectLayout`) and skip most questions.

#### Step 3: Folder levels

Compute for each depth: number of distinct folder names, files per folder, and
sample names. Present them in a compact table and ask what each level means.
Defaults:

- the deepest folder level with many values and few files each → `talker`;
- shallow levels with few values → a grouping variable (user supplies the name);
- a level whose names are a prefix of the file names → `talker`, with the
  redundancy shown as confirming evidence.

Options per level: `talker`, a custom field name (`dialect`, `condition`,
`session`, …), or `ignore` (organizational only).

#### Step 4: Filename fields

Tokenize each stem into runs of character classes and delimiters (`s0101a` →
`s`, `0101`, `a`). Cluster stems by shape. If one shape covers most files,
propose a split and list the outliers. The user can define fields three ways,
in order of preference:

1. **Select to label.** Show a real filename; the user highlights a span and
   names it (`s01` → `talker`). Generalized to the other files by position or
   delimiter, and checked against the outliers.
2. **Template.** A small syntax: `{talker:3}{session:2}{part}`,
   `{talker}_{item}`, `{*}` as a wildcard. Fixed-width and delimited fields
   cover most corpora and map directly onto "xxxyyy where xxx is the talker".
3. **Regex** (advanced). Named groups, with live match / non-match counts.

Internally all three compile to a regex with named groups, which is also what
is stored. Regex is the storage and interchange form, not the primary UI.
A fourth route, programming by example ("type the talker for this one file"),
can be added later on top of select-to-label.

#### Step 5: Tiers

Group files by tier-name signature and report clusters instead of failing on
the first mismatch: "38 files have [words, phones]; 4 have [words, phones,
notes]. Include `notes`?" Name-based hints (`word`, `phone`, `segment`, …) come
first; interval-duration statistics are only a tiebreaker. For multi-speaker
TextGrids, the speaker field's source is the tier name.

#### Step 6: Confirm, import, persist

Show the final preview table plus a summary (N recordings, M with
annotations, fields found). On confirmation, write the layout to
`phonlab.toml` and build `phonlab.db`.

### 3.3 Question catalog

Each question shows its evidence and has a default that Enter accepts.

| # | Question | Shown when | Evidence shown |
|---|----------|------------|----------------|
| Q1 | Unpaired files: proceed, exclude, or change pairing? | any orphan audio/annotation | counts, example paths |
| Q2 | What does each folder level represent? | ≥1 folder level above the files | distinct count, examples, files per folder |
| Q3 | How should file names be split into fields? | stems share a dominant shape | highlighted examples, outliers |
| Q4 | Which tiers should be included / what are they? | tier signatures differ or roles unclear | signature clusters, file counts |
| Q5 | Multi-speaker TextGrids: which tier part is the speaker? | ` - ` in tier names | example tier names |
| Q6 | Is this a known corpus layout (Buckeye, TIMIT, MFA output)? | preset signature matches | matched extensions / tier names |

### 3.4 Worked examples

**Flat (today's layout).** `rec1.wav`, `rec1.TextGrid`. Sibling pairing,
no folder levels, one dominant stem shape with no obvious split. No questions
except optional Q3.

**Buckeye.** `s01/s0101a.wav`, `.words`, `.phones`. Preset detected from the
extension set. Folder level 1 = `talker` and the filename prefix `s01` agrees;
the template `{talker:3}{session:2}{part}` captures session and part as extra
fields.

**TIMIT.** `TRAIN/DR1/FCJF0/SA1.WAV` (+`.WRD`, `.PHN`, `.TXT`). Preset detected.
Levels: `split`, `dialect`, `talker`; filename `{sentence}`. Sample rate read
from the wav header, not hardcoded.

**MFA output.** `speaker/utt.TextGrid` with `words`/`phones` tiers, audio in a
separate tree. Parallel-tree pairing; folder level = `talker`.

**GlobalPhone-style.** `adc/001/AA001_1.adc.wav` with transcripts in `trl/` and
speaker info in `spk/`. Pairing by extracted ID after a Q3 template. This is
the case polyglotDB does not cover and the reason pairing rule 4 exists.

## 4. Persistence

### 4.1 Layout file

`phonlab.toml` already exists at the project root. Add an `[import]` section
(sketch; exact keys to be settled in review):

```toml
[import]
version = 1
preset = "custom"                 # buckeye | timit | mfa | flat | custom

[import.pairing]
rule = "sibling"                  # sibling | parallel_tree | by_id
audio_ext = [".wav"]
annotation_ext = [".TextGrid"]

[import.annotation]
format = "textgrid"               # textgrid | buckeye | timit
tiers = { include = ["words", "phones"] }

[[import.levels]]
depth = 1
field = "dialect"

[[import.levels]]
depth = 2
field = "talker"

[import.filename]
template = "{sentence}"
regex = "(?P<sentence>[A-Z]+\\d+)"

[import.fingerprint]
# shape clusters and tier signatures captured at import time
```

### 4.2 Re-validation

On reopen, or when new files appear, rescan and compare to the fingerprint:
"11 of 12 new files match the layout; 1 does not" with an option to adjust the
layout or exclude the file. Never import non-matching files silently.

### 4.3 Database

Store derived fields as key/value rows per annotation, so user-defined
variables need no schema change and can later drive filtering, grouping, and
export:

```
annotation_attribute(annotation_id, name, value, source)
-- source ∈ {folder, filename, tier, manual}
```

`AnnotationEntity.file_stem` is already a unique relative path stem, which
works for recursive import (stems include subfolders).

## 5. Architecture placement

Per `ARCHITECTURE.md` and `CLAUDE.md`:

- `core/` has no UI dependency. New feature folders, grouped by feature with
  dataclasses in `entity/`:
  - `core/project_layout/`: `ScanProject`, `InferLayout`, `ApplyLayout` use
    cases; `ProjectScan`, `Recording`, `ProjectLayout`, `FieldSource` entities;
    the template compiler and matcher.
  - `core/parse_buckeye/`, `core/parse_timit/`: readers alongside the existing
    `core/parse_textgrid/`, each producing the same `Annotation` /
    `AnnotationType` / `AnnotationLabel` structures.
- `ui/` maps `ProjectLayout` to a `-State` class at the view-model boundary;
  the wizard (a dialog owned by the project-open view under
  `ui/main/component/`) never sees core entities. Data flows up through the
  view model's single `state_changed` signal.
- Constants and defaults (shape-cluster thresholds, preset names) go in
  `res/constants.py`.
- All user-facing strings go through `self.tr()`.
- `MainWindow` should only launch the wizard and receive the result; the logic
  belongs in the view model and `core`.

## 6. Delivery plan

Small, mechanical PRs (< ~400 lines each), each with tests mirroring `src`:

1. Scanner and layout entities (`ProjectScan`, `ProjectLayout`).
2. Template compiler and matcher (template → named-group regex, preview rows).
3. Pairing rules and orphan reporting.
4. Folder-level and filename-shape inference.
5. Buckeye reader, then TIMIT reader (sample rate from the wav).
6. Layout persistence in `phonlab.toml`; DB `annotation_attribute` table.
7. Wizard UI and preview table.
8. Fingerprint validation on reopen.

Any file moves or renames go in their own commits.

## 7. Open questions

- Should folder levels and filename fields share one field namespace, and what
  happens when both define `talker` and disagree? (Proposal: warn, and let the
  user choose the authoritative source.)
- Is `talker` special-cased (e.g. for per-talker defaults later), or just a
  conventionally named field?
- Where do user-wide presets live (shared across projects), if at all?
- Multi-channel audio with talker-per-channel: in scope for the first version?
- Should the layout live in `phonlab.toml` or a separate `phonlab.layout.toml`
  so it can be shared between projects without the rest of the config?
- How to handle projects whose layout changes partway (e.g. two collection
  batches with different conventions): multiple layouts per project, or one
  layout per sub-tree?

## 8. Risks

- Heuristics over-asking or under-asking. Mitigation: always show the preview
  table; keep every inference overridable.
- Template/regex input errors. Mitigation: live match counts and outlier lists
  before accepting.
- Large corpora (TIMIT ≈ 6,300 utterances; Buckeye ≈ 300k words). The scan must
  not parse file contents; content sniffing samples a bounded number of files.
- Legacy format quirks (Buckeye header parsing and misparsed lines, TIMIT
  sample-based times). Mitigation: port behavior from polyglotDB's readers
  deliberately, with fixtures from small, redistributable samples.

## 9. Implementation notes (first version)

What was built, and where it differs from the sketch above:

- `core/project_layout/`: `ScanProject`, `InferLayout`, `ResolveRecordings`,
  `ImportRecordings`, `LoadProjectLayout` / `SaveProjectLayout`, the filename
  template compiler and the audio-to-file pairing (`pairing.py`).
- `core/read_tiers/`: one `read_tiers()` for TextGrid, Buckeye (`.words` +
  `.phones`) and TIMIT (`.wrd` + `.phn`). `ParseTextGrid` uses it, so legacy
  files open like TextGrids. Buckeye's citation, surface and part-of-speech
  fields are not kept; only `word` and `phone` tiers are.
- Recordings live in the existing `annotation` table, in new columns:
  `audio_file`, `annotation_file`, `data_files` (JSON: kind of file → path),
  `talkers` (JSON list) and `fields` (JSON: variable → value). Paths are relative
  to the project directory. The old database file is not migrated; delete an
  existing `phonlab.db` made by an earlier version.
- Annotations are still read from their files when a recording is first opened, not
  at import. `ParseTextGrid` fills the empty row the import made.
- Files other than audio and annotations that share a recording's name (the same
  stem, or the stem plus a suffix such as `_f0`) are offered as "other files for
  each recording". Kinds that most recordings have are ticked by default.
  Audio without an annotation is reported, and can be left out.
- The layout is saved under `[import]` in `phonlab.toml`. A later import with a
  saved layout asks nothing unless file names stop fitting the template.
  **File > Project Layout…** reopens the questions.
- **Recordings stored as one audio file per channel** (`a_L.wav`, `a_R.wav`):
  audio files in one folder that differ only by a repeating ending are offered as the
  channels of one recording. They are offered only when the file headers say they could
  be (mono, same length and rate), and numbered endings (`_01`, `_02`) only when the
  headers show channels, so numbered items are not mistaken for channels. The user
  confirms, and can name the talker on each channel; names are offered from the tier
  names of a paired TextGrid (`Ann - words`, `words - Ann`, or tiers named for
  talkers). The annotation and data files pair with the base name (`a`). Such a
  recording opens as one document with a channel per file.
- **Database tables.** The table of recordings is called `recording` (one row per
  recording: `file_stem`, `audio_file`, `annotation_file`, `data_files`, `fields`, plus
  any columns added from CSV files). Who is in a recording is not a column: it is in
  `recording_talker`, a link table with a row for each recording and talker, pointing at
  the `talker` table (one row per talker, plus the information added about talkers). The
  channels of a recording stored as one file per channel are rows of `recording_channel`
  (channel label, audio file, and the talker on it), so recordings stored as one file
  have no channel columns. The table itself is only created when a recording with
  channel files is first added; a project without any does not have it.
- **Project > Add New Files… > talkers** adds columns to the talker table (one row per
  talker). SQLite adds a column to a
  table that already has rows, so nothing has to be known at import time. The key
  column is found by trying every column; rows that link to nothing are listed, and the
  user is asked before the rest are added. Adding the same column names again updates
  the values. An "i" button explains how to prepare the file.
- **File > Inspect Project Database…** is a read-only window onto every table, with a
  filter, to check what was imported and added. Columns that point at another table show
  a readable value: the file stem of a recording, the name of a talker or of a tier, the
  time of a node, not their row numbers.
- Not done yet: select-to-label for file names, the fingerprint check beyond
  template mismatches, and any viewer for the data files.

### How this fits the project database code on `dev`

`dev` already builds the project database (`core/project`: `AddProjectFiles`,
`RebuildProject`, with a progress dialog), so the layout code feeds it rather than
importing on its own:

- The layout wizard (**Project > Project Layout…**, and automatically when a *new*
  project is opened) only decides how the project is organized and saves it in
  `phonlab.toml`. It does not open the project database, so cancelling it leaves no
  `phonlab.db` behind.
- `scan_project_files` reads the project through that layout (the saved one, or the one
  the project appears to have) and attaches a `Recording` to each `ProjectFile`.
  `AddProjectFiles` stores the recordings next to the annotations when it registers file
  stems, so **Add New Files** and **Rebuild Project** follow the layout too.
- **Rebuild Project** starts a new database, so the columns added from CSV files would
  be lost. Each time information is added from a CSV file, the project file remembers the
  file (relative to the project when it is inside it), what its rows are about, the key
  column and the columns chosen, under `information` in `phonlab.toml`. Rebuilding adds
  that information again as its last step, from the files as they are now. A file that is
  missing, has lost its key column, or no longer matches any talker or recording is
  reported in the rebuild message, and the others are still added.

## Later additions

- **Ignored parts of file names.** `(ignore)` in a filename template allows anything,
  or nothing, at that position and keeps none of it, so `{talker:7}(ignore)` reads both
  `S24-002.wav` and `S24-002-1.wav` as talker `S24-002`. It can go anywhere in the template.
- **Choosing where annotations are read from.** When several top-level folders hold
  annotation files of the same recordings (versions of the TextGrids, say), the wizard
  offers them in a "Read them from" list and the choice is saved as `annotation_dir` in
  `[import]`. Annotation files outside that folder are ignored. Folders that hold
  different recordings are not a choice and nothing is asked.
- **Progress while the database is built.** Importing a new project and rebuilding one
  both show a progress box ("Importing/Rebuilding the project database") from the start:
  looking through the files, recording them, then "Reading annotations: n of N done" with the
  file being read, and adding the remembered CSV information. The scan runs in the
  background task so the window is never silent.
- **Duplicate audio warning.** Audio files with the same name, in different folders, and
  the same non-zero size are reported in the wizard as likely copies. Nothing is left
  out; each is a recording of its own, and the user is told so.
- **Import speed.** Reading one large TextGrid (about 70,000 nodes) did a database query
  for every node time, and again for every node written. Nodes are now read once per
  annotation and kept after the commit, label lookups no longer copy the node lists for
  each label, and SQL logging is off unless `PHONLAB_SQL_ECHO=1` is set.
- **Removed: filename-shape suggestion.** The wizard no longer clusters file names by
  shape, shows the most common shapes, or offers a "Use suggestion" template; the
  template is typed by the user. The sections above that describe shape clustering
  are the original design, not what is built.
- **Extra files that hold tiers.** Each kind of extra file in the wizard has a Kind
  (Annotation, Time series data, Other; the default is Other) and, for an annotation, a
  tier name (the kind's name if left empty). The choice is saved with the data file
  kinds in `[import]`. Files of annotation kind are put in `Recording.tier_files`, not in
  `data_files`, and a recording that has one counts as annotated. Reading those files
  into tiers is a later step: until then they are only found and counted.
- **Reading tier files.** Files of annotation kind are read when the project database is
  built or rebuilt: each becomes a tier named by the wizard, next to the tiers of the
  TextGrid if the recording has one. How a file is read as a table is worked out from it,
  not from any one corpus's format, and the user can correct it in a popup that opens when
  Annotation is chosen (and from the Columns button): the delimiter (tab, comma or spaces),
  the lines before the data (a header, a row of column names), what each column is (start
  time, end time, label, unknown) and the unit of the times. The choice is saved with the
  kind of file in `[import]`.
  - A column is a time if it is all non-negative numbers within the length of the audio
    file, in seconds or in milliseconds (the unit is whichever fits; seconds if both do).
    The time column with the smallest values is the start, and the one with the largest is
    the end if it is never below the start; others are unknown.
  - With only a start column, each label ends where the next begins and the last at the
    end of the audio. The label is the first column that is not a time (a text one if
    there is one); with spaces as the delimiter the label may have spaces, being the rest
    of the line. Sample numbers (TIMIT) and labels made of sub-columns (Buckeye) are not
    supported in tables.
  - The heading of the label column in the popup is the name of the tier: what the user
    typed in the wizard's Tier name box, else what the file calls the column (when its
    first line names the columns), else the name of the kind of file. Double-clicking the
    heading changes it. Times are always stored in seconds, whatever the file's unit.
  - A label is attached to the node nearest its time, so a tier whose times differ by a
    hair from another's (a sentence beginning where a word does) shares its node.
- **Project > Add New Files…** opens a dialog with four choices.
  - *New annotations*: reads the TextGrids that are not in the database yet, and adds the
    audio files they belong to (as laid out in the project's import description).
  - *Replacement annotations*: the user chooses TextGrids in a file dialog (all of them is
    like a rebuild that keeps the rest of the database), and the database's annotations
    for them are replaced. A chosen file that is no recording's TextGrid is reported and
    left out.
  - *Talkers*: the table import for talkers, without asking what the rows are about; its
    columns become columns of the talker table, and the match with the project's talkers
    is reported.
  - *Words*: a table with the words in its first column and a row of column names. The
    user says which tier has the words (`word` is chosen if there is one); the table is
    compared with the label text of that tier, letter for letter. The dialog says how many
    of the tier's words the table has and offers to save the others (word, count). The
    table becomes the `word` table of the database (replacing one it has, and made only
    when words are first added), with a column for each other column of the file, as
    numbers when all its values are. The file is remembered in `[words]` of the project
    file and the table is made again when the database is rebuilt.
