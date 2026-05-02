"""Tests for resolver/apply.py"""

import tempfile
from pathlib import Path

import pytest

from git.parser import ConflictHunk
from resolver.apply import (
    write_resolved,
    apply_all,
    all_resolved,
)


def test_write_resolved_simple():
    """Test writing a resolved hunk to a file with a single conflict."""
    # Create a temp file with a conflict block
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        test_file = repo_root / "test.py"
        
        conflict_content = """def hello():
<<<<<<< HEAD
    print("Hello from HEAD")
||||||| base
    print("Hello from base")
=======
    print("Hello from branch")
>>>>>>> branch
    return True
"""
        test_file.write_text(conflict_content)
        
        # Create a hunk with resolved text
        hunk = ConflictHunk(
            file="test.py",
            hunk_index=0,
            start_line=2,  # Line where <<<<<<< appears
            ours=["    print(\"Hello from HEAD\")\n"],
            theirs=["    print(\"Hello from branch\")\n"],
            base=["    print(\"Hello from base\")\n"],
            resolved_text="    print(\"Hello, resolved!\")\n"
        )
        
        # Apply the resolution
        write_resolved(hunk, repo_root)
        
        # Read back and verify
        result = test_file.read_text()
        
        # Should not contain conflict markers
        assert "<<<<<<" not in result
        assert "||||||" not in result
        assert "======" not in result
        assert ">>>>>>" not in result
        
        # Should contain the resolved text
        assert "Hello, resolved!" in result
        
        # Should preserve surrounding content
        assert "def hello():" in result
        assert "return True" in result


def test_write_resolved_multiple_hunks():
    """Test writing resolved hunks when file has multiple conflicts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        test_file = repo_root / "multi.py"
        
        conflict_content = """# First conflict
<<<<<<< HEAD
x = 1
||||||| base
x = 0
=======
x = 2
>>>>>>> branch

# Second conflict
<<<<<<< HEAD
y = 10
||||||| base
y = 5
=======
y = 20
>>>>>>> branch
"""
        test_file.write_text(conflict_content)
        
        # Create hunks for both conflicts
        hunk1 = ConflictHunk(
            file="multi.py",
            hunk_index=0,
            start_line=2,
            ours=["x = 1\n"],
            theirs=["x = 2\n"],
            base=["x = 0\n"],
            resolved_text="x = 3\n"
        )
        
        hunk2 = ConflictHunk(
            file="multi.py",
            hunk_index=1,
            start_line=11,  # Line where second <<<<<<< appears
            ours=["y = 10\n"],
            theirs=["y = 20\n"],
            base=["y = 5\n"],
            resolved_text="y = 15\n"
        )
        
        # Apply in reverse order (bottom-up) to preserve line numbers
        write_resolved(hunk2, repo_root)
        write_resolved(hunk1, repo_root)
        
        result = test_file.read_text()
        
        # Should not contain any conflict markers
        assert "<<<<<<" not in result
        assert ">>>>>>>" not in result
        
        # Should contain both resolved values
        assert "x = 3" in result
        assert "y = 15" in result


def test_write_resolved_no_trailing_newline():
    """Test that resolved text without trailing newline gets one added."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        test_file = repo_root / "test.py"
        
        conflict_content = """<<<<<<< HEAD
old
||||||| base
base
=======
new
>>>>>>> branch
"""
        test_file.write_text(conflict_content)
        
        hunk = ConflictHunk(
            file="test.py",
            hunk_index=0,
            start_line=1,
            ours=["old\n"],
            theirs=["new\n"],
            base=["base\n"],
            resolved_text="resolved"  # No trailing newline
        )
        
        write_resolved(hunk, repo_root)
        result = test_file.read_text()
        
        # Should have added a newline
        assert result == "resolved\n"


def test_write_resolved_unresolved_hunk_raises():
    """Test that writing an unresolved hunk raises ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        
        hunk = ConflictHunk(
            file="test.py",
            hunk_index=0,
            start_line=1,
            ours=["old\n"],
            theirs=["new\n"],
            base=["base\n"],
            resolved_text=None  # Not resolved
        )
        
        with pytest.raises(ValueError, match="Cannot write unresolved hunk"):
            write_resolved(hunk, repo_root)


def test_apply_all_groups_by_file():
    """Test that apply_all groups hunks by file and applies them correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        
        # Create two files with conflicts
        file1 = repo_root / "file1.py"
        file1.write_text("""<<<<<<< HEAD
a = 1
||||||| base
a = 0
=======
a = 2
>>>>>>> branch
""")
        
        file2 = repo_root / "file2.py"
        file2.write_text("""<<<<<<< HEAD
b = 10
||||||| base
b = 5
=======
b = 20
>>>>>>> branch
""")
        
        # Create hunks
        hunks = [
            ConflictHunk(
                file="file1.py",
                hunk_index=0,
                start_line=1,
                ours=["a = 1\n"],
                theirs=["a = 2\n"],
                base=["a = 0\n"],
                resolved_text="a = 3\n"
            ),
            ConflictHunk(
                file="file2.py",
                hunk_index=0,
                start_line=1,
                ours=["b = 10\n"],
                theirs=["b = 20\n"],
                base=["b = 5\n"],
                resolved_text="b = 15\n"
            ),
        ]
        
        # Apply all
        result = apply_all(hunks, repo_root)
        
        # Should return dict with both files
        assert "file1.py" in result
        assert "file2.py" in result
        assert len(result["file1.py"]) == 1
        assert len(result["file2.py"]) == 1
        
        # Verify files were updated
        assert "a = 3" in file1.read_text()
        assert "b = 15" in file2.read_text()


def test_apply_all_skips_unresolved():
    """Test that apply_all only processes hunks with resolved_text set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        
        file1 = repo_root / "file1.py"
        file1.write_text("""<<<<<<< HEAD
x = 1
||||||| base
x = 0
=======
x = 2
>>>>>>> branch
""")
        
        hunks = [
            ConflictHunk(
                file="file1.py",
                hunk_index=0,
                start_line=1,
                ours=["x = 1\n"],
                theirs=["x = 2\n"],
                base=["x = 0\n"],
                resolved_text=None  # Not resolved
            ),
        ]
        
        result = apply_all(hunks, repo_root)
        
        # Should return empty dict
        assert result == {}
        
        # File should still have conflict markers
        content = file1.read_text()
        assert "<<<<<<" in content


def test_all_resolved():
    """Test the all_resolved helper function."""
    hunks = [
        ConflictHunk(
            file="test.py",
            hunk_index=0,
            start_line=1,
            ours=["a\n"],
            theirs=["b\n"],
            base=["c\n"],
            resolved_text="resolved"
        ),
        ConflictHunk(
            file="test.py",
            hunk_index=1,
            start_line=5,
            ours=["d\n"],
            theirs=["e\n"],
            base=["f\n"],
            resolved_text="also resolved"
        ),
    ]
    
    assert all_resolved(hunks) is True
    
    # Add an unresolved hunk
    hunks.append(
        ConflictHunk(
            file="test.py",
            hunk_index=2,
            start_line=10,
            ours=["g\n"],
            theirs=["h\n"],
            base=["i\n"],
            resolved_text=None
        )
    )
    
    assert all_resolved(hunks) is False


def test_all_resolved_empty_list():
    """Test all_resolved with empty list returns True."""
    assert all_resolved([]) is True


# Made with Bob