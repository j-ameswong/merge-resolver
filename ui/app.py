"""Main Textual application for merge-resolver."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer
from textual.binding import Binding

from git.parser import ConflictHunk
from ui.file_list import FileListPanel, FileSelected
from ui.diff_view import DiffViewPanel, HunkResolved
from ui.ai_panel import AIPanelWidget


class MergeResolverApp(App):
    """
    Main TUI application for merge conflict resolution.
    
    Layout:
    - Header: title and branch info
    - Body: 3-panel layout (file list | diff view | AI panel)
    - Footer: key bindings
    """
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #main-container {
        height: 100%;
    }
    
    #panels {
        height: 1fr;
    }
    """
    
    BINDINGS = [
        Binding("tab", "cycle_focus", "Switch Panel", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("c", "commit", "Commit", show=True),
    ]
    
    def __init__(
        self,
        hunks: list[ConflictHunk],
        ours_branch: str = "HEAD",
        theirs_branch: str = "MERGE_HEAD"
    ) -> None:
        super().__init__()
        self.hunks = hunks
        self.ours_branch = ours_branch
        self.theirs_branch = theirs_branch
        
        # Track current state
        self.current_file: str | None = None
        self.file_list_panel: FileListPanel | None = None
        self.diff_view_panel: DiffViewPanel | None = None
        self.ai_panel: AIPanelWidget | None = None
    
    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        # Calculate stats for subtitle
        num_files = len(set(h.file for h in self.hunks))
        num_hunks = len(self.hunks)
        
        subtitle = f"{self.ours_branch} → {self.theirs_branch} · {num_files} files, {num_hunks} hunks"
        
        yield Header(show_clock=False)
        
        with Container(id="main-container"):
            with Horizontal(id="panels"):
                # Left panel: file list
                self.file_list_panel = FileListPanel(self.hunks)
                yield self.file_list_panel
                
                # Center panel: diff view
                self.diff_view_panel = DiffViewPanel()
                yield self.diff_view_panel
                
                # Right panel: AI analysis
                self.ai_panel = AIPanelWidget()
                yield self.ai_panel
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        # Set the title and subtitle
        self.title = "merge-resolver"
        self.sub_title = f"{self.ours_branch} → {self.theirs_branch} · {len(set(h.file for h in self.hunks))} files, {len(self.hunks)} hunks"
        
        # Auto-select first file if available
        if self.file_list_panel and self.hunks:
            first_file = self.file_list_panel.get_selected_filename()
            if first_file:
                self._load_file(first_file)
    
    def on_file_selected(self, message: FileSelected) -> None:
        """Handle file selection from the file list panel."""
        self._load_file(message.filename)
    
    def _load_file(self, filename: str) -> None:
        """Load hunks for the selected file into the diff view."""
        self.current_file = filename
        
        # Filter hunks for this file
        file_hunks = [h for h in self.hunks if h.file == filename]
        
        # Update diff view
        if self.diff_view_panel:
            self.diff_view_panel.update_hunks(file_hunks)
        
        # Update AI panel with first hunk
        if self.ai_panel and file_hunks:
            self.ai_panel.update_hunk(file_hunks[0])
    
    def on_hunk_resolved(self, message: HunkResolved) -> None:
        """Handle hunk resolution from the diff view panel."""
        # Update the hunk's resolved_text
        message.hunk.resolved_text = message.resolved_text
        
        # Refresh file list to show updated progress
        if self.file_list_panel:
            self.file_list_panel._refresh_rows()
        
        # Move to next hunk if available
        if self.diff_view_panel:
            current_idx = self.diff_view_panel.current_hunk_index
            if current_idx < len(self.diff_view_panel.hunks) - 1:
                self.diff_view_panel.current_hunk_index += 1
                self.diff_view_panel._refresh_view()
                
                # Update AI panel
                if self.ai_panel:
                    next_hunk = self.diff_view_panel.get_current_hunk()
                    self.ai_panel.update_hunk(next_hunk)
    
    def action_cycle_focus(self) -> None:
        """Cycle focus between panels."""
        # Get all focusable widgets
        focusable = [self.file_list_panel, self.diff_view_panel, self.ai_panel]
        focusable = [w for w in focusable if w is not None]
        
        if not focusable:
            return
        
        # Find current focused widget
        current = self.focused
        
        if current in focusable:
            current_idx = focusable.index(current)
            next_idx = (current_idx + 1) % len(focusable)
            focusable[next_idx].focus()
        else:
            # Focus first panel
            focusable[0].focus()
    
    def action_commit(self) -> None:
        """Handle commit action (placeholder for now)."""
        # Check if all hunks are resolved
        unresolved = [h for h in self.hunks if h.resolved_text is None]
        
        if unresolved:
            self.bell()
            # In a real implementation, show a modal with the count
        else:
            # All resolved - would trigger commit flow
            self.bell()
    
    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

# Made with Bob
