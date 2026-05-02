"""AI analysis panel showing Bob's insights and suggestions."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static
from rich.text import Text

from git.parser import ConflictHunk


class AIPanelWidget(Widget):
    """
    Right panel showing AI analysis and suggestions.
    
    Displays:
    - AI summary of the conflict
    - AI suggestion for resolution
    - Placeholder when analysis is pending
    """
    
    DEFAULT_CSS = """
    AIPanelWidget {
        width: 25%;
        border: solid $primary;
    }
    
    AIPanelWidget > VerticalScroll {
        height: 100%;
        padding: 1;
    }
    
    .ai-header {
        text-style: bold;
        color: $accent;
        padding: 0 0 1 0;
    }
    
    .ai-summary {
        padding: 0 0 2 0;
    }
    
    .ai-suggestion {
        padding: 0 0 1 0;
    }
    
    .ai-pending {
        color: $text 50%;
        text-style: italic;
    }
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.current_hunk: ConflictHunk | None = None
    
    def compose(self) -> ComposeResult:
        """Compose the AI panel."""
        with VerticalScroll():
            yield self._create_content()
    
    def _create_content(self) -> Static:
        """Create the content for the current hunk."""
        text = Text()
        
        if self.current_hunk is None:
            text.append("Select a conflict to see AI analysis", style="dim italic")
            return Static(text)
        
        # Check if AI analysis is available
        if self.current_hunk.ai_summary or self.current_hunk.ai_suggestion:
            # Show AI analysis
            if self.current_hunk.ai_summary:
                text.append("BOB SAYS\n", style="bold cyan")
                text.append(self.current_hunk.ai_summary + "\n\n")
            
            if self.current_hunk.ai_suggestion:
                text.append("SUGGESTION:\n", style="bold green")
                text.append(self.current_hunk.ai_suggestion + "\n")
        else:
            # Show pending message
            text.append("🤖 Bob is thinking...\n\n", style="bold cyan")
            text.append("Analysis pending\n", style="dim italic")
            text.append("\nFile: ", style="dim")
            text.append(f"{self.current_hunk.file}\n", style="")
            text.append("Type: ", style="dim")
            text.append(f"{self.current_hunk.kind}\n", style="")
            text.append("Severity: ", style="dim")
            
            severity_colors = {1: "green", 2: "yellow", 3: "red"}
            severity_labels = {1: "Low", 2: "Medium", 3: "High"}
            severity_color = severity_colors.get(self.current_hunk.severity, "white")
            severity_label = severity_labels.get(self.current_hunk.severity, "Unknown")
            text.append(f"{severity_label}\n", style=severity_color)
        
        return Static(text)
    
    def update_hunk(self, hunk: ConflictHunk | None) -> None:
        """
        Update the displayed hunk.
        
        This method will be called when the user navigates to a different hunk.
        In a future task, this will trigger AI analysis if not already done.
        
        Args:
            hunk: The ConflictHunk to display, or None to clear
        """
        self.current_hunk = hunk
        self._refresh_content()
    
    def _refresh_content(self) -> None:
        """Refresh the display to show updated content."""
        scroll = self.query_one(VerticalScroll)
        scroll.remove_children()
        scroll.mount(self._create_content())

# Made with Bob
