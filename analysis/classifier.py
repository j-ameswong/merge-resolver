"""Conflict hunk classification by type and severity.

This module analyzes ConflictHunk instances and assigns them a classification:
- mechanical: simple, non-overlapping changes (severity 1)
- logical: changes to the same named entities (severity 2)
- structural: symbols that appear across multiple files (severity 3)
"""

import re
from git.parser import ConflictHunk


def _extract_names(lines: list[str]) -> set[str]:
    """
    Extract top-level Python identifiers (function and class names) from code lines.
    
    Uses a simple regex to find 'def name' and 'class name' patterns.
    
    Args:
        lines: List of code lines (may include newlines)
        
    Returns:
        set[str]: Set of identifier names found
    """
    names = set()
    pattern = re.compile(r'\b(def |class )(\w+)')
    
    for line in lines:
        matches = pattern.findall(line)
        for _, name in matches:
            names.add(name)
    
    return names


def classify(hunk: ConflictHunk, all_hunks: list[ConflictHunk]) -> ConflictHunk:
    """
    Classify a single conflict hunk and set its kind and severity.
    
    Classification logic:
    1. Check for structural conflicts (cross-file symbol collision) first
    2. If not structural, check if it's mechanical (short, non-overlapping)
    3. Otherwise, it's logical (overlapping symbols)
    
    Args:
        hunk: The ConflictHunk to classify
        all_hunks: All hunks in the repository (needed for structural analysis)
        
    Returns:
        ConflictHunk: The same hunk with kind and severity set
    """
    # Extract names from this hunk
    ours_names = _extract_names(hunk.ours)
    theirs_names = _extract_names(hunk.theirs)
    all_names = ours_names | theirs_names
    
    # Check for structural conflicts: any symbol from this hunk appears in a different file
    is_structural = False
    if all_names:
        for other_hunk in all_hunks:
            # Skip hunks from the same file
            if other_hunk.file == hunk.file:
                continue
            
            # Check if any names overlap with other files
            other_ours = _extract_names(other_hunk.ours)
            other_theirs = _extract_names(other_hunk.theirs)
            other_names = other_ours | other_theirs
            
            if all_names & other_names:
                is_structural = True
                break
    
    if is_structural:
        hunk.kind = "structural"
        hunk.severity = 3
        return hunk
    
    # Check for mechanical conflicts: short and non-overlapping
    ours_short = len(hunk.ours) <= 5
    theirs_short = len(hunk.theirs) <= 5
    no_overlap = not (ours_names & theirs_names)
    
    if ours_short and theirs_short and no_overlap:
        hunk.kind = "mechanical"
        hunk.severity = 1
        return hunk
    
    # Default to logical conflict
    hunk.kind = "logical"
    hunk.severity = 2
    return hunk


def classify_all(hunks: list[ConflictHunk]) -> list[ConflictHunk]:
    """
    Classify all conflict hunks in the repository.
    
    This function processes hunks in a way that allows structural analysis
    (which requires knowledge of all hunks) to work correctly.
    
    Args:
        hunks: List of all ConflictHunk instances to classify
        
    Returns:
        list[ConflictHunk]: The same list with all hunks classified
    """
    # Classify each hunk with access to the full list for structural analysis
    for hunk in hunks:
        classify(hunk, hunks)
    
    return hunks

# Made with Bob
