"""Diff view panel showing conflict hunks with resolution actions."""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static
from rich.text import Text

from git.parser import ConflictHunk


class HunkResolved(Message):
    """Message emitted when a hunk is resolved."""
    
    def __init__(self, hunk: ConflictHunk, resolved_text: str) -> None:
        self.hunk = hunk
        self.resolved_text = resolved_text
        super().__init__()


class HunkChanged(Message):
    """Message emitted when the current hunk changes (navigation)."""
    
    def __init__(self, hunk: ConflictHunk) -> None:
        self.hunk = hunk
        super().__init__()


class DiffViewPanel(Widget):
    """
    Center panel showing conflict hunks with resolution actions.
    
    Displays one hunk at a time with:
    - Hunk header (index/total)
    - Ours lines (green background)
    - Base lines (dimmed)
    - Theirs lines (red background)
    - Action buttons
    """
    
    DEFAULT_CSS = """
    DiffViewPanel {
        width: 55%;
        border: solid $primary;
    }
    
    DiffViewPanel > VerticalScroll {
        height: 100%;
    }
    
    .hunk-header {
        background: $panel;
        padding: 0 1;
        text-align: center;
    }
    
    .hunk-section {
        padding: 1;
    }
    
    .ours-line {
        background: $success 20%;
        color: $success;
    }
    
    .theirs-line {
        background: $error 20%;
        color: $error;
    }
    
    .base-line {
        color: $text 50%;
    }
    
    .actions {
        padding: 1;
        background: $panel;
    }
    """
    
    def __init__(self, hunks: list[ConflictHunk] | None = None) -> None:
        super().__init__()
        self.hunks = hunks or []
        self.current_hunk_index = 0
        self._last_key = None  # Track last key for gg motion
    
    def compose(self) -> ComposeResult:
        """Compose the diff view."""
        with VerticalScroll():
            if not self.hunks:
                yield Static("[dim]Select a file to view conflicts[/dim]")
            else:
                for widget in self._create_hunk_widgets():
                    yield widget
    
    def _create_hunk_widgets(self) -> list[Widget]:
        """Create widgets for the current hunk."""
        widgets = []
        
        if not self.hunks:
            widgets.append(Static("[dim]No hunks to display[/dim]"))
            return widgets
        
        hunk = self.hunks[self.current_hunk_index]
        total = len(self.hunks)
        
        # Header
        header_text = f"~~~ HUNK {self.current_hunk_index + 1} of {total} ~~~"
        header = Static(header_text)
        header.add_class("hunk-header")
        widgets.append(header)
        
        # Ours section
        ours_section = Static(self._format_section("OURS", hunk.ours, "ours-line"))
        ours_section.add_class("hunk-section")
        widgets.append(ours_section)
        
        # Base section
        if hunk.base:
            base_section = Static(self._format_section("BASE", hunk.base, "base-line"))
            base_section.add_class("hunk-section")
            widgets.append(base_section)
        
        # Theirs section
        theirs_section = Static(self._format_section("THEIRS", hunk.theirs, "theirs-line"))
        theirs_section.add_class("hunk-section")
        widgets.append(theirs_section)
        
        # Actions
        actions_text = Text()
        actions_text.append("[A] Accept Ours  ", style="bold green")
        actions_text.append("[B] Accept Theirs  ", style="bold red")
        actions_text.append("[E] Edit  ", style="bold yellow")
        actions_text.append("[S] Bob's suggestion", style="bold cyan")
        
        actions = Static(actions_text)
        actions.add_class("actions")
        widgets.append(actions)
        
        return widgets
    
    def _format_section(self, label: str, lines: list[str], style_class: str) -> Text:
        """Format a section (ours/base/theirs) with line prefixes."""
        text = Text()
        
        # Determine style based on section type
        if style_class == "ours-line":
            prefix = "< "
            style = "green"
        elif style_class == "theirs-line":
            prefix = "> "
            style = "red"
        else:  # base-line
            prefix = "| "
            style = "dim"
        
        # Section label
        text.append(f"{prefix}{label}\n", style="bold")
        
        # Lines with prefix and style
        for line in lines:
            # Remove trailing newline if present
            line_text = line.rstrip('\n')
            text.append(prefix + line_text + "\n", style=style)
        
        return text
    
    def update_hunks(self, hunks: list[ConflictHunk]) -> None:
        """Update the hunks being displayed."""
        self.hunks = hunks
        self.current_hunk_index = 0
        self._refresh_view()
    
    def _refresh_view(self) -> None:
        """Refresh the display to show the current hunk."""
        scroll = self.query_one(VerticalScroll)
        scroll.remove_children()
        
        if not self.hunks:
            scroll.mount(Static("[dim]Select a file to view conflicts[/dim]"))
        else:
            for widget in self._create_hunk_widgets():
                scroll.mount(widget)
    
    def on_key(self, event) -> None:
        """Handle keyboard navigation and actions with vim motions."""
        if not self.hunks:
            return
        
        # Vim motions: j for next, k for previous (in addition to n/p)
        if event.key in ("n", "j"):
            # Next hunk
            old_index = self.current_hunk_index
            self.current_hunk_index = min(len(self.hunks) - 1, self.current_hunk_index + 1)
            self._refresh_view()
            if old_index != self.current_hunk_index:
                self.post_message(HunkChanged(self.hunks[self.current_hunk_index]))
            self._last_key = None
            event.prevent_default()
        elif event.key in ("p", "k"):
            # Previous hunk
            old_index = self.current_hunk_index
            self.current_hunk_index = max(0, self.current_hunk_index - 1)
            self._refresh_view()
            if old_index != self.current_hunk_index:
                self.post_message(HunkChanged(self.hunks[self.current_hunk_index]))
            self._last_key = None
            event.prevent_default()
        # Vim motions: gg for first, G for last
        elif event.key == "g":
            if self._last_key == "g":
                # gg - go to first hunk
                old_index = self.current_hunk_index
                self.current_hunk_index = 0
                self._refresh_view()
                if old_index != self.current_hunk_index:
                    self.post_message(HunkChanged(self.hunks[self.current_hunk_index]))
                self._last_key = None
                event.prevent_default()
            else:
                # First g, wait for second
                self._last_key = "g"
                event.prevent_default()
        elif event.key == "G":
            # G - go to last hunk
            old_index = self.current_hunk_index
            self.current_hunk_index = len(self.hunks) - 1
            self._refresh_view()
            if old_index != self.current_hunk_index:
                self.post_message(HunkChanged(self.hunks[self.current_hunk_index]))
            self._last_key = None
            event.prevent_default()
        elif event.key == "a":
            # Accept ours
            self._resolve_with_ours()
            self._last_key = None
            event.prevent_default()
        elif event.key == "b":
            # Accept theirs
            self._resolve_with_theirs()
            self._last_key = None
            event.prevent_default()
        elif event.key == "s":
            # Accept Bob's suggestion
            self._resolve_with_suggestion()
            self._last_key = None
            event.prevent_default()
        elif event.key == "e":
            # Edit manually (placeholder for now)
            self.app.bell()
            self._last_key = None
            event.prevent_default()
        else:
            # Reset gg sequence on any other key
            self._last_key = None
    
    def _resolve_with_ours(self) -> None:
        """Resolve current hunk by accepting ours."""
        if not self.hunks:
            return
        
        hunk = self.hunks[self.current_hunk_index]
        resolved_text = "".join(hunk.ours)
        self.post_message(HunkResolved(hunk, resolved_text))
    
    def _resolve_with_theirs(self) -> None:
        """Resolve current hunk by accepting theirs."""
        if not self.hunks:
            return
        
        hunk = self.hunks[self.current_hunk_index]
        resolved_text = "".join(hunk.theirs)
        self.post_message(HunkResolved(hunk, resolved_text))
    
    def _resolve_with_suggestion(self) -> None:
        """Resolve current hunk using Bob's suggestion."""
        if not self.hunks:
            return
        
        hunk = self.hunks[self.current_hunk_index]
        
        # For now, use ai_suggestion if available, otherwise fall back to ours
        if hunk.ai_suggestion:
            resolved_text = hunk.ai_suggestion
        else:
            # No suggestion yet, just use ours as fallback
            resolved_text = "".join(hunk.ours)
        
        self.post_message(HunkResolved(hunk, resolved_text))
    
    def get_current_hunk(self) -> ConflictHunk | None:
        """Get the currently displayed hunk."""
        if self.hunks and 0 <= self.current_hunk_index < len(self.hunks):
            return self.hunks[self.current_hunk_index]
        return None

# Made with Bob
