"""Entry point for merge-resolver TUI application."""

import argparse
import sys
from pathlib import Path

from git.state import find_repo_root, get_branch_names
from git.parser import enable_diff3, parse_all
from analysis.classifier import classify_all
from ui.app import MergeResolverApp


def main() -> int:
    """
    Main entry point for merge-resolver.
    
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Intelligent merge conflict resolver with AI assistance"
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Path to git repository (default: current directory)"
    )
    args = parser.parse_args()
    
    try:
        # Find repository root
        repo_root = find_repo_root()
        print(f"Repository: {repo_root}")
        
        # Enable diff3 conflict style
        enable_diff3(repo_root)
        
        # Get branch names
        try:
            ours_branch, theirs_branch = get_branch_names(repo_root)
            print(f"Merge: {ours_branch} ← {theirs_branch}")
        except RuntimeError as e:
            print(f"Warning: {e}")
            print("Using default branch names")
            ours_branch = "HEAD"
            theirs_branch = "MERGE_HEAD"
        
        # Parse all conflicts
        print("Parsing conflicts...")
        hunks = parse_all(repo_root)
        
        if not hunks:
            print("✓ No conflicts found!")
            return 0
        
        # Classify conflicts
        print(f"Found {len(hunks)} conflict hunks across {len(set(h.file for h in hunks))} files")
        print("Classifying conflicts...")
        classify_all(hunks)
        
        # Show classification summary
        mechanical = sum(1 for h in hunks if h.kind == "mechanical")
        logical = sum(1 for h in hunks if h.kind == "logical")
        structural = sum(1 for h in hunks if h.kind == "structural")
        print(f"  Mechanical: {mechanical}")
        print(f"  Logical: {logical}")
        print(f"  Structural: {structural}")
        
        # Launch TUI
        print("\nLaunching TUI...")
        app = MergeResolverApp(
            hunks=hunks,
            ours_branch=ours_branch,
            theirs_branch=theirs_branch
        )
        app.run()
        
        return 0
        
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAborted by user")
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
