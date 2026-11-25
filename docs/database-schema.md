# The project database (`phonlab.db`)

A phonlab project keeps what it knows about its recordings in one SQLite file,
`phonlab.db`, in the project folder. The desktop app makes it, corrects it, and adds
information to it; analysis scripts read it. This page says what is in it and how to
find your way around, without assuming which optional information a project has.

Every query below was run against a database made by the app's own import code.

## Three kinds of table and column

A table or column is one of:

- **Core**: always there, and what scripts can rely on. Changing or removing one is a
  change of schema version.
- **Optional**: made by the app, but only when a project has a value for it, so a
  project without video has no `video_file` column. A script asks whether it is there
  before using it.
- **Open**: added by the researcher (age and sex of talkers, frequency and part of
  speech of words, any column of a CSV file added to recordings). The schema promises
  nothing about them except what they are called and what type they were given.

Nothing is created empty. There are no placeholder columns for information a project
does not have.

## Finding out what a project has

```python
import sqlite3

con = sqlite3.connect("file:phonlab.db?mode=ro", uri=True)   # read only

tables = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]

def columns(table):
    """{name: declared type} of a table"""
    return {r[1]: r[2] for r in con.execute(f'PRAGMA table_info("{table}")')}

"word" in tables                      # has a word table been added?
"pos" in columns("word")              # does it have part of speech?
```

Open a database you only read with `mode=ro`: the app may be open on the same file.

## Tables

### `recording` (core)

One row per recording.

| column | type | |
|---|---|---|
| `id` | INTEGER | primary key |
| `file_stem` | VARCHAR | unique; the path of the recording without its extension, relative to the project folder (`aa1/aa1_01`) |
| `audio_file` | VARCHAR | path of the sound file, relative to the project folder; null if the recording has none |
| `annotation_file` | VARCHAR | the file the annotation was read from, if it came from one |
| `data_files` | JSON | `{kind: path}` of files that go with the recording (formant tracks...) |
| `fields` | JSON | `{name: value}` of variables taken from folder and file names (`{"dialect": "north"}`) |
| `video_file` | TEXT | **optional**: a video of the recording, as a path in the project, or the name an ELAN file gives it |
| `media_offset` | REAL | **optional**: seconds, as an ELAN file gives for its sound; annotation times are not shifted by it |
| `target_talker` | TEXT | **optional**: the talker the folders and file names say, kept when the annotation file names talkers of its own |
| *others* | | **open**: columns added from a CSV file of recording information |

`fields` is JSON, so a value is read with `json_extract(fields, '$.dialect')`.

### `talker` (core)

One row per talker who is in a recording.

| column | type | |
|---|---|---|
| `id` | INTEGER | primary key |
| `name` | VARCHAR | unique |
| *others* | | **open**: columns added from a CSV file of talker information (`age`, `sex`...) |

### `recording_talker` (core)

Who is in which recording: one row for each recording and talker. A recording with
several talkers has several rows, in the order they were recorded.

| column | type | |
|---|---|---|
| `id` | INTEGER | |
| `recording_id` | INTEGER | → `recording.id` |
| `talker_id` | INTEGER | → `talker.id` |

### `annotation_type` (core)

One row per tier of a recording. Recordings have their own tiers: tier `word` of
one recording and tier `word` of another are two rows.

| column | type | |
|---|---|---|
| `id` | INTEGER | |
| `annotation_id` | INTEGER | → `recording.id` (the name is older than the table) |
| `name` | VARCHAR | the tier's name |
| `talker_id` | INTEGER | **optional**: → `talker.id`; who produced the tier, when its source says (ELAN participant, subtitle talker). The column exists only if some tier has a talker |

### `annotation_node` (core)

A point in time of a recording. Tiers share nodes: when the end of a word and of its
last phone are the same time they are the same node, and moving it moves both.

| column | type | |
|---|---|---|
| `id` | INTEGER | |
| `annotation_id` | INTEGER | → `recording.id` |
| `time` | DOUBLE | seconds from the start of the annotation |

### `annotation_label` (core)

An interval of a tier with its text.

| column | type | |
|---|---|---|
| `id` | INTEGER | |
| `annotation_type_id` | INTEGER | → `annotation_type.id` |
| `label_text` | TEXT | |
| `start_node_id`, `end_node_id` | INTEGER | → `annotation_node.id` |

### `word` (optional table; open columns)

Made when the user adds a table of words (a frequency list, a lexicon). It is not
linked to the labels by an id: a word of the table is the label text of a tier, compared as
written (the case counts), so the tier it applies to is the one the user matched it
with.

| column | type | |
|---|---|---|
| `id` | INTEGER | |
| `word` | TEXT | unique |
| *others* | | **open**: whatever the user's table had (`pos`, `freq`...) |

### `recording_channel` (optional table)

Only for a recording stored as one sound file per channel.

| column | type | |
|---|---|---|
| `id` | INTEGER | |
| `recording_id` | INTEGER | → `recording.id` |
| `channel` | VARCHAR | the label of the channel |
| `audio_file` | VARCHAR | path of that channel's file |
| `talker_id` | INTEGER | → `talker.id`, if known |

## Names that mean the same thing in every project

The names of open columns are the researcher's. Where people usually add the same kind of
information, use the same name so scripts can be shared; this is a recommendation,
the database does not check it.

| table | name | values |
|---|---|---|
| `word` | `pos` | part of speech: `noun`, `verb`, `adjective`, `determiner`... |
| `word` | `freq` | frequency, a number |
| `talker` | `sex`, `age` | as the researcher records them |

Column names are letters, digits and underscores, and start with a letter or underscore.

## Using it

### A flat table of labels

The tables are joined by id, which is awkward for analysis. This view gives one row per
label:

```sql
CREATE TEMP VIEW label_table AS
SELECT r.file_stem AS recording, t.name AS tier,
       s.time AS t1, e.time AS t2, l.label_text AS label
FROM annotation_label AS l
JOIN annotation_type  AS t ON t.id = l.annotation_type_id
JOIN recording        AS r ON r.id = t.annotation_id
JOIN annotation_node  AS s ON s.id = l.start_node_id
JOIN annotation_node  AS e ON e.id = l.end_node_id;
```

A temporary view lives only in your connection, so it works on a read-only file.

```python
import pandas as pd
labels = pd.read_sql("SELECT * FROM label_table WHERE tier = 'word'", con)
```

### Who is in each recording

```python
pd.read_sql("""
SELECT r.file_stem, k.name AS talker, r.target_talker
FROM recording AS r
JOIN recording_talker AS rt ON rt.recording_id = r.id
JOIN talker AS k ON k.id = rt.talker_id""", con)
```

Add `k.age` (or any open column) only after checking `columns("talker")` has it.

### What is under a label: count the phones in each word

What a label contains is not stored; it is the labels of another tier within its time
span. Compare times (not node ids: two nodes may be the same time without being shared):

```sql
SELECT w.recording, w.t1, w.t2, w.label AS word,
       (SELECT COUNT(*) FROM label_table AS p
         WHERE p.recording = w.recording AND p.tier = 'phone'
           AND p.t1 >= w.t1 AND p.t2 <= w.t2) AS n_phones
FROM label_table AS w
WHERE w.tier = 'word';
```

### Are words with the same number of phones longer as verbs than as adjectives?

Only for a project whose word table has `pos`:

```python
if "pos" not in columns("word"):
    raise SystemExit("this project's word table has no part of speech")

words = pd.read_sql("""
SELECT w.recording, w.t1, w.t2, w.label AS word,
       (SELECT COUNT(*) FROM label_table AS p
         WHERE p.recording = w.recording AND p.tier = 'phone'
           AND p.t1 >= w.t1 AND p.t2 <= w.t2) AS n_phones
FROM label_table AS w WHERE w.tier = 'word'""", con)
words = words.merge(pd.read_sql("SELECT word, pos FROM word", con), on="word")
words["duration"] = words.t2 - words.t1
words.groupby(["n_phones", "pos"]).duration.agg(["mean", "count"])
```

### Added columns whose names you do not know

```python
columns("talker")                                    # everything, core and added
set(columns("talker")) - {"id", "name"}              # what the researcher added
```

## What is not promised yet

- **Version number.** The file does not carry one yet. It should, with SQLite's
  `PRAGMA user_version`, before other people write scripts against it.
- **Types.** Added columns are `TEXT`, `INTEGER` or `REAL`. A column of numbers read
  from a CSV file that had a stray word in it is `TEXT`; check the type before averaging.
- **Writing.** Only the app writes to the file. A script that writes can break rules the
  app keeps (nodes shared between tiers, the order of tiers), so read it with
  `mode=ro`.
- **Names of core columns.** Some are older than what they mean: `annotation_id` in
  `annotation_type` and `annotation_node` points at a recording. They would be renamed
  together with the first version number.

## The Python interface (`phonlab_project`)

`src/phonlab_project` does what the sections above do by hand. It is a prototype of what
could go into phonlab: it uses only `sqlite3`, numpy and pandas, nothing of the desktop
app (a test checks this), and it opens the file read only.

```python
from phonlab_project import open_project

with open_project("my_corpus") as project:       # the folder, or the phonlab.db in it
    project.tables()                              # ['annotation_label', ..., 'word']
    project.columns("talker")                     # DataFrame: name, type, kind
    project.has_column("word", "pos")             # True

    project.recordings()                          # every column, 'fields' made columns
    project.talkers()                             # every column, added ones too
    project.recording_talkers()                   # recording, talker
    project.tiers()                               # recording, tier, talker, n_labels

    project.labels(tier="word")                   # recording, tier, talker, t1, t2, label
    project.labels(tier=["word", "phone"], talker="Ann", recording="aa1/aa1_01")

    project.count_within("word", "phone")         # labels of 'word' + n_phone
    words = project.words(count="phone")          # + the word table's columns (pos, freq...)
```

The question about part of speech then is:

```python
words = project.words(count="phone")
words["duration"] = words.t2 - words.t1
words.groupby(["n_phone", "pos"]).duration.agg(["mean", "count"])
```

What it does when the project lacks something:

- A tier, talker or recording that is not there raises `ProjectError` and names the ones
  that are: `The project has no tier ['syllable']; it has ['word', 'phone']`.
- A project with no word table, or asking for a talker when no tier has one, raises
  `ProjectError` with what to do, instead of returning nothing.
- The `talker` column of `labels()` and `tiers()` is always there, and empty when the
  source files did not say who made a tier. Check `has_column("annotation_type",
  "talker_id")` to know which.

Not done yet: `Python 3.10` is not checked (phonlab supports it; the prototype avoids
`typing.Self` but has not been run there), the schema version is not read, and a project
of tens of thousands of words has not been timed.
