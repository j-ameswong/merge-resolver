"""File list panel showing conflicted files with severity indicators."""

from collections import defaultdict
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static
from rich.text import Text

from git.parser import ConflictHunk


class FileSelected(Message):
    """Message emitted when a file is selected."""
    
    def __init__(self, filename: str) -> None:
        self.filename = filename
        super().__init__()


class FileListPanel(Widget):
    """
    Left panel showing list of conflicted files.
    
    Each row displays:
    - Severity indicator (● in red/yellow/green)
    - Filename (truncated if needed)
    - Conflict type badge [mechanical]/[logical]/[structural]
    - Resolution progress (e.g., "2/3")
    """
    
    DEFAULT_CSS = """
    FileListPanel {
        width: 20%;
        border: solid $primary;
    }
    
    FileListPanel > VerticalScroll {
        height: 100%;
    }
    
    .file-row {
        padding: 0 1;
        height: 1;
    }
    
    .file-row-selected {
        background: $accent;
    }
    
    .file-row:hover {
        background: $accent 50%;
    }
    """
    
    def __init__(self, hunks: list[ConflictHunk]) -> None:
        super().__init__()
        self.hunks = hunks
        self.selected_index = 0
        self._group_hunks()
    
    def _group_hunks(self) -> None:
        """Group hunks by file and calculate stats."""
        self.file_groups: dict[str, list[ConflictHunk]] = defaultdict(list)
        
        for hunk in self.hunks:
            self.file_groups[hunk.file].append(hunk)
        
        self.filenames = sorted(self.file_groups.keys())
    
    def compose(self) -> ComposeResult:
        """Compose the file list."""
        with VerticalScroll():
            if not self.filenames:
                yield Static("[dim]No conflicts found[/dim]")
            else:
                for idx, filename in enumerate(self.filenames):
                    yield self._create_file_row(filename, idx)
    
    def _create_file_row(self, filename: str, idx: int) -> Static:
        """Create a single file row with severity indicator and stats."""
        hunks = self.file_groups[filename]
        
        # Calculate max severity and most common kind
        max_severity = max(h.severity for h in hunks)
        kind_counts = defaultdict(int)
        for h in hunks:
            kind_counts[h.kind] += 1
        most_common_kind = max(kind_counts.items(), key=lambda x: x[1])[0]
        
        # Count resolved hunks
        resolved_count = sum(1 for h in hunks if h.resolved_text is not None)
        total_count = len(hunks)
        
        # Severity indicator
        severity_colors = {1: "green", 2: "yellow", 3: "red"}
        severity_color = severity_colors[max_severity]
        
        # Truncate filename if too long
        display_name = filename
        if len(display_name) > 25:
            display_name = "..." + display_name[-22:]
        
        # Build the row text
        text = Text()
        text.append("● ", style=severity_color)
        text.append(display_name, style="bold" if idx == self.selected_index else "")
        text.append(f" [{most_common_kind}] ", style="dim")
        text.append(f"{resolved_count}/{total_count}", style="cyan")
        
        row = Static(text)
        row.add_class("file-row")
        if idx == self.selected_index:
            row.add_class("file-row-selected")
        
        return row
    
    def on_key(self, event) -> None:
        """Handle keyboard navigation."""
        if not self.filenames:
            return
        
        if event.key == "up":
            self.selected_index = max(0, self.selected_index - 1)
            self._refresh_rows()
            event.prevent_default()
        elif event.key == "down":
            self.selected_index = min(len(self.filenames) - 1, self.selected_index + 1)
            self._refresh_rows()
            event.prevent_default()
        elif event.key in ("enter", "space"):
            self._select_current_file()
            event.prevent_default()
    
    def _refresh_rows(self) -> None:
        """Refresh the display to show updated selection."""
        # Remove all children and recreate
        scroll = self.query_one(VerticalScroll)
        scroll.remove_children()
        
        for idx, filename in enumerate(self.filenames):
            scroll.mount(self._create_file_row(filename, idx))
    
    def _select_current_file(self) -> None:
        """Emit FileSelected message for the currently selected file."""
        if self.filenames:
            filename = self.filenames[self.selected_index]
            self.post_message(FileSelected(filename))
    
    def get_selected_filename(self) -> str | None:
        """Get the currently selected filename."""
        if self.filenames and 0 <= self.selected_index < len(self.filenames):
            return self.filenames[self.selected_index]
        return None

# Made with Bob
