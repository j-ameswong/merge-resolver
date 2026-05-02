"""Git repository state detection and conflict file discovery."""

import subprocess
from pathlib import Path


def find_repo_root() -> Path:
    """
    Walk up from current working directory until a .git directory is found.
    
    Returns:
        Path: The root directory of the git repository
        
    Raises:
        RuntimeError: If no .git directory is found in any parent directory
    """
    current = Path.cwd()
    
    # Walk up the directory tree
    for parent in [current, *current.parents]:
        git_dir = parent / ".git"
        if git_dir.exists() and git_dir.is_dir():
            return parent
    
    raise RuntimeError(
        f"Not in a git repository. No .git directory found in {current} or any parent directory."
    )


def get_branch_names(repo_root: Path) -> tuple[str, str]:
    """
    Get the names of the branches involved in the current merge.
    
    Args:
        repo_root: Path to the git repository root
        
    Returns:
        tuple[str, str]: (our_branch, their_branch) where our_branch is the current
                        HEAD branch and their_branch is the branch being merged in
                        
    Raises:
        RuntimeError: If not currently in a merge state
    """
    # Get our branch (current HEAD)
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    our_branch = result.stdout.strip()
    
    # Check if we're in a merge state
    merge_head_file = repo_root / ".git" / "MERGE_HEAD"
    if not merge_head_file.exists():
        raise RuntimeError(
            "Not currently in a merge state. No .git/MERGE_HEAD file found."
        )
    
    # Read the SHA from MERGE_HEAD
    merge_sha = merge_head_file.read_text().strip()
    
    # Get a readable name for the merge branch
    result = subprocess.run(
        ["git", "name-rev", "--name-only", merge_sha],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    their_branch = result.stdout.strip()
    
    return (our_branch, their_branch)


def get_conflicted_files(repo_root: Path) -> list[str]:
    """
    Get list of files with unresolved merge conflicts.
    
    Args:
        repo_root: Path to the git repository root
        
    Returns:
        list[str]: List of relative file paths (from repo root) that have conflicts
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    
    # Split by newlines and filter out empty strings
    files = [line.strip() for line in result.stdout.split("\n") if line.strip()]
    return files

# Made with Bob
