# 🔀 merge-resolver

**An intelligent terminal UI for resolving git merge conflicts with AI assistance**

`merge-resolver` replaces manual conflict resolution with a guided, intelligent workflow. It detects conflicted files, classifies each conflict by type (mechanical/logical/structural), calls IBM Bob AI for plain-English analysis and resolution suggestions, and lets you resolve hunks interactively before staging and committing.

Built for the **IBM Bob Dev Day Hackathon 2026** — theme: *"Turn idea into impact faster"*.

---

## ✨ Features

- 🎯 **Smart conflict classification**: Automatically categorizes conflicts as mechanical, logical, or structural
- 🤖 **AI-powered analysis**: IBM Bob (watsonx.ai) provides plain-English summaries and resolution suggestions
- 🖥️ **Beautiful TUI**: Three-panel interface with file list, diff view, and AI insights
- ⚡ **Efficient workflow**: Navigate conflicts with keyboard shortcuts, resolve with one keystroke
- 🔍 **Cross-file awareness**: Detects structural conflicts that span multiple files
- 📊 **Severity indicators**: Visual badges show conflict complexity at a glance

---

## 🚀 Installation

### Prerequisites

- Python 3.11 or higher
- Git 2.0 or higher
- IBM Bob API access (for AI features)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/merge-resolver.git
cd merge-resolver
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure IBM Bob credentials (if using AI features):
```bash
export BOB_API_KEY="your-api-key"
export BOB_API_URL="https://bob.api.example.com"
```

---

## 📖 Usage

### Basic Usage

When you encounter merge conflicts during a git merge:

```bash
# Start a merge that creates conflicts
git merge feature-branch

# Launch merge-resolver
python main.py
```

The TUI will open with all conflicts detected and classified.

### Command Line Options

```bash
python main.py [--repo PATH]
```

- `--repo PATH`: Specify a different git repository path (default: current directory)

### TUI Navigation

**File List Panel (Left)**
- `↑/↓` or `j/k`: Navigate between files
- `Enter`: Select file and view first conflict

**Diff View Panel (Center)**
- `↑/↓` or `j/k`: Navigate between hunks in current file
- `A`: Accept "ours" (current branch) version
- `B`: Accept "theirs" (incoming branch) version
- `E`: Edit manually (opens in editor)
- `S`: Apply Bob's AI suggestion
- `N`: Skip to next hunk
- `P`: Go to previous hunk

**AI Panel (Right)**
- Automatically shows analysis for selected hunk
- Updates as you navigate

**Global Shortcuts**
- `Tab`: Cycle between panels
- `?`: Show keyboard shortcuts help
- `C`: Commit resolved changes
- `Q`: Quit (prompts if unresolved conflicts remain)

---

## 🎨 TUI Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  🔀 merge-resolver  ·  feature/auth → main  ·  3 files, 5 hunks     │
├──────────────────┬──────────────────────────┬────────────────────────┤
│ FILES            │  src/auth/login.py [1/2] │ BOB SAYS               │
│                  │                          │                        │
│ 🔴 login.py      │  ~~~ HUNK 1 of 2 ~~~    │ Both sides modified    │
│    [logical]     │                          │ the authentication     │
│ 🟡 models.py     │  < OURS (feature/auth)   │ logic differently.     │
│    [mechanical]  │  + use_jwt = True        │                        │
│ 🔴 migrations/.. │  ---                     │ SUGGESTION:            │
│    [structural]  │  > THEIRS (main)         │ Keep JWT auth from     │
│                  │  + session_mw = True     │ feature branch, it's   │
│                  │                          │ more secure.           │
│                  │  [A] Accept Ours         │                        │
│                  │  [B] Accept Theirs       │                        │
│                  │  [E] Edit manually       │                        │
│                  │  [S] Bob's suggestion    │                        │
├──────────────────┴──────────────────────────┴────────────────────────┤
│  [↑↓] navigate · [Tab] switch panel · [C] commit · [Q] quit         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 How IBM Bob Was Used

This project was built entirely using **IBM Bob IDE** during the Bob Dev Day Hackathon 2026. Bob's AI capabilities were instrumental in:

### Development Process

1. **Architecture Design**: Bob helped design the modular structure (git/, analysis/, ui/, resolver/)
2. **Code Generation**: Bob wrote the core parsing logic, TUI components, and AI integration
3. **Testing**: Bob generated comprehensive unit tests for all modules
4. **Debugging**: Bob identified and fixed edge cases in conflict parsing
5. **Documentation**: Bob helped write docstrings, comments, and this README

### Bob Task Sessions

All development sessions were tracked in Bob IDE and exported for transparency:

- `bob_sessions/bob_task_may-2-2026_8-12-22-pm.md` - Initial project setup and git state detection
- `bob_sessions/bob_task_may-2-2026_8-31-13-pm.md` - Conflict parser implementation
- `bob_sessions/bob_task_may-2-2026_8-42-52-pm.md` - Conflict classifier with heuristics
- `bob_sessions/bob_task_may-2-2026_9-19-59-pm.md` - TUI skeleton with Textual
- `bob_sessions/bob_task_may-2-2026_10-24-56-pm.md` - AI integration with watsonx.ai
- `bob_sessions/bob_task_may-2-2026_11-07-22-pm.md` - Resolution workflow and git operations
- `bob_sessions/bob_task_may-2-2026_11-20-17-pm.md` - Polish, error handling, and final touches

Each session export includes:
- Task description and planning
- Code changes made
- Testing approach
- Challenges encountered and solutions

### AI-Powered Features

The AI analysis in merge-resolver uses IBM Bob's watsonx.ai backend to:
- Understand the semantic meaning of conflicting code
- Identify why conflicts occurred (refactoring, feature additions, etc.)
- Suggest the most appropriate resolution strategy
- Detect cross-file dependencies in structural conflicts

---

## 🏗️ Architecture

```
merge-resolver/
├── git/              # Git repository interaction
│   ├── state.py      # Repo detection, branch names, conflict discovery
│   └── parser.py     # Conflict marker parsing → ConflictHunk objects
├── analysis/         # Conflict analysis
│   ├── classifier.py # Heuristic classification (mechanical/logical/structural)
│   └── bob.py        # AI API integration for summaries and suggestions
├── ui/               # Textual TUI components
│   ├── app.py        # Main application and layout
│   ├── file_list.py  # Left panel: file list with severity badges
│   ├── diff_view.py  # Center panel: conflict diff with actions
│   └── ai_panel.py   # Right panel: AI analysis display
├── resolver/         # Conflict resolution
│   └── apply.py      # Write resolved files, stage, commit
└── main.py           # Entry point
```

---

## 🧪 Testing

Run the test suite:

```bash
# All tests
python -m pytest

# Specific module
python -m pytest tests/test_parser.py

# With coverage
python -m pytest --cov=. --cov-report=html
```

Test fixtures are in `tests/fixtures/` with pre-baked conflict scenarios.

---

## 🎯 Conflict Types

### 🟢 Mechanical (Severity 1)
Simple conflicts where changes don't overlap semantically. Example: one side adds an import, the other modifies a function body.

**Resolution**: Usually safe to accept both changes or choose based on code style.

### 🟡 Logical (Severity 2)
Both sides modified the same function, class, or variable. Requires understanding the intent of each change.

**Resolution**: May need to merge logic from both sides or choose the more complete implementation.

### 🔴 Structural (Severity 3)
One side renamed/moved symbols that appear in other conflicted files. Cross-file dependencies detected.

**Resolution**: Must resolve in correct order to maintain consistency across the codebase.

---

## 📸 Screenshots

*Screenshots will be added here after demo*

---

## 🤝 Contributing

This project was built for the IBM Bob Dev Day Hackathon 2026. Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- **IBM Bob IDE** for making rapid development possible
- **watsonx.ai** for powering the AI analysis
- **Textual** framework for the beautiful TUI
- **IBM Bob Dev Day Hackathon 2026** for the inspiration

---

## 📞 Support

For issues or questions:
- Open an issue on GitHub
- Check the `bob_sessions/` directory for detailed development notes
- Review the `AGENTS.md` file for architecture details

---

**Built with ❤️ and 🤖 IBM Bob**