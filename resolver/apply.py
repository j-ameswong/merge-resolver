"""Apply resolved conflict hunks to files and commit changes."""

import subprocess
from collections import defaultdict
from pathlib import Path

from git.parser import ConflictHunk


def write_resolved(hunk: ConflictHunk, repo_root: Path) -> None:
    """
    Write a resolved hunk back to its file, replacing the conflict block.
    
    Reads the file, finds the conflict block matching this hunk's start_line,
    and replaces the entire block (from <<<<<<< to >>>>>>>) with the resolved text.
    
    Args:
        hunk: ConflictHunk with resolved_text set
        repo_root: Path to the git repository root
        
    Raises:
        ValueError: If hunk.resolved_text is None or conflict block not found
    """
    if hunk.resolved_text is None:
        raise ValueError(f"Cannot write unresolved hunk: {hunk.file}:{hunk.start_line}")
    
    full_path = repo_root / hunk.file
    
    if not full_path.exists():
        raise ValueError(f"File not found: {hunk.file}")
    
    # Read the current file content
    lines = full_path.read_text().splitlines(keepends=True)
    
    # Find the conflict block starting at hunk.start_line (1-based)
    # start_line points to the line number where <<<<<<< appears
    conflict_start_idx = hunk.start_line - 1  # Convert to 0-based index
    
    if conflict_start_idx >= len(lines) or not lines[conflict_start_idx].startswith("<<<<<<<"):
        raise ValueError(
            f"Conflict marker not found at expected line {hunk.start_line} in {hunk.file}"
        )
    
    # Find the end marker (>>>>>>>) after the start
    conflict_end_idx = None
    for i in range(conflict_start_idx + 1, len(lines)):
        if lines[i].startswith(">>>>>>>"):
            conflict_end_idx = i
            break
    
    if conflict_end_idx is None:
        raise ValueError(
            f"Conflict end marker not found after line {hunk.start_line} in {hunk.file}"
        )
    
    # Replace the conflict block with resolved text
    # Ensure resolved_text ends with newline if it doesn't already
    resolved = hunk.resolved_text
    if resolved and not resolved.endswith('\n'):
        resolved += '\n'
    
    # Build new file content: before + resolved + after
    new_lines = (
        lines[:conflict_start_idx] +
        [resolved] +
        lines[conflict_end_idx + 1:]
    )
    
    # Write back to file
    full_path.write_text(''.join(new_lines))


def apply_all(hunks: list[ConflictHunk], repo_root: Path) -> dict[str, list[ConflictHunk]]:
    """
    Apply all resolved hunks to their respective files.
    
    Groups hunks by file and processes them bottom-up (highest start_line first)
    to preserve line numbers during replacement.
    
    Args:
        hunks: List of ConflictHunk instances
        repo_root: Path to the git repository root
        
    Returns:
        dict mapping filename to list of resolved hunks that were applied
    """
    # Filter to only resolved hunks
    resolved_hunks = [h for h in hunks if h.resolved_text is not None]
    
    if not resolved_hunks:
        return {}
    
    # Group by file
    by_file: dict[str, list[ConflictHunk]] = defaultdict(list)
    for hunk in resolved_hunks:
        by_file[hunk.file].append(hunk)
    
    # Process each file
    result: dict[str, list[ConflictHunk]] = {}
    for filename, file_hunks in by_file.items():
        # Sort bottom-up (highest start_line first) to preserve line numbers
        sorted_hunks = sorted(file_hunks, key=lambda h: h.start_line, reverse=True)
        
        # Apply each hunk
        for hunk in sorted_hunks:
            write_resolved(hunk, repo_root)
        
        result[filename] = sorted_hunks
    
    return result


def stage_file(filepath: str, repo_root: Path) -> None:
    """
    Stage a file using git add.
    
    Args:
        filepath: Relative path from repo root
        repo_root: Path to the git repository root
        
    Raises:
        subprocess.CalledProcessError: If git add fails
    """
    subprocess.run(
        ["git", "add", filepath],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )


def commit(message: str, repo_root: Path) -> None:
    """
    Create a git commit with the given message.
    
    Args:
        message: Commit message
        repo_root: Path to the git repository root
        
    Raises:
        subprocess.CalledProcessError: If git commit fails
    """
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )


def all_resolved(hunks: list[ConflictHunk]) -> bool:
    """
    Check if all hunks have been resolved.
    
    Args:
        hunks: List of ConflictHunk instances
        
    Returns:
        True if every hunk has resolved_text set, False otherwise
    """
    return all(h.resolved_text is not None for h in hunks)


# Made with Bob