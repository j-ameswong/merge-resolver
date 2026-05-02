# merge-resolver — AGENTS.md

## Project overview

`merge-resolver` is a terminal application (TUI) that replaces manual `git` conflict resolution
with an intelligent, guided workflow. It detects conflicted files, classifies each conflict hunk
by type (mechanical / logical / structural), calls an AI backend (IBM Bob / watsonx.ai) for
plain-English analysis and resolution suggestions, and lets the user resolve hunks interactively
before staging and committing the result.

Built for the IBM Bob Dev Day Hackathon 2026 — theme: "Turn idea into impact faster".
Stack: Python 3.11+, Textual (TUI), Rich (styling), dataclasses (data model).

---

## Repository layout

```
merge-resolver/
├── AGENTS.md                  ← this file; keep updated as work progresses
├── README.md
├── main.py                    ← entry point; mounts the Textual App
├── git/
│   ├── __init__.py
│   ├── state.py               ← repo detection, branch names, conflicted file list
│   └── parser.py              ← conflict marker parsing → ConflictHunk dataclasses
├── analysis/
│   ├── __init__.py
│   ├── classifier.py          ← heuristic classification (mechanical/logical/structural)
│   └── bob.py                 ← AI API calls; fills ai_summary + ai_suggestion fields
├── ui/
│   ├── __init__.py
│   ├── app.py                 ← Textual App root; mounts all panels
│   ├── file_list.py           ← left panel: conflicted files with severity badges
│   ├── diff_view.py           ← centre panel: colour-coded conflict hunks
│   └── ai_panel.py            ← right panel: AI analysis + suggestion
├── resolver/
│   ├── __init__.py
│   └── apply.py               ← writes resolved file to disk, runs `git add`
├── tests/
│   ├── test_parser.py
│   ├── test_classifier.py
│   └── fixtures/              ← pre-baked conflicted file snippets for unit tests
├── test-repo/                 ← toy git repo with seeded conflicts (not committed)
├── bob_sessions/              ← Bob IDE task session exports (required for judging)
└── requirements.txt
```

---

## Core data model

Everything in the app flows through `ConflictHunk`. Never restructure this without updating
all consumers.

```python
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class ConflictHunk:
    file: str                          # relative path from repo root
    hunk_index: int                    # 0-based index within this file
    start_line: int                    # line number where <<<<<<< appears
    ours: list[str]                    # lines from HEAD side (after <<<<<<<)
    theirs: list[str]                  # lines from incoming branch (after >>>>>>>)
    base: list[str]                    # common ancestor lines (from diff3 ||||||| section)
    kind: Literal["mechanical",
                  "logical",
                  "structural"]        # set by classifier.py
    severity: int                      # 1 = low, 2 = medium, 3 = high
    ai_summary: str = ""               # filled by bob.py
    ai_suggestion: str = ""            # filled by bob.py
    resolved_text: str | None = None   # set when user accepts/edits a resolution
```

---

## Module responsibilities

### git/state.py
- `find_repo_root() -> Path` — walk up from cwd until `.git` found; raise if none
- `get_branch_names() -> tuple[str, str]` — returns `(ours_branch, theirs_branch)`
  by parsing `git status` or `.git/MERGE_HEAD` + `git rev-parse --abbrev-ref HEAD`
- `get_conflicted_files() -> list[str]` — runs `git diff --name-only --diff-filter=U`
  and returns relative paths

### git/parser.py
- `enable_diff3(repo_root: Path)` — runs `git config merge.conflictstyle diff3` so
  the `|||||||` ancestor section is present in conflict markers
- `parse_file(filepath: Path) -> list[ConflictHunk]` — reads the file, splits on
  `<<<<<<<` / `|||||||` / `=======` / `>>>>>>>` markers, returns list of hunks.
  Populates: file, hunk_index, start_line, ours, theirs, base.
  Does NOT set kind/severity/ai_* — those come later.
- `parse_all(repo_root: Path) -> list[ConflictHunk]` — calls `get_conflicted_files()`
  then `parse_file()` for each; returns flat list

### analysis/classifier.py
- `classify(hunk: ConflictHunk) -> ConflictHunk` — sets kind + severity in place:
  - **mechanical**: both sides are short (≤5 lines each), changed tokens don't overlap
    semantically (e.g. one side adds an import, other edits a function body). Severity 1.
  - **logical**: both sides modify the same named function/class/variable (extract
    top-level names from ours + theirs using simple regex, check intersection). Severity 2.
  - **structural**: one side has renamed/moved symbols that appear in other conflicted
    files — cross-reference symbol names across all hunks. Severity 3.
- `classify_all(hunks: list[ConflictHunk]) -> list[ConflictHunk]` — applies classify()
  to each hunk; runs structural pass last (needs global symbol view)

### analysis/bob.py
- `analyse_hunk(hunk: ConflictHunk, context: str) -> ConflictHunk` — calls the AI API
  with a structured prompt containing the hunk's ours/theirs/base and file context;
  parses JSON response into ai_summary + ai_suggestion
- `analyse_all(hunks: list[ConflictHunk], repo_root: Path)` — batches hunk analysis;
  shows a Rich progress spinner while waiting
- Prompt contract: ask Bob to return JSON `{"summary": "...", "suggestion": "..."}`;
  keep prompts tight to preserve Bobcoins

### ui/app.py
- Textual `App` subclass; mounts `FileListPanel`, `DiffViewPanel`, `AIPanelWidget`
- Manages shared state: currently selected file and hunk index
- Handles keyboard bindings: Tab (cycle panels), Q (quit), C (commit flow)

### ui/file_list.py
- `FileListPanel(Widget)` — scrollable list of conflicted files
- Each row shows: severity dot (🔴/🟡/🟢), filename, conflict type badge, resolved count
- Emits `FileSelected` message when user navigates to a file

### ui/diff_view.py
- `DiffViewPanel(Widget)` — shows one hunk at a time with navigation
- Renders ours lines in green, theirs lines in red, base lines in dim
- Action buttons: [A] Accept Ours, [B] Accept Theirs, [E] Edit, [S] Bob's suggestion
- Emits `HunkResolved` message with the chosen text

### ui/ai_panel.py
- `AIPanelWidget(Widget)` — right sidebar
- Shows ai_summary and ai_suggestion for the currently focused hunk
- Shows a spinner while analysis is in flight
- Falls back gracefully if AI call fails (shows raw hunk info instead)

### resolver/apply.py
- `write_resolved(hunk: ConflictHunk, repo_root: Path)` — replaces the conflict block
  in the file on disk with `hunk.resolved_text`
- `apply_all(hunks: list[ConflictHunk], repo_root: Path)` — writes all resolved hunks;
  handles ordering within a file carefully (process hunks bottom-up to preserve line numbers)
- `stage_file(filepath: str, repo_root: Path)` — runs `git add <filepath>`
- `commit(message: str, repo_root: Path)` — runs `git commit -m <message>`

---

## AI prompt template (bob.py)

```
You are a merge conflict analyst. Given the following conflict hunk, respond ONLY with
valid JSON in this exact format:
{"summary": "<one sentence describing why this conflict exists>",
 "suggestion": "<one to three sentences on how to resolve it>"}

File: {file}
Conflict type: {kind}

=== OURS ({ours_branch}) ===
{ours_text}

=== BASE (common ancestor) ===
{base_text}

=== THEIRS ({theirs_branch}) ===
{theirs_text}
```

---

## TUI layout (3-panel)

```
┌─────────────────────────────────────────────────────────────────────┐
│  🔀 merge-resolver  ·  feature/auth → main  ·  3 files, 5 hunks     │
├──────────────────┬──────────────────────────┬────────────────────────┤
│ FILES            │  src/auth/login.py [1/2] │ BOB SAYS               │
│                  │                          │                        │
│ 🔴 login.py      │  ~~~ HUNK 1 of 2 ~~~    │ <ai_summary>           │
│    [logical]     │                          │                        │
│ 🟡 models.py     │  < OURS (feature/auth)   │ SUGGESTION:            │
│    [mechanical]  │  + use_jwt = True        │ <ai_suggestion>        │
│ 🔴 migrations/.. │  ---                     │                        │
│    [structural]  │  > THEIRS (main)         │                        │
│                  │  + session_mw = True     │                        │
│                  │                          │                        │
│                  │  [A] Accept Ours         │                        │
│                  │  [B] Accept Theirs       │                        │
│                  │  [E] Edit manually       │                        │
│                  │  [S] Bob's suggestion    │                        │
├──────────────────┴──────────────────────────┴────────────────────────┤
│  [↑↓] navigate hunks · [Tab] switch panel · [C] commit · [Q] quit   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation order

1. `git/state.py` + `git/parser.py` + `ConflictHunk` dataclass — foundation; test first
2. `analysis/classifier.py` — heuristics only, no AI needed
3. `ui/` skeleton — static data, no AI, just rendering
4. `analysis/bob.py` — wire AI; connect to `ui/ai_panel.py`
5. `resolver/apply.py` + commit flow — end-to-end resolution

---

## Bob IDE task guidelines

- Start each Bob session with: `@AGENTS.md` to give Bob full context
- One task = one module or one clearly scoped feature
- Use **Plan mode** first to let Bob outline the approach, then **Code mode** to implement
- Use **Ask mode** for questions that don't need code written (saves Bobcoins)
- Export task session report after every meaningful task (History → select task → Export)
- Save exports to `bob_sessions/` in the repo

---

## Current status

- [ ] Repo skeleton created
- [ ] Test repo with seeded conflicts created
- [ ] git/state.py
- [ ] git/parser.py + ConflictHunk dataclass
- [ ] tests/test_parser.py
- [ ] analysis/classifier.py
- [ ] tests/test_classifier.py
- [ ] ui/ skeleton (static data)
- [ ] analysis/bob.py
- [ ] ui/ai_panel.py wired to bob.py
- [ ] resolver/apply.py
- [ ] End-to-end demo run
- [ ] bob_sessions/ populated for judging
