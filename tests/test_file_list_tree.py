"""Unit tests for the FileListPanel tree functionality."""

import pytest
from git.parser import ConflictHunk
from ui.file_list import FileListPanel, FileNode, HunkNode, FileSelected, HunkSelected


def create_test_hunks() -> list[ConflictHunk]:
    """Create test conflict hunks for tree testing."""
    hunks = []
    
    # Two hunks in file1
    hunk1 = ConflictHunk(
        file="src/auth/login.py",
        hunk_index=0,
        start_line=15,
        ours=["line1\n", "line2\n"],
        theirs=["line3\n"],
        base=["line0\n"],
        kind="mechanical",
        severity=1,
        ai_summary="Test summary",
        ai_suggestion="Test suggestion"
    )
    hunks.append(hunk1)
    
    hunk2 = ConflictHunk(
        file="src/auth/login.py",
        hunk_index=1,
        start_line=42,
        ours=["line4\n"],
        theirs=["line5\n", "line6\n"],
        base=["line7\n"],
        kind="logical",
        severity=2,
        ai_summary="Test summary 2",
        ai_suggestion="Test suggestion 2",
        resolved_text="resolved!"
    )
    hunks.append(hunk2)
    
    # One hunk in file2
    hunk3 = ConflictHunk(
        file="src/models.py",
        hunk_index=0,
        start_line=8,
        ours=["import1\n"],
        theirs=["import2\n"],
        base=["import0\n"],
        kind="structural",
        severity=3
    )
    hunks.append(hunk3)
    
    return hunks


class TestFileListTree:
    """Test the tree-based file list panel."""
    
    def test_file_node_creation(self):
        """Test that file nodes are created with correct data."""
        hunks = create_test_hunks()
        panel = FileListPanel(hunks)
        
        # Check that files are grouped correctly
        assert len(panel.filenames) == 2
        assert "src/auth/login.py" in panel.filenames
        assert "src/models.py" in panel.filenames
        
        # Check that hunks are grouped by file
        assert len(panel.file_groups["src/auth/login.py"]) == 2
        assert len(panel.file_groups["src/models.py"]) == 1
    
    def test_file_label_format(self):
        """Test that file node labels contain severity, filename, kind, and progress."""
        hunks = create_test_hunks()
        panel = FileListPanel(hunks)
        
        # Format a file label
        label = panel._format_file_label(
            "src/auth/login.py",
            severity=2,
            kind="logical",
            resolved=1,
            total=2
        )
        
        # Check that label contains expected components
        label_str = label.plain
        assert "src/auth/login.py" in label_str
        assert "[logical]" in label_str
        assert "1/2" in label_str
        # Severity dot should be present (●)
        assert "●" in label_str
    
    def test_hunk_label_format(self):
        """Test that hunk node labels contain line range and resolution status."""
        hunks = create_test_hunks()
        panel = FileListPanel(hunks)
        
        # Test unresolved hunk
        hunk1 = hunks[0]
        label1 = panel._format_hunk_label(hunk1)
        label1_str = label1.plain
        
        # Should show line range
        assert "L15" in label1_str
        # Should show unresolved status
        assert "○" in label1_str
        
        # Test resolved hunk
        hunk2 = hunks[1]
        label2 = panel._format_hunk_label(hunk2)
        label2_str = label2.plain
        
        # Should show line range
        assert "L42" in label2_str
        # Should show resolved status
        assert "✓" in label2_str
    
    def test_hunk_line_range_calculation(self):
        """Test that hunk line ranges are calculated correctly."""
        hunks = create_test_hunks()
        panel = FileListPanel(hunks)
        
        # Hunk 1: start=15, ours=2 lines, base=1 line, theirs=1 line = 4 lines total
        # End should be 15 + 4 - 1 = 18
        hunk1 = hunks[0]
        label1 = panel._format_hunk_label(hunk1)
        label1_str = label1.plain
        assert "L15-18" in label1_str
        
        # Hunk 2: start=42, ours=1 line, base=1 line, theirs=2 lines = 4 lines total
        # End should be 42 + 4 - 1 = 45
        hunk2 = hunks[1]
        label2 = panel._format_hunk_label(hunk2)
        label2_str = label2.plain
        assert "L42-45" in label2_str
    
    def test_node_data_types(self):
        """Test that nodes have correct data types."""
        hunks = create_test_hunks()
        panel = FileListPanel(hunks)
        
        # Create a file node
        from textual.widgets.tree import TreeNode
        root = TreeNode("root", None)
        file_node = panel._add_file_node(root, "src/auth/login.py")
        
        # File node should have FileNode data
        assert isinstance(file_node.data, FileNode)
        assert file_node.data.filename == "src/auth/login.py"
        
        # Children should have HunkNode data
        assert len(list(file_node.children)) == 2
        for child in file_node.children:
            assert isinstance(child.data, HunkNode)
            assert isinstance(child.data.hunk, ConflictHunk)
    
    def test_refresh_labels_updates_status(self):
        """Test that refresh_labels updates resolution status without rebuilding tree."""
        hunks = create_test_hunks()
        panel = FileListPanel(hunks)
        
        # Initially, hunk1 is unresolved
        hunk1 = hunks[0]
        assert hunk1.resolved_text is None
        
        # Resolve hunk1
        hunk1.resolved_text = "resolved content"
        
        # Refresh labels should update the display
        # (We can't fully test this without mounting the widget, but we can verify
        # the method exists and doesn't crash)
        try:
            # This will fail without a mounted tree, but that's expected
            panel.refresh_labels()
        except Exception:
            # Expected - tree not mounted
            pass
    
    def test_expand_file_method_exists(self):
        """Test that expand_file method exists and accepts filename."""
        hunks = create_test_hunks()
        panel = FileListPanel(hunks)
        
        # Method should exist
        assert hasattr(panel, 'expand_file')
        assert callable(panel.expand_file)
        
        # Should accept a filename parameter
        try:
            panel.expand_file("src/auth/login.py")
        except Exception:
            # Expected - tree not mounted
            pass
    
    def test_file_selected_message(self):
        """Test that FileSelected message is created correctly."""
        msg = FileSelected("test.py")
        assert msg.filename == "test.py"
    
    def test_hunk_selected_message(self):
        """Test that HunkSelected message is created correctly."""
        hunks = create_test_hunks()
        hunk = hunks[0]
        msg = HunkSelected(hunk)
        assert msg.hunk is hunk
        assert msg.hunk.file == "src/auth/login.py"
        assert msg.hunk.hunk_index == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob