"""Git repository state detection and conflict file discovery."""

import subprocess
from pathlib import Path


class GitError(Exception):
    """Base exception for git-related errors."""
    pass


class GitNotFoundError(GitError):
    """Raised when git executable is not found."""
    pass


class NotInRepoError(GitError):
    """Raised when not in a git repository."""
    pass


class NotInMergeError(GitError):
    """Raised when not in a merge state."""
    pass


def find_repo_root() -> Path:
    """
    Walk up from current working directory until a .git directory is found.
    
    Returns:
        Path: The root directory of the git repository
        
    Raises:
        NotInRepoError: If no .git directory is found in any parent directory
    """
    current = Path.cwd()
    
    # Walk up the directory tree
    for parent in [current, *current.parents]:
        git_dir = parent / ".git"
        if git_dir.exists() and git_dir.is_dir():
            return parent
    
    raise NotInRepoError(
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
        GitNotFoundError: If git executable is not found
        NotInMergeError: If not currently in a merge state
        GitError: If git command fails
    """
    try:
        # Get our branch (current HEAD)
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )
        our_branch = result.stdout.strip()
    except FileNotFoundError:
        raise GitNotFoundError(
            "Git executable not found. Please ensure git is installed and in your PATH."
        )
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to get current branch: {e.stderr.strip()}")
    
    # Check if we're in a merge state
    merge_head_file = repo_root / ".git" / "MERGE_HEAD"
    if not merge_head_file.exists():
        raise NotInMergeError(
            "Not currently in a merge state. Run 'git merge <branch>' first to create conflicts."
        )
    
    # Read the SHA from MERGE_HEAD
    merge_sha = merge_head_file.read_text().strip()
    
    try:
        # Get a readable name for the merge branch
        result = subprocess.run(
            ["git", "name-rev", "--name-only", merge_sha],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )
        their_branch = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to get merge branch name: {e.stderr.strip()}")
    
    return (our_branch, their_branch)


def get_conflicted_files(repo_root: Path) -> list[str]:
    """
    Get list of files with unresolved merge conflicts.
    
    Args:
        repo_root: Path to the git repository root
        
    Returns:
        list[str]: List of relative file paths (from repo root) that have conflicts
        
    Raises:
        GitNotFoundError: If git executable is not found
        GitError: If git command fails
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )
    except FileNotFoundError:
        raise GitNotFoundError(
            "Git executable not found. Please ensure git is installed and in your PATH."
        )
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to get conflicted files: {e.stderr.strip()}")
    
    # Split by newlines and filter out empty strings
    files = [line.strip() for line in result.stdout.split("\n") if line.strip()]
    return files

# Made with Bob
