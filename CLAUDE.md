# Guidelines for Claude in this repository

Read `ARCHITECTURE.md` and `CONTRIBUTING.md` first; they are authoritative.
The points below distill how the maintainer (upstream `alecmullen/phonlab-desktop`)
has corrected earlier AI-written code. Background: `docs/upstream-refactor-review.md`.

## Where code goes

- **Put UI behaviour in the view that owns the widget.** A plot defines its own
  context-menu actions, checkboxes and buttons and connects their signals itself.
  `DocumentView` only coordinates things that span plots (layout, shared
  zoom/selection, dialogs). Don't add menu actions, hit-testing, or per-channel
  controls to `DocumentView` / `DocumentViewModel` just because they have the context.
- **Input handling:** override Qt event methods (`mousePressEvent`, `wheelEvent`,
  ...) on the relevant view. Don't install a viewport-wide `eventFilter` that
  hit-tests children; children must be able to receive their own events.
- **Business logic goes in `core`.** Don't hand-roll array slicing/copying/undo
  in a view model. Extend or reuse a use case (e.g. `EditAudio` with an
  `EditCommandType`). Don't create a use-case class for a one-line numpy op.
- Group by feature: audio-modifying use cases live in `core/transform_audio/`
  or `core/edit_audio/`; dataclasses in the feature's `entity/`; constants and
  defaults in `res/constants.py`; View-owned dialogs under that feature's
  `component/`; UI state dataclasses under `state/`.

## How components talk

- Data flows up as `State` via the view model's single `state_changed` signal and
  down via method calls from parent VM to child VM. **Do not add new
  `pyqtSignal`s between views.**
- Context-menu commands follow one pattern: `QAction.triggered` -> slot on the
  plot's own view model -> VM emits a payload-free `*Action(State)`
  (`ui/waveform/state/audio_wave_action.py`) -> `DocumentViewModel.on_wave_state_changed`
  handles it or relays it -> `DocumentView.on_state_change` opens the dialog and
  calls the document VM with the result. To add a command, add an `*Action`
  state; don't wire the view straight to the document VM.
- Child view models carry their identity (e.g. `AudioWaveViewModel.channel_idx`)
  and include it in emitted states. The parent reacts; it should not push
  mirrored state into children by position.

## Entities and layers

- `core` never imports `ui`. `ui` views and dialogs never receive `core`
  entities: map once at the VM boundary (`to_audio_state`, `to_audio_signals`,
  ...), and give UI its own `-State` class (e.g. `AudioOpenOptionsState`).
- Prefer one accessor over near-duplicates (`active_channels()` returning
  `dict[int, ...]`); if you are about to write a second helper that differs
  slightly from an existing one, generalize the existing one.

## Process

- Before writing, find the existing feature folder, test file, and a similar
  implementation, and follow it. Before adding code to `document_view*.py`,
  ask whether a plot/child view model should own it.
- Tests mirror `src`; put a control's tests in that plot's/VM's test file, not in
  `test_document_view.py`.
- Run `uv run ruff format .`, `uv run ruff check`, `uv run ty check`, and
  `uv run pytest` before commits headed upstream. All user-facing strings go
  through `self.tr()`. Keep PRs under ~400 lines; do pure file moves/renames in
  their own commit.
- Prefer many small, mechanical "move/consolidate" commits over mixing a
  refactor into feature work.
