"""Git conflict marker parsing and ConflictHunk data model."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from git.state import get_conflicted_files


@dataclass
class ConflictHunk:
    """
    Represents a single merge conflict hunk within a file.
    
    This is the core data model for the entire application. All conflict analysis,
    AI suggestions, and resolution flows operate on ConflictHunk instances.
    """
    file: str                          # relative path from repo root
    hunk_index: int                    # 0-based index within this file
    start_line: int                    # line number where <<<<<<< appears
    ours: list[str]                    # lines from HEAD side (after <<<<<<<)
    theirs: list[str]                  # lines from incoming branch (after >>>>>>>)
    base: list[str]                    # common ancestor lines (from diff3 ||||||| section)
    kind: Literal["mechanical",
                  "logical",
                  "structural"] = "mechanical"  # set by classifier.py
    severity: int = 1                  # 1 = low, 2 = medium, 3 = high
    ai_summary: str = ""               # filled by bob.py
    ai_suggestion: str = ""            # filled by bob.py
    resolved_text: str | None = None   # set when user accepts/edits a resolution


def enable_diff3(repo_root: Path) -> None:
    """
    Configure git to use diff3 conflict style, which includes the common ancestor.
    
    This adds the ||||||| marker section showing the base (common ancestor) version
    of the conflicted code, which is essential for understanding merge conflicts.
    
    Args:
        repo_root: Path to the git repository root
    """
    subprocess.run(
        ["git", "config", "merge.conflictstyle", "diff3"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )


def parse_file(repo_root: Path, filepath: str) -> list[ConflictHunk]:
    """
    Parse a single file for diff3-style conflict markers and extract hunks.
    
    Expected conflict marker format:
    <<<<<<< HEAD (or branch name)
    ... ours lines ...
    ||||||| base commit
    ... base lines ...
    =======
    ... theirs lines ...
    >>>>>>> branch-name
    
    Args:
        repo_root: Path to the git repository root
        filepath: Relative path from repo root to the conflicted file
        
    Returns:
        list[ConflictHunk]: List of conflict hunks found in the file, or empty list
                           if no conflicts exist
                           
    Raises:
        ValueError: If conflict markers are malformed or incomplete
    """
    full_path = repo_root / filepath
    
    if not full_path.exists():
        raise ValueError(f"File not found: {filepath}")
    
    lines = full_path.read_text().splitlines(keepends=True)
    hunks: list[ConflictHunk] = []
    hunk_index = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for conflict start marker
        if line.startswith("<<<<<<<"):
            start_line = i + 1  # 1-based line number
            
            # Find the base marker (|||||||)
            base_start = None
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("|||||||"):
                    base_start = j
                    break
            
            if base_start is None:
                raise ValueError(
                    f"Malformed conflict in {filepath} at line {start_line}: "
                    f"missing ||||||| base marker"
                )
            
            # Find the separator marker (=======)
            separator = None
            for j in range(base_start + 1, len(lines)):
                if lines[j].startswith("======="):
                    separator = j
                    break
            
            if separator is None:
                raise ValueError(
                    f"Malformed conflict in {filepath} at line {start_line}: "
                    f"missing ======= separator"
                )
            
            # Find the end marker (>>>>>>>)
            end = None
            for j in range(separator + 1, len(lines)):
                if lines[j].startswith(">>>>>>>"):
                    end = j
                    break
            
            if end is None:
                raise ValueError(
                    f"Malformed conflict in {filepath} at line {start_line}: "
                    f"missing >>>>>>> end marker"
                )
            
            # Extract the three sections
            ours = lines[i + 1:base_start]
            base = lines[base_start + 1:separator]
            theirs = lines[separator + 1:end]
            
            # Create the hunk
            hunk = ConflictHunk(
                file=filepath,
                hunk_index=hunk_index,
                start_line=start_line,
                ours=ours,
                theirs=theirs,
                base=base
            )
            hunks.append(hunk)
            hunk_index += 1
            
            # Continue parsing after this conflict block
            i = end + 1
        else:
            i += 1
    
    return hunks


def parse_all(repo_root: Path) -> list[ConflictHunk]:
    """
    Parse all conflicted files in the repository.
    
    This is the main entry point for conflict detection. It discovers all files
    with unresolved conflicts and parses each one.
    
    Args:
        repo_root: Path to the git repository root
        
    Returns:
        list[ConflictHunk]: Flat list of all conflict hunks across all files
    """
    conflicted_files = get_conflicted_files(repo_root)
    all_hunks: list[ConflictHunk] = []
    
    for filepath in conflicted_files:
        hunks = parse_file(repo_root, filepath)
        all_hunks.extend(hunks)
    
    return all_hunks

# Made with Bob
