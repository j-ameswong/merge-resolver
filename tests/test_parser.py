"""Tests for git/parser.py conflict parsing functionality."""

import pytest
from pathlib import Path
from git.parser import ConflictHunk, parse_file, enable_diff3, parse_all


# Get the path to the fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_file_with_conflict():
    """Test parsing a file with a single diff3-style conflict."""
    # Use the fixtures directory as a mock repo root
    hunks = parse_file(FIXTURES_DIR, "simple_conflict.py")
    
    # Should find exactly one conflict hunk
    assert len(hunks) == 1
    
    hunk = hunks[0]
    
    # Check basic metadata
    assert hunk.file == "simple_conflict.py"
    assert hunk.hunk_index == 0
    assert hunk.start_line == 9  # Line where <<<<<<< appears
    
    # Check that ours, base, and theirs sections are correctly extracted
    assert len(hunk.ours) > 0
    assert len(hunk.base) > 0
    assert len(hunk.theirs) > 0
    
    # Verify content of each section
    # OURS section should contain the sum with generator
    ours_text = "".join(hunk.ours)
    assert "sum(item * 1.1 for item in items)" in ours_text
    
    # BASE section should contain the original loop
    base_text = "".join(hunk.base)
    assert "total = 0" in base_text
    assert "for item in items:" in base_text
    
    # THEIRS section should contain the loop with tax
    theirs_text = "".join(hunk.theirs)
    assert "total = 0" in theirs_text
    assert "total += item * 1.1" in theirs_text
    
    # Check default values for fields set by other modules
    assert hunk.kind == "mechanical"
    assert hunk.severity == 1
    assert hunk.ai_summary == ""
    assert hunk.ai_suggestion == ""
    assert hunk.resolved_text is None


def test_parse_file_no_conflicts():
    """Test parsing a file with no conflict markers returns empty list."""
    hunks = parse_file(FIXTURES_DIR, "no_conflict.py")
    
    # Should return empty list when no conflicts exist
    assert hunks == []
    assert isinstance(hunks, list)


def test_parse_file_nonexistent():
    """Test that parsing a nonexistent file raises ValueError."""
    with pytest.raises(ValueError, match="File not found"):
        parse_file(FIXTURES_DIR, "does_not_exist.py")


def test_parse_file_malformed_missing_base():
    """Test that malformed conflict (missing base marker) raises ValueError."""
    # Create a temporary file with malformed conflict
    malformed_file = FIXTURES_DIR / "malformed_no_base.py"
    malformed_file.write_text("""
def foo():
<<<<<<< HEAD
    return 1
=======
    return 2
>>>>>>> branch
""")
    
    try:
        with pytest.raises(ValueError, match="missing.*base marker"):
            parse_file(FIXTURES_DIR, "malformed_no_base.py")
    finally:
        # Clean up
        if malformed_file.exists():
            malformed_file.unlink()


def test_parse_file_malformed_missing_separator():
    """Test that malformed conflict (missing separator) raises ValueError."""
    malformed_file = FIXTURES_DIR / "malformed_no_sep.py"
    malformed_file.write_text("""
def foo():
<<<<<<< HEAD
    return 1
||||||| base
    return 0
>>>>>>> branch
""")
    
    try:
        with pytest.raises(ValueError, match="missing.*separator"):
            parse_file(FIXTURES_DIR, "malformed_no_sep.py")
    finally:
        if malformed_file.exists():
            malformed_file.unlink()


def test_parse_file_malformed_missing_end():
    """Test that malformed conflict (missing end marker) raises ValueError."""
    malformed_file = FIXTURES_DIR / "malformed_no_end.py"
    malformed_file.write_text("""
def foo():
<<<<<<< HEAD
    return 1
||||||| base
    return 0
=======
    return 2
""")
    
    try:
        with pytest.raises(ValueError, match="missing.*end marker"):
            parse_file(FIXTURES_DIR, "malformed_no_end.py")
    finally:
        if malformed_file.exists():
            malformed_file.unlink()


def test_parse_file_multiple_conflicts():
    """Test parsing a file with multiple conflict hunks."""
    # Create a file with two conflicts
    multi_conflict_file = FIXTURES_DIR / "multi_conflict.py"
    multi_conflict_file.write_text("""
def foo():
<<<<<<< HEAD
    return 1
||||||| base
    return 0
=======
    return 2
>>>>>>> branch

def bar():
<<<<<<< HEAD
    return "a"
||||||| base
    return "x"
=======
    return "b"
>>>>>>> branch
""")
    
    try:
        hunks = parse_file(FIXTURES_DIR, "multi_conflict.py")
        
        # Should find two conflict hunks
        assert len(hunks) == 2
        
        # Check that hunk indices are correct
        assert hunks[0].hunk_index == 0
        assert hunks[1].hunk_index == 1
        
        # Check that both hunks reference the same file
        assert hunks[0].file == "multi_conflict.py"
        assert hunks[1].file == "multi_conflict.py"
        
        # Check that start lines are different
        assert hunks[0].start_line < hunks[1].start_line
    finally:
        if multi_conflict_file.exists():
            multi_conflict_file.unlink()


def test_conflict_hunk_dataclass():
    """Test that ConflictHunk dataclass has correct structure and defaults."""
    hunk = ConflictHunk(
        file="test.py",
        hunk_index=0,
        start_line=10,
        ours=["line1\n", "line2\n"],
        theirs=["line3\n", "line4\n"],
        base=["line0\n"]
    )
    
    # Check required fields
    assert hunk.file == "test.py"
    assert hunk.hunk_index == 0
    assert hunk.start_line == 10
    assert hunk.ours == ["line1\n", "line2\n"]
    assert hunk.theirs == ["line3\n", "line4\n"]
    assert hunk.base == ["line0\n"]
    
    # Check default values
    assert hunk.kind == "mechanical"
    assert hunk.severity == 1
    assert hunk.ai_summary == ""
    assert hunk.ai_suggestion == ""
    assert hunk.resolved_text is None


def test_conflict_hunk_mutable_fields():
    """Test that ConflictHunk fields can be modified (for classifier/AI)."""
    hunk = ConflictHunk(
        file="test.py",
        hunk_index=0,
        start_line=10,
        ours=["line1\n"],
        theirs=["line2\n"],
        base=["line0\n"]
    )
    
    # Modify fields that are set by other modules
    hunk.kind = "logical"
    hunk.severity = 2
    hunk.ai_summary = "Test summary"
    hunk.ai_suggestion = "Test suggestion"
    hunk.resolved_text = "resolved content"
    
    # Verify modifications
    assert hunk.kind == "logical"
    assert hunk.severity == 2
    assert hunk.ai_summary == "Test summary"
    assert hunk.ai_suggestion == "Test suggestion"
    assert hunk.resolved_text == "resolved content"


def test_enable_diff3(tmp_path):
    """Test that enable_diff3 runs git config command."""
    # This test requires a git repository
    # We'll create a minimal one in tmp_path
    import subprocess
    
    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    
    # Run enable_diff3
    enable_diff3(tmp_path)
    
    # Verify the config was set
    result = subprocess.run(
        ["git", "config", "merge.conflictstyle"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True
    )
    
    assert result.stdout.strip() == "diff3"


def test_parse_all_integration(tmp_path):
    """Test parse_all with a mock git repository."""
    import subprocess
    from git.state import get_conflicted_files
    
    # Initialize a git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True
    )
    
    # Create a file and commit it
    test_file = tmp_path / "test.py"
    test_file.write_text("def foo():\n    return 0\n")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=tmp_path,
        check=True,
        capture_output=True
    )
    
    # Create a branch and make a conflicting change
    subprocess.run(
        ["git", "checkout", "-b", "branch1"],
        cwd=tmp_path,
        check=True,
        capture_output=True
    )
    test_file.write_text("def foo():\n    return 1\n")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "change to 1"],
        cwd=tmp_path,
        check=True,
        capture_output=True
    )
    
    # Go back to main and make a different change
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=tmp_path,
        check=True,
        capture_output=True
    )
    test_file.write_text("def foo():\n    return 2\n")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "change to 2"],
        cwd=tmp_path,
        check=True,
        capture_output=True
    )
    
    # Enable diff3 style
    enable_diff3(tmp_path)
    
    # Try to merge - this should create a conflict
    result = subprocess.run(
        ["git", "merge", "branch1"],
        cwd=tmp_path,
        capture_output=True,
        text=True
    )
    
    # Merge should fail due to conflict
    assert result.returncode != 0
    
    # Now parse_all should find the conflict
    hunks = parse_all(tmp_path)
    
    # Should have at least one hunk
    assert len(hunks) > 0
    assert hunks[0].file == "test.py"

# Made with Bob
