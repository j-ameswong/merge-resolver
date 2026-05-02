#!/usr/bin/env python3
"""Test script for bob.py AI analysis module."""

import os
from git.parser import ConflictHunk
from analysis.bob import analyse_hunk, analyse_all

# Set mock backend for testing
os.environ["AI_BACKEND"] = "mock"

def test_analyse_single_hunk():
    """Test analysing a single hunk with mock backend."""
    print("Testing analyse_hunk with mock backend...")
    
    # Create a test hunk
    hunk = ConflictHunk(
        file="test.py",
        hunk_index=0,
        start_line=10,
        ours=["def foo():\n", "    return 'ours'\n"],
        theirs=["def foo():\n", "    return 'theirs'\n"],
        base=["def foo():\n", "    return 'base'\n"],
        kind="logical",
        severity=2
    )
    
    # Analyse it
    result = analyse_hunk(hunk, "main", "feature-branch")
    
    # Check results
    assert result.ai_summary != "", "ai_summary should be populated"
    assert result.ai_suggestion != "", "ai_suggestion should be populated"
    
    print(f"✓ ai_summary: {result.ai_summary}")
    print(f"✓ ai_suggestion: {result.ai_suggestion}")
    print()

def test_analyse_multiple_hunks():
    """Test analysing multiple hunks."""
    print("Testing analyse_all with mock backend...")
    
    hunks = [
        ConflictHunk(
            file="test1.py",
            hunk_index=0,
            start_line=10,
            ours=["x = 1\n"],
            theirs=["x = 2\n"],
            base=["x = 0\n"],
            kind="mechanical",
            severity=1
        ),
        ConflictHunk(
            file="test2.py",
            hunk_index=0,
            start_line=20,
            ours=["y = 'a'\n"],
            theirs=["y = 'b'\n"],
            base=["y = ''\n"],
            kind="logical",
            severity=2
        ),
    ]
    
    # Analyse all
    analyse_all(hunks, "main", "feature")
    
    # Check all have results
    for i, hunk in enumerate(hunks):
        assert hunk.ai_summary != "", f"Hunk {i} should have ai_summary"
        assert hunk.ai_suggestion != "", f"Hunk {i} should have ai_suggestion"
        print(f"✓ Hunk {i} analysed successfully")
    
    print()

def test_error_handling():
    """Test that errors are handled gracefully."""
    print("Testing error handling...")
    
    # Create a hunk with empty content (edge case)
    hunk = ConflictHunk(
        file="empty.py",
        hunk_index=0,
        start_line=1,
        ours=[],
        theirs=[],
        base=[],
        kind="mechanical",
        severity=1
    )
    
    # Should not raise, should set "Analysis unavailable"
    result = analyse_hunk(hunk, "main", "feature")
    
    # Mock backend should still work even with empty content
    assert result.ai_summary != "", "Should have summary even with empty content"
    print(f"✓ Handled empty content: {result.ai_summary}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Testing analysis/bob.py")
    print("=" * 60)
    print()
    
    test_analyse_single_hunk()
    test_analyse_multiple_hunks()
    test_error_handling()
    
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)

# Made with Bob
