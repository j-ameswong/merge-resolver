"""AI analysis panel showing Bob's insights and suggestions."""

import threading

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static, LoadingIndicator
from rich.text import Text

from git.parser import ConflictHunk
from analysis.bob import analyse_hunk


class AIPanelWidget(Widget):
    """
    Right panel showing AI analysis and suggestions.
    
    Displays:
    - AI summary of the conflict
    - AI suggestion for resolution
    - Placeholder when analysis is pending
    """
    
    can_focus = True
    
    DEFAULT_CSS = """
    AIPanelWidget {
        width: 22%;
        border: round $background 60%;
        overflow-x: hidden;
    }

    AIPanelWidget > VerticalScroll {
        height: 100%;
        width: 100%;
        padding: 1;
        overflow-x: hidden;
    }

    AIPanelWidget Static {
        width: 100%;
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
        self.is_analysing: bool = False
        self.analysis_thread: threading.Thread | None = None
    
    def compose(self) -> ComposeResult:
        """Compose the AI panel."""
        with VerticalScroll():
            yield self._create_content()
    
    def _create_content(self) -> Widget:
        """Create the content for the current hunk."""
        if self.current_hunk is None:
            text = Text("Select a conflict to see AI analysis", style="dim italic")
            return Static(text)
        
        # Show loading indicator while analysing
        if self.is_analysing:
            return LoadingIndicator()
        
        # Check if AI analysis is available
        text = Text()
        if self.current_hunk.ai_summary or self.current_hunk.ai_suggestion:
            # Show AI analysis
            if self.current_hunk.ai_summary:
                text.append("BOB SAYS\n", style="bold cyan")
                text.append(self.current_hunk.ai_summary + "\n\n")
            
            if self.current_hunk.ai_suggestion:
                text.append("SUGGESTION:\n", style="bold green")
                text.append(self.current_hunk.ai_suggestion + "\n")
            
            # Show related files for structural conflicts
            if self.current_hunk.kind == "structural" and self.current_hunk.related_files:
                text.append("\n⚠ RELATED FILES:\n", style="bold yellow")
                text.append("These files share symbols with this conflict:\n", style="dim")
                for related_file in self.current_hunk.related_files:
                    text.append(f"  • {related_file}\n", style="yellow")
        else:
            # Show pending message (analysis not started yet)
            text.append("🤖 Bob is ready to analyse\n\n", style="bold cyan")
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
            
            # Show related files for structural conflicts even before AI analysis
            if self.current_hunk.kind == "structural" and self.current_hunk.related_files:
                text.append("\n⚠ RELATED FILES:\n", style="bold yellow")
                text.append("These files share symbols with this conflict:\n", style="dim")
                for related_file in self.current_hunk.related_files:
                    text.append(f"  • {related_file}\n", style="yellow")
        
        return Static(text)
    
    def update_hunk(self, hunk: ConflictHunk | None) -> None:
        """
        Update the displayed hunk.
        
        This method will be called when the user navigates to a different hunk.
        
        Args:
            hunk: The ConflictHunk to display, or None to clear
        """
        self.current_hunk = hunk
        self.is_analysing = False
        self._refresh_content()
    
    def start_analysis(
        self,
        hunk: ConflictHunk,
        ours_branch: str,
        theirs_branch: str
    ) -> None:
        """
        Start AI analysis for a hunk in a background thread.
        
        Shows a loading indicator while the analysis is running, then updates
        the display with the results.
        
        Args:
            hunk: The ConflictHunk to analyse
            ours_branch: Name of the current branch (HEAD)
            theirs_branch: Name of the incoming branch
        """
        # Don't start if already analysing or already has results
        if self.is_analysing or hunk.ai_summary:
            return
        
        self.is_analysing = True
        self._refresh_content()
        
        def analyse_worker():
            """Worker function that runs in background thread."""
            try:
                # Call the AI analysis
                analyse_hunk(hunk, ours_branch, theirs_branch)
            finally:
                # Update UI on main thread using call_from_thread
                self.is_analysing = False
                self.app.call_from_thread(self._refresh_content)
        
        # Start the background thread
        self.analysis_thread = threading.Thread(target=analyse_worker, daemon=True)
        self.analysis_thread.start()
    
    def _refresh_content(self) -> None:
        """Refresh the display to show updated content."""
        scroll = self.query_one(VerticalScroll)
        scroll.remove_children()
        scroll.mount(self._create_content())

# Made with Bob
