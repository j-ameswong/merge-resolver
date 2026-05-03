"""File list panel showing conflicted files with severity indicators."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Union
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from rich.text import Text

from git.parser import ConflictHunk


@dataclass
class FileNode:
    """Node data for a file in the tree."""
    filename: str


@dataclass
class HunkNode:
    """Node data for a hunk in the tree."""
    hunk: ConflictHunk


NodeData = Union[FileNode, HunkNode]


class FileSelected(Message):
    """Message emitted when a file is selected."""
    
    def __init__(self, filename: str) -> None:
        self.filename = filename
        super().__init__()


class HunkSelected(Message):
    """Message emitted when a hunk is selected."""
    
    def __init__(self, hunk: ConflictHunk) -> None:
        self.hunk = hunk
        super().__init__()


class FileListPanel(Widget):
    """
    Left panel showing tree of conflicted files with expandable hunks.
    
    Each file node displays:
    - Severity indicator (● in red/yellow/green)
    - Filename (truncated if needed)
    - Conflict type badge [mechanical]/[logical]/[structural]
    - Resolution progress (e.g., "2/3")
    
    Each hunk child displays:
    - Line range (e.g., "L120-145")
    - Resolution status (✓ resolved / ○ unresolved)
    """
    
    can_focus = True

    DEFAULT_CSS = """
    FileListPanel {
        width: 28%;
        border: solid $primary;
    }
    
    FileListPanel > Tree {
        height: 100%;
        padding: 0 1;
    }
    
    Tree {
        background: $surface;
    }
    
    Tree > .tree--cursor {
        background: $accent;
    }
    """
    
    def __init__(self, hunks: list[ConflictHunk]) -> None:
        super().__init__()
        self.hunks = hunks
        self._last_key = None  # Track last key for gg motion
        self._group_hunks()
    
    def _group_hunks(self) -> None:
        """Group hunks by file and calculate stats."""
        self.file_groups: dict[str, list[ConflictHunk]] = defaultdict(list)
        
        for hunk in self.hunks:
            self.file_groups[hunk.file].append(hunk)
        
        self.filenames = sorted(self.file_groups.keys())
    
    def compose(self) -> ComposeResult:
        """Compose the file list tree."""
        tree: Tree[NodeData] = Tree("Files", data=None)
        tree.show_root = False
        yield tree
    
    def on_mount(self) -> None:
        """Populate the tree after mounting."""
        tree = self.query_one(Tree)
        
        if not self.filenames:
            # Add a placeholder node
            tree.root.add_leaf("[dim]No conflicts found[/dim]")
        else:
            for filename in self.filenames:
                self._add_file_node(tree.root, filename)
    
    def _add_file_node(self, parent: TreeNode, filename: str) -> TreeNode:
        """Add a file node with its hunk children to the tree."""
        hunks = self.file_groups[filename]
        
        # Calculate file-level stats
        max_severity = max(h.severity for h in hunks)
        kind_counts = defaultdict(int)
        for h in hunks:
            kind_counts[h.kind] += 1
        most_common_kind = max(kind_counts.items(), key=lambda x: x[1])[0]
        
        resolved_count = sum(1 for h in hunks if h.resolved_text is not None)
        total_count = len(hunks)
        
        # Build file node label
        label = self._format_file_label(filename, max_severity, most_common_kind, 
                                       resolved_count, total_count)
        
        # Add file node
        file_node = parent.add(label, data=FileNode(filename), allow_expand=True)
        
        # Add hunk children
        for hunk in hunks:
            hunk_label = self._format_hunk_label(hunk)
            file_node.add_leaf(hunk_label, data=HunkNode(hunk))
        
        return file_node
    
    def _format_file_label(self, filename: str, severity: int, kind: str,
                          resolved: int, total: int) -> Text:
        """Format a file node label."""
        # Severity indicator
        severity_colors = {1: "green", 2: "yellow", 3: "red"}
        severity_color = severity_colors[severity]
        
        # Truncate filename if too long
        display_name = filename
        if len(display_name) > 25:
            display_name = "..." + display_name[-22:]
        
        # Build the label
        text = Text()
        text.append("● ", style=severity_color)
        text.append(display_name, style="bold")
        text.append(f" [{kind}] ", style="dim")
        text.append(f"{resolved}/{total}", style="cyan")
        
        return text
    
    def _format_hunk_label(self, hunk: ConflictHunk) -> Text:
        """Format a hunk node label with line range and resolution status."""
        # Calculate end line (start_line + number of lines in the conflict)
        # The conflict spans from start_line through all ours/base/theirs lines
        num_lines = len(hunk.ours) + len(hunk.base) + len(hunk.theirs)
        end_line = hunk.start_line + num_lines - 1
        
        # Resolution status
        status = "✓" if hunk.resolved_text is not None else "○"
        status_color = "green" if hunk.resolved_text is not None else "dim"
        
        # Build the label
        text = Text()
        text.append(f"L{hunk.start_line}-{end_line}  ", style="dim")
        text.append(status, style=status_color)
        
        return text
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        node = event.node
        
        if node.data is None:
            return
        
        if isinstance(node.data, FileNode):
            # File node selected - emit FileSelected message
            self.post_message(FileSelected(node.data.filename))
        elif isinstance(node.data, HunkNode):
            # Hunk node selected - emit HunkSelected message
            self.post_message(HunkSelected(node.data.hunk))
    
    def on_key(self, event) -> None:
        """Handle keyboard navigation with vim motions."""
        tree = self.query_one(Tree)
        
        # Translate vim motions to tree cursor movements
        if event.key in ("j", "down"):
            tree.action_cursor_down()
            self._last_key = None
            event.prevent_default()
        elif event.key in ("k", "up"):
            tree.action_cursor_up()
            self._last_key = None
            event.prevent_default()
        elif event.key == "g":
            if self._last_key == "g":
                # gg - go to first node
                tree.action_select_cursor()  # Ensure something is selected
                tree.cursor_line = 0
                tree.scroll_to_line(0)
                self._last_key = None
                event.prevent_default()
            else:
                # First g, wait for second
                self._last_key = "g"
                event.prevent_default()
        elif event.key == "G":
            # G - go to last node
            # Find the last visible line in the tree
            last_line = len(list(tree.root.children)) - 1
            if last_line >= 0:
                tree.cursor_line = last_line
                tree.scroll_to_line(last_line)
            self._last_key = None
            event.prevent_default()
        else:
            # Reset gg sequence on any other key
            self._last_key = None
    
    def refresh_labels(self) -> None:
        """
        Refresh all node labels to reflect current resolution state.
        
        This updates the ✓/○ status on hunk nodes and the n/total count on file nodes
        without rebuilding the tree (preserves expansion state and cursor position).
        """
        tree = self.query_one(Tree)
        
        for file_node in tree.root.children:
            if not isinstance(file_node.data, FileNode):
                continue
            
            filename = file_node.data.filename
            hunks = self.file_groups[filename]
            
            # Recalculate file-level stats
            max_severity = max(h.severity for h in hunks)
            kind_counts = defaultdict(int)
            for h in hunks:
                kind_counts[h.kind] += 1
            most_common_kind = max(kind_counts.items(), key=lambda x: x[1])[0]
            
            resolved_count = sum(1 for h in hunks if h.resolved_text is not None)
            total_count = len(hunks)
            
            # Update file node label
            file_node.label = self._format_file_label(filename, max_severity, 
                                                     most_common_kind, resolved_count, 
                                                     total_count)
            
            # Update hunk child labels
            for hunk_node in file_node.children:
                if isinstance(hunk_node.data, HunkNode):
                    hunk_node.label = self._format_hunk_label(hunk_node.data.hunk)
        
        tree.refresh()
    
    def expand_file(self, filename: str) -> None:
        """
        Expand the node for the given file and collapse all siblings.
        
        Args:
            filename: The file whose node should be expanded
        """
        tree = self.query_one(Tree)
        
        for file_node in tree.root.children:
            if not isinstance(file_node.data, FileNode):
                continue
            
            if file_node.data.filename == filename:
                file_node.expand()
            else:
                file_node.collapse()
    
    def get_selected_filename(self) -> str | None:
        """Get the currently selected filename (for initial load)."""
        if self.filenames:
            return self.filenames[0]
        return None

# Made with Bob
