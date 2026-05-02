# Bob Task Prompt Plan — merge-resolver

These are ready-to-paste prompts for each Bob IDE task session.
Always begin each session by mentioning @AGENTS.md so Bob has full context.
Use Plan mode first, then Code mode.

---

## Pre-work (do manually, no Bobcoins)

```bash
# 1. Create project structure
mkdir -p merge-resolver/{git,analysis,ui,resolver,tests/fixtures,bob_sessions}
cd merge-resolver
touch main.py requirements.txt README.md AGENTS.md
touch git/__init__.py git/state.py git/parser.py
touch analysis/__init__.py analysis/classifier.py analysis/bob.py
touch ui/__init__.py ui/app.py ui/file_list.py ui/diff_view.py ui/ai_panel.py
touch resolver/__init__.py resolver/apply.py
touch tests/test_parser.py tests/test_classifier.py

# 2. Create seeded test repo
mkdir ../test-repo && cd ../test-repo
git init && git config user.email "test@test.com" && git config user.name "Test"

# File 1: simple logical conflict
mkdir -p src/auth
cat > src/auth/login.py << 'EOF'
def authenticate(user, password):
    return password == "secret"

def get_session_token():
    return "token_123"
EOF
git add . && git commit -m "initial: auth module"

# Branch A — adds JWT
git checkout -b feature/jwt
cat > src/auth/login.py << 'EOF'
import jwt

def authenticate(user, password):
    if password == "secret":
        return jwt.encode({"user": user}, "key")
    return None

def get_session_token():
    return jwt.encode({"session": True}, "key")
EOF
git add . && git commit -m "feature: add JWT authentication"

# Main branch — adds session middleware
git checkout main
cat > src/auth/login.py << 'EOF'
from sessions import SessionMiddleware

def authenticate(user, password):
    if password == "secret":
        SessionMiddleware.create(user)
        return True
    return False

def get_session_token():
    return SessionMiddleware.current_token()
EOF

# File 2: mechanical conflict (independent changes)
cat > src/auth/config.py << 'EOF'
MAX_RETRIES = 3
TIMEOUT = 30
DEBUG = False
EOF
git add . && git commit -m "main: add session middleware"

git merge feature/jwt   # creates conflicts — this is your test repo
cd ../merge-resolver
```

```
# requirements.txt contents:
textual>=0.59.0
rich>=13.7.0
pytest>=8.0.0
```

---

## TASK 1 — git/state.py + git/parser.py + ConflictHunk dataclass

**Mode:** Plan → Code
**Estimated Bobcoin cost:** Low-medium (focused, well-scoped)

```
@AGENTS.md

I am building a Python terminal app called merge-resolver. Please implement two modules:

**1. git/state.py** with these functions:
- `find_repo_root() -> Path` — walks up from cwd until a `.git` directory is found;
  raises `RuntimeError` with a clear message if none found
- `get_branch_names(repo_root: Path) -> tuple[str, str]` — returns (our_branch, their_branch).
  Our branch: `git rev-parse --abbrev-ref HEAD`. Their branch: read `.git/MERGE_HEAD`, then
  run `git name-rev --name-only <sha>` to get a readable name. Handle the case where
  MERGE_HEAD doesn't exist (not in a merge) gracefully.
- `get_conflicted_files(repo_root: Path) -> list[str]` — runs
  `git diff --name-only --diff-filter=U` and returns relative paths as strings

**2. git/parser.py** with:
- The `ConflictHunk` dataclass exactly as specified in AGENTS.md
- `enable_diff3(repo_root: Path)` — runs `git config merge.conflictstyle diff3`
- `parse_file(repo_root: Path, filepath: str) -> list[ConflictHunk]` — reads the file,
  splits on diff3-style markers: `<<<<<<<`, `|||||||`, `=======`, `>>>>>>>`.
  Populates file, hunk_index, start_line, ours, theirs, base.
  Does NOT set kind/severity/ai_* fields (those come from classifier.py later).
  Handle edge cases: file with no conflicts returns [], malformed markers raise ValueError.
- `parse_all(repo_root: Path) -> list[ConflictHunk]` — calls get_conflicted_files()
  then parse_file() for each; returns flat list of all hunks

**3. tests/test_parser.py** — pytest tests that:
- Test parse_file() against a fixture file in tests/fixtures/simple_conflict.py
  (create this fixture file too — it should be a realistic Python file with one
  diff3-style conflict block)
- Test that a file with no conflict markers returns []
- Test that ours/theirs/base are correctly split

All subprocess calls should use `subprocess.run(..., capture_output=True, text=True,
check=True)`. Use `pathlib.Path` throughout, not os.path.
```

---

## TASK 2 — analysis/classifier.py

**Mode:** Plan → Code
**Estimated Bobcoin cost:** Low (pure Python, no external calls)

```
@AGENTS.md

Implement `analysis/classifier.py` for the merge-resolver project.

The module classifies each ConflictHunk (imported from git/parser.py) into one of three
kinds and assigns a severity score. Here is the classification logic:

**Mechanical** (severity 1):
- Both ours and theirs are short (≤ 5 lines each total), AND
- The changed tokens don't share top-level Python identifiers
  (extract names using a simple regex: `r'\b(def |class )(\w+)'`, check that
  ours_names ∩ theirs_names == ∅)
- This catches cases like: one side adds an import, other changes a function body

**Logical** (severity 2):
- Both ours and theirs define or reference at least one shared top-level name
  (same regex as above — ours_names ∩ theirs_names != ∅)
- This is the default for most real conflicts

**Structural** (severity 3):
- Any symbol name from this hunk appears in a *different* conflicted file's hunks.
  This requires the full list of hunks as context (cross-file symbol collision).
- Set kind="structural" on ALL hunks that share a cross-file symbol.

Functions to implement:
- `_extract_names(lines: list[str]) -> set[str]` — regex extraction, internal helper
- `classify(hunk: ConflictHunk, all_hunks: list[ConflictHunk]) -> ConflictHunk`
  — sets kind and severity in place, returns the hunk
- `classify_all(hunks: list[ConflictHunk]) -> list[ConflictHunk]`
  — runs the structural pass first to build the cross-file symbol map, then
  classifies each hunk individually; returns the modified list

Also write `tests/test_classifier.py` with:
- A test for mechanical classification (short, non-overlapping hunks)
- A test for logical classification (overlapping function names)
- A test for structural classification (same symbol in two different files)

Use the ConflictHunk dataclass from git/parser.py. Do not import anything from ui/ or resolver/.
```

---

## TASK 3 — ui/ skeleton (static data, no AI)

**Mode:** Plan → Code
**Estimated Bobcoin cost:** Medium (Textual layout has nuance)

```
@AGENTS.md

Implement the Textual TUI skeleton for merge-resolver. Use static/hardcoded data for now —
the AI panel will be wired up in the next task. The goal is a fully navigable 3-panel layout.

**ui/app.py** — `MergeResolverApp(App)`:
- Title: "merge-resolver"
- Subtitle: "{ours_branch} → {theirs_branch} · {n} files, {m} hunks"
- Mounts three panels side by side: FileListPanel (20% width), DiffViewPanel (55%),
  AIPanelWidget (25%)
- Footer with key bindings: Tab=switch panel, Q=quit, C=commit
- Handles `FileSelected` and `HunkResolved` messages from child widgets
- Keyboard: Tab cycles focus between panels; Q quits; arrow keys within panels

**ui/file_list.py** — `FileListPanel(Widget)`:
- Takes `hunks: list[ConflictHunk]` as input
- Groups hunks by file, shows one row per file
- Each row: severity indicator (● in red/yellow/green based on max severity in file),
  filename (truncated if long), kind badge [logical]/[mechanical]/[structural],
  resolved progress e.g. "2/3"
- Arrow keys navigate rows; Enter/Space selects
- Emits `FileSelected(filename: str)` message on selection

**ui/diff_view.py** — `DiffViewPanel(Widget)`:
- Takes the currently selected list[ConflictHunk] for one file
- Shows "~~~ HUNK {i} of {n} ~~~" header
- Renders ours lines with green background prefix "< ", theirs with red "< ",
  base (ancestor) lines dimmed with "| " prefix
- Shows action hints at bottom: [A] Accept Ours [B] Accept Theirs [E] Edit [S] Bob
- Keyboard: ↑↓ scroll within hunk; n/p = next/prev hunk; a/b/s trigger resolution
- Emits `HunkResolved(hunk: ConflictHunk, resolved_text: str)` on a/b/s

**ui/ai_panel.py** — `AIPanelWidget(Widget)`:
- Static for now: shows a placeholder "Bob is thinking..." message
- Has a `update_hunk(hunk: ConflictHunk)` method that will be called later
- If hunk.ai_summary is non-empty, display it under "BOB SAYS"
- If hunk.ai_suggestion is non-empty, display it under "SUGGESTION:"
- Otherwise display a subtle "Analysis pending..." message

**main.py**:
- Accepts an optional `--repo` CLI argument (default: cwd)
- Calls `find_repo_root()`, `parse_all()`, `classify_all()`
- Launches `MergeResolverApp(hunks=hunks, ...)`

Use Textual's `compose()` pattern throughout. Use `Rich` markup for colours
(not raw ANSI codes). The app should run without crashing even if there are zero conflicts
(show a "No conflicts found" screen instead).
```

---

## TASK 4 — analysis/bob.py + wire AI panel

**Mode:** Plan → Code
**Estimated Bobcoin cost:** Medium (API integration + error handling)

```
@AGENTS.md

Implement `analysis/bob.py` and wire it into the TUI's AI panel.

**analysis/bob.py**:

The module calls an AI API to analyse each ConflictHunk and fill ai_summary + ai_suggestion.
For the hackathon, support two backends selectable via an environment variable AI_BACKEND:
- "watsonx" — calls IBM watsonx.ai text generation API
- "mock" — returns deterministic fake responses (for testing without burning API credits)

Use this exact prompt template (defined as a module-level constant ANALYSIS_PROMPT):

"""
You are a merge conflict analyst. Given the following conflict hunk, respond ONLY with
valid JSON in this exact format with no preamble or markdown:
{"summary": "<one sentence: why does this conflict exist>",
 "suggestion": "<one to three sentences: how to resolve it>"}

File: {file}
Conflict type: {kind}

=== OURS ({ours_branch}) ===
{ours_text}

=== BASE (common ancestor) ===
{base_text}

=== THEIRS ({theirs_branch}) ===
{theirs_text}
"""

Functions:
- `analyse_hunk(hunk: ConflictHunk, ours_branch: str, theirs_branch: str) -> ConflictHunk`
  — formats the prompt, calls the API, parses JSON response, sets hunk.ai_summary
  and hunk.ai_suggestion, returns hunk. On any error (network, parse failure),
  sets ai_summary to "Analysis unavailable" and ai_suggestion to "" — never raise.
- `analyse_all(hunks: list[ConflictHunk], ours_branch: str, theirs_branch: str)`
  — calls analyse_hunk for each hunk; for the watsonx backend, add a 0.5s delay
  between calls to avoid rate limiting

For the watsonx backend, use the watsonx.ai text generation REST API:
- Endpoint: https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29
- Auth: Bearer token from env var WATSONX_API_KEY (exchange via IAM endpoint)
- Model: ibm/granite-3-3-8b-instruct (recommended: small, fast, good at structured output)
- Parameters: max_new_tokens=300, temperature=0.1 (low temp for consistent JSON)
- The IAM token exchange URL is: https://iam.cloud.ibm.com/identity/token

Also wire this into **ui/ai_panel.py**:
- Add a `start_analysis(hunk, ours_branch, theirs_branch)` method that calls
  `analyse_hunk()` in a Textual worker thread (use `@work` decorator) so the UI
  doesn't freeze
- Show a spinner (Textual's `LoadingIndicator`) while the worker is running
- On completion, call `update_hunk(hunk)` to display the result

And update **ui/app.py** to call `start_analysis()` whenever the focused hunk changes
(listen for `FileSelected` and hunk navigation events).

Include a `mock` backend that returns:
{"summary": "Both branches modified the same function in incompatible ways.",
 "suggestion": "Review both implementations and manually merge the logic, preserving both changes where possible."}
```

---

## TASK 5 — resolver/apply.py + commit flow

**Mode:** Plan → Code
**Estimated Bobcoin cost:** Low-medium

```
@AGENTS.md

Implement `resolver/apply.py` and the end-to-end resolution + commit flow.

**resolver/apply.py**:

- `write_resolved(hunk: ConflictHunk, repo_root: Path) -> None`
  — reads the conflicted file from disk, finds the specific conflict block for this hunk
  (match by start_line and the <<<<<<< marker), replaces the entire block
  (from <<<<<<< to >>>>>>>) with `hunk.resolved_text`. Writes the file back.
  IMPORTANT: if multiple hunks in one file, process them bottom-up (highest start_line first)
  so earlier hunks' line numbers stay valid.

- `apply_all(hunks: list[ConflictHunk], repo_root: Path) -> dict[str, list[ConflictHunk]]`
  — filters to hunks where resolved_text is not None, groups by file, sorts each group
  bottom-up, calls write_resolved for each, returns a dict of {filename: [resolved_hunks]}.

- `stage_file(filepath: str, repo_root: Path) -> None`
  — runs `git add <filepath>`

- `commit(message: str, repo_root: Path) -> None`
  — runs `git commit -m <message>`

- `all_resolved(hunks: list[ConflictHunk]) -> bool`
  — returns True if every hunk has resolved_text set

**Commit flow in ui/app.py** (update this file):
- When user presses C:
  - If not all_resolved(hunks): show a modal dialog listing unresolved hunks,
    ask "Commit anyway? (partial)" with Yes/No
  - If yes or all resolved: call apply_all(), then stage each modified file,
    then show an input dialog for the commit message (pre-filled with
    "Resolve merge conflicts (merge-resolver)"), then call commit()
  - On success: show a "✓ Committed successfully" notification and quit after 2 seconds
  - On failure: show the error in a modal

Write a test in `tests/test_apply.py` that:
- Creates a temp file with a conflict block
- Creates a ConflictHunk with resolved_text = "resolved content\n"
- Calls write_resolved() and asserts the file no longer contains <<<<<<< markers
  and contains the resolved text
```

---

## TASK 6 (stretch) — Polish + demo prep

**Mode:** Code / Ask
**Use if Bobcoins remain**

```
@AGENTS.md

The core merge-resolver app is complete. Please help with the following polish items:

1. **Error handling audit**: Review all subprocess calls in git/ and ensure they handle:
   - Not being in a git repo
   - Being in a repo but not mid-merge
   - Git not installed
   Show friendly error messages in the TUI rather than stack traces.

2. **README.md**: Write a clear project README covering:
   - What the tool does and why it's useful (2-3 sentences)
   - Installation (pip install -r requirements.txt)
   - Usage (python main.py [--repo PATH])
   - How IBM Bob was used to build it (mention Bob IDE, task sessions in bob_sessions/)
   - Screenshot placeholder section

3. **Structural conflict cross-file hint**: In ui/ai_panel.py, if hunk.kind == "structural",
   add a section "⚠ Related files that may be affected:" listing the other files that share
   symbols with this hunk. This data is already computed in classifier.py — pass it through.

4. **Keyboard shortcut help modal**: Pressing ? should show a centered modal with all
   keyboard shortcuts listed in a clean table.
```

---

## Bobcoin budget guide

| Task | Rough cost | Cumulative |
|------|-----------|------------|
| Pre-work (manual) | 0 | 0 |
| Task 1: git parsing | 3–5 | ~5 |
| Task 2: classifier | 2–3 | ~8 |
| Task 3: TUI skeleton | 5–7 | ~15 |
| Task 4: AI integration | 4–6 | ~21 |
| Task 5: resolver | 3–4 | ~25 |
| Task 6: polish | 3–5 | ~30 |
| **Buffer** | — | **10 remaining** |

These are rough estimates. Use **Ask mode** for questions and **Plan mode** to review
Bob's plan before switching to Code — this avoids expensive re-dos.

---

## Judging checklist

Before submitting, verify:
- [ ] `bob_sessions/` folder contains screenshots + exported .md files for every task
- [ ] README.md explains the project and mentions IBM Bob
- [ ] App runs end-to-end on the test repo (`python main.py --repo ../test-repo`)
- [ ] At least 3 Bob task sessions exported (one per major module)
- [ ] No IBM API keys committed to the repo (use .env + .gitignore)
- [ ] `requirements.txt` is complete and accurate
