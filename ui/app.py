"""Main Textual application for merge-resolver."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widget import Widget
from textual.widgets import Header, Footer, Label, Button, Input, TextArea
from textual.binding import Binding
from textual.screen import ModalScreen
from textual import work

from git.parser import ConflictHunk
from git.state import find_repo_root
from ui.file_list import FileListPanel, FileSelected, HunkSelected
from ui.diff_view import DiffViewPanel, HunkResolved, HunkChanged, HunkEditRequested
from ui.ai_panel import AIPanelWidget
from resolver.apply import apply_all, stage_file, commit, all_resolved


class UnresolvedHunksModal(ModalScreen):
    """Modal screen showing unresolved hunks with option to commit anyway."""
    
    CSS = """
    UnresolvedHunksModal {
        align: center middle;
    }
    
    #dialog {
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #message {
        width: 100%;
        height: auto;
        content-align: center middle;
        padding: 1 0;
    }
    
    #buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 0;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, unresolved_hunks: list[ConflictHunk]) -> None:
        super().__init__()
        self.unresolved_hunks = unresolved_hunks
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(
                f"⚠️  {len(self.unresolved_hunks)} unresolved hunks remaining",
                id="message"
            )
            
            # List first few unresolved files
            files = list(set(h.file for h in self.unresolved_hunks))[:5]
            file_list = "\n".join(f"  • {f}" for f in files)
            if len(files) < len(set(h.file for h in self.unresolved_hunks)):
                file_list += "\n  ..."
            
            yield Label(file_list)
            yield Label("\nCommit anyway? (partial resolution)", id="message")
            
            with Horizontal(id="buttons"):
                yield Button("Yes", variant="error", id="yes")
                yield Button("No", variant="primary", id="no")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)


class CommitMessageModal(ModalScreen):
    """Modal screen for entering commit message."""
    
    CSS = """
    CommitMessageModal {
        align: center middle;
    }
    
    #dialog {
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #message {
        width: 100%;
        height: auto;
        content-align: center middle;
        padding: 1 0;
    }
    
    Input {
        width: 100%;
        margin: 1 0;
    }
    
    #buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 0;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, default_message: str) -> None:
        super().__init__()
        self.default_message = default_message
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Enter commit message:", id="message")
            yield Input(
                value=self.default_message,
                placeholder="Commit message",
                id="commit_input"
            )
            
            with Horizontal(id="buttons"):
                yield Button("Commit", variant="success", id="commit")
                yield Button("Cancel", variant="default", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#commit_input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "commit_input":
            self.dismiss(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "commit":
            input_widget = self.query_one("#commit_input", Input)
            self.dismiss(input_widget.value)
        else:
            self.dismiss(None)


class EditModal(ModalScreen):
    """Modal screen for manually editing a hunk's resolved text."""

    CSS = """
    EditModal {
        align: center middle;
    }

    #dialog {
        width: 80%;
        height: 80%;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    #title {
        width: 100%;
        text-align: center;
        text-style: bold;
        padding: 0 0 1 0;
    }

    TextArea {
        height: 1fr;
        margin: 1 0;
    }

    #buttons {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 0;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(self, initial_text: str) -> None:
        super().__init__()
        self.initial_text = initial_text

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Edit resolution (Ctrl+S to save, Esc to cancel)", id="title")
            yield TextArea(self.initial_text, id="editor")
            with Horizontal(id="buttons"):
                yield Button("Save", variant="success", id="save")
                yield Button("Cancel", variant="default", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#editor", TextArea).focus()

    def action_save(self) -> None:
        self.dismiss(self.query_one("#editor", TextArea).text)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.action_save()
        else:
            self.action_cancel()


class ErrorModal(ModalScreen):
    """Modal screen for displaying errors."""
    
    CSS = """
    ErrorModal {
        align: center middle;
    }
    
    #dialog {
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #message {
        width: 100%;
        height: auto;
        padding: 1 0;
    }
    
    Button {
        width: 100%;
        margin: 1 0;
    }
    """
    
    def __init__(self, error_message: str) -> None:
        super().__init__()
        self.error_message = error_message
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(f"❌ Error\n\n{self.error_message}", id="message")
            yield Button("OK", variant="error", id="ok")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


class SuccessModal(ModalScreen):
    """Modal screen for displaying success message."""
    
    CSS = """
    SuccessModal {
        align: center middle;
    }
    
    #dialog {
        width: 40;
        height: auto;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #message {
        width: 100%;
        height: auto;
        content-align: center middle;
        padding: 1 0;
    }
    """
    
    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(f"✓ {self.message}", id="message")


class HelpModal(ModalScreen):
    """Modal screen showing keyboard shortcuts."""
    
    CSS = """
    HelpModal {
        align: center middle;
    }
    
    #dialog {
        width: 70;
        height: auto;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }
    
    #title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 0 0 1 0;
    }
    
    #shortcuts {
        width: 100%;
        height: auto;
        padding: 1 0;
    }
    
    Button {
        width: 100%;
        margin: 1 0;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("⌨️  Keyboard Shortcuts", id="title")
            
            shortcuts_text = """
╔═══════════════════════════════════════════════════════════════╗
║ GLOBAL SHORTCUTS                                              ║
╠═══════════════════════════════════════════════════════════════╣
║  Tab          Cycle between panels                            ║
║  h            Focus panel to the left                         ║
║  l            Focus panel to the right                        ║
║  ?            Show this help                                  ║
║  c            Commit resolved changes                         ║
║  q            Quit application                                ║
╠═══════════════════════════════════════════════════════════════╣
║ FILE LIST PANEL (Left)                                        ║
╠═══════════════════════════════════════════════════════════════╣
║  ↑/↓ or j/k   Navigate files/hunks                            ║
║  Enter        Toggle expand (file) / jump to hunk (hunk)      ║
║  Note: Current file auto-expands when center panel focused    ║
╠═══════════════════════════════════════════════════════════════╣
║ DIFF VIEW PANEL (Center)                                      ║
╠═══════════════════════════════════════════════════════════════╣
║  n or j       Next hunk                                       ║
║  p or k       Previous hunk                                   ║
║  gg           Jump to first hunk                              ║
║  G            Jump to last hunk                               ║
║  a            Accept OURS (current branch)                    ║
║  b            Accept THEIRS (incoming branch)                 ║
║  s            Accept Bob's AI suggestion                      ║
║  e            Edit manually (not yet implemented)             ║
╠═══════════════════════════════════════════════════════════════╣
║ CONFLICT TYPES                                                ║
╠═══════════════════════════════════════════════════════════════╣
║  🟢 Mechanical   Simple, non-overlapping changes (low risk)   ║
║  🟡 Logical      Same symbols modified (medium risk)          ║
║  🔴 Structural   Cross-file symbol conflicts (high risk)      ║
╚═══════════════════════════════════════════════════════════════╝
"""
            yield Label(shortcuts_text, id="shortcuts")
            yield Button("Close", variant="primary", id="close")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


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

    FileListPanel.panel-active,
    DiffViewPanel.panel-active,
    AIPanelWidget.panel-active {
        border: round yellow;
    }

    FileListPanel.panel-focused,
    DiffViewPanel.panel-focused,
    AIPanelWidget.panel-focused {
        border: round cyan;
    }
    """
    
    BINDINGS = [
        Binding("tab", "cycle_focus", "Switch Panel", show=True),
        Binding("h", "focus_left", "← Panel", show=True, priority=True),
        Binding("l", "focus_right", "→ Panel", show=True, priority=True),
        Binding("question_mark", "show_help", "Help", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("c", "commit", "Commit", show=True),
    ]
    
    def __init__(
        self,
        hunks: list[ConflictHunk],
        ours_branch: str = "HEAD",
        theirs_branch: str = "MERGE_HEAD",
        repo_root: Path | None = None,
    ) -> None:
        super().__init__()
        self.hunks = hunks
        self.ours_branch = ours_branch
        self.theirs_branch = theirs_branch
        self.repo_root = repo_root
        
        # Track current state
        self.current_file: str | None = None
        self._expanded_file: str | None = None
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

        self._update_panel_classes()

    def _panels(self) -> list[Widget]:
        return [p for p in (self.file_list_panel, self.diff_view_panel, self.ai_panel) if p is not None]

    def _focused_panel(self):
        focused = self.focused
        if focused is None:
            return None
        for panel in self._panels():
            if focused is panel or panel in focused.ancestors:
                return panel
        return None

    def _update_panel_classes(self) -> None:
        """Apply panel-focused (cyan) and panel-active (yellow) classes.

        Active = the diff panel, since that's where the current hunk lives.
        Focused wins over active when both apply to the same panel.
        """
        focused_panel = self._focused_panel()
        for panel in self._panels():
            panel.remove_class("panel-focused")
            panel.remove_class("panel-active")
        if self.diff_view_panel is not None and self.diff_view_panel is not focused_panel:
            self.diff_view_panel.add_class("panel-active")
        if focused_panel is not None:
            focused_panel.add_class("panel-focused")
    
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
        
        # Update AI panel with first hunk and start analysis
        if self.ai_panel and file_hunks:
            first_hunk = file_hunks[0]
            self.ai_panel.update_hunk(first_hunk)
            self.ai_panel.start_analysis(first_hunk, self.ours_branch, self.theirs_branch)

        if self.file_list_panel and file_hunks:
            self.file_list_panel.set_current_hunk(file_hunks[0])
    
    def on_hunk_resolved(self, message: HunkResolved) -> None:
        """Handle hunk resolution from the diff view panel."""
        # Update the hunk's resolved_text
        message.hunk.resolved_text = message.resolved_text
        
        # Refresh file list to show updated progress
        if self.file_list_panel:
            self.file_list_panel.refresh_labels()
        
        # Move to next hunk if available
        if self.diff_view_panel:
            current_idx = self.diff_view_panel.current_hunk_index
            if current_idx < len(self.diff_view_panel.hunks) - 1:
                self.diff_view_panel.current_hunk_index += 1
                self.diff_view_panel._refresh_view()
                
                # Update AI panel and start analysis
                next_hunk = self.diff_view_panel.get_current_hunk()
                if next_hunk:
                    if self.ai_panel:
                        self.ai_panel.update_hunk(next_hunk)
                        self.ai_panel.start_analysis(next_hunk, self.ours_branch, self.theirs_branch)
                    if self.file_list_panel:
                        self.file_list_panel.set_current_hunk(next_hunk)
    
    def on_hunk_selected(self, message: HunkSelected) -> None:
        """Handle hunk selection from the file list panel."""
        # If the hunk is from a different file, load that file first
        if message.hunk.file != self.current_file:
            self._load_file(message.hunk.file)
        
        # Jump to the selected hunk in the diff view
        if self.diff_view_panel:
            self.diff_view_panel.jump_to_hunk(message.hunk)

        # Update AI panel
        if self.ai_panel:
            self.ai_panel.update_hunk(message.hunk)
            self.ai_panel.start_analysis(message.hunk, self.ours_branch, self.theirs_branch)

        if self.file_list_panel:
            self.file_list_panel.set_current_hunk(message.hunk)
    
    @work
    async def on_hunk_edit_requested(self, message: HunkEditRequested) -> None:
        """Open the edit modal so the user can manually craft a resolution."""
        hunk = message.hunk
        if hunk.resolved_text is not None:
            initial = hunk.resolved_text
        else:
            initial = "".join(hunk.ours)
        result = await self.push_screen_wait(EditModal(initial))
        if result is None:
            return
        self.post_message(HunkResolved(hunk, result))

    def on_hunk_changed(self, message: HunkChanged) -> None:
        """Handle hunk navigation from the diff view panel."""
        # Update AI panel and start analysis for the new hunk
        if self.ai_panel:
            self.ai_panel.update_hunk(message.hunk)
            self.ai_panel.start_analysis(message.hunk, self.ours_branch, self.theirs_branch)
        if self.file_list_panel:
            self.file_list_panel.set_current_hunk(message.hunk)
    
    def on_descendant_focus(self, event) -> None:
        """Handle focus changes to auto-expand the current file in the tree."""
        self._update_panel_classes()
        if not (self.diff_view_panel and self.file_list_panel and self.current_file):
            return
        focused = event.widget
        # Match focus on the diff panel itself OR any descendant of it.
        in_diff = focused is self.diff_view_panel or focused in self.diff_view_panel.walk_children()
        if not in_diff:
            return
        if self._expanded_file == self.current_file:
            return
        self._expanded_file = self.current_file
        self.file_list_panel.expand_file(self.current_file)
    
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
    
    def action_focus_left(self) -> None:
        """Focus the panel to the left (vim h motion)."""
        # Get all focusable widgets
        focusable = [self.file_list_panel, self.diff_view_panel, self.ai_panel]
        focusable = [w for w in focusable if w is not None]
        
        if not focusable:
            return
        
        # Find current focused widget, walking ancestors if needed
        current = self.focused
        current_panel = next((p for p in focusable if current is p or (current and p in current.ancestors)), None)
        
        if current_panel is not None:
            current_idx = focusable.index(current_panel)
            prev_idx = (current_idx - 1) % len(focusable)
            focusable[prev_idx].focus()
        else:
            # Focus first panel
            focusable[0].focus()
    
    def action_focus_right(self) -> None:
        """Focus the panel to the right (vim l motion)."""
        # Get all focusable widgets
        focusable = [self.file_list_panel, self.diff_view_panel, self.ai_panel]
        focusable = [w for w in focusable if w is not None]
        
        if not focusable:
            return
        
        # Find current focused widget, walking ancestors if needed
        current = self.focused
        current_panel = next((p for p in focusable if current is p or (current and p in current.ancestors)), None)
        
        if current_panel is not None:
            current_idx = focusable.index(current_panel)
            next_idx = (current_idx + 1) % len(focusable)
            focusable[next_idx].focus()
        else:
            # Focus first panel
            focusable[0].focus()
    
    @work
    async def action_commit(self) -> None:
        """Handle commit action with full resolution and commit flow."""
        # Check if all hunks are resolved
        unresolved = [h for h in self.hunks if h.resolved_text is None]
        
        # If there are unresolved hunks, ask user if they want to commit anyway
        if unresolved:
            result = await self.push_screen_wait(UnresolvedHunksModal(unresolved))
            if not result:
                # User chose not to commit
                return
        
        # Get commit message from user
        default_message = "Resolve merge conflicts (merge-resolver)"
        commit_message = await self.push_screen_wait(CommitMessageModal(default_message))
        
        if commit_message is None:
            # User cancelled
            return
        
        # Apply all resolved hunks
        try:
            repo_root = self.repo_root if self.repo_root is not None else find_repo_root()
            
            # Apply resolved hunks to files
            resolved_files = apply_all(self.hunks, repo_root)
            
            if not resolved_files:
                await self.push_screen_wait(ErrorModal("No resolved hunks to commit"))
                return
            
            # Stage each modified file
            for filepath in resolved_files.keys():
                stage_file(filepath, repo_root)
            
            # Commit
            commit(commit_message, repo_root)
            
            # Show success message
            await self.push_screen(SuccessModal("Committed successfully"))

            # Wait 2 seconds then quit
            self.set_timer(2.0, self.exit)
            
        except Exception as e:
            await self.push_screen_wait(ErrorModal(f"Commit failed:\n{str(e)}"))
    
    @work
    async def action_show_help(self) -> None:
        """Show keyboard shortcuts help modal."""
        await self.push_screen_wait(HelpModal())
    
    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

# Made with Bob
