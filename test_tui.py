"""Test script for the TUI with static data."""

from git.parser import ConflictHunk
from ui.app import MergeResolverApp


def create_test_hunks() -> list[ConflictHunk]:
    """Create some test conflict hunks with static data."""
    hunks = []
    
    # Hunk 1: Mechanical conflict in auth/login.py
    hunk1 = ConflictHunk(
        file="src/auth/login.py",
        hunk_index=0,
        start_line=15,
        ours=["def authenticate(user, password):\n", "    use_jwt = True\n", "    return validate(user, password)\n"],
        theirs=["def authenticate(user, password):\n", "    session_middleware = True\n", "    return validate(user, password)\n"],
        base=["def authenticate(user, password):\n", "    return validate(user, password)\n"],
        kind="mechanical",
        severity=1,
        ai_summary="Both sides added different configuration flags without conflicting logic.",
        ai_suggestion="Keep both flags: use_jwt = True and session_middleware = True"
    )
    hunks.append(hunk1)
    
    # Hunk 2: Logical conflict in auth/login.py
    hunk2 = ConflictHunk(
        file="src/auth/login.py",
        hunk_index=1,
        start_line=42,
        ours=["class LoginHandler:\n", "    def handle_login(self, request):\n", "        return jwt_login(request)\n"],
        theirs=["class LoginHandler:\n", "    def handle_login(self, request):\n", "        return session_login(request)\n"],
        base=["class LoginHandler:\n", "    def handle_login(self, request):\n", "        return basic_login(request)\n"],
        kind="logical",
        severity=2,
        ai_summary="Both sides changed the login method implementation in conflicting ways.",
        ai_suggestion="Use a strategy pattern to support both JWT and session-based login."
    )
    hunks.append(hunk2)
    
    # Hunk 3: Mechanical conflict in models.py
    hunk3 = ConflictHunk(
        file="src/models.py",
        hunk_index=0,
        start_line=8,
        ours=["from datetime import datetime\n", "from typing import Optional\n"],
        theirs=["from datetime import datetime, timedelta\n"],
        base=["from datetime import datetime\n"],
        kind="mechanical",
        severity=1,
        ai_summary="",  # No AI analysis yet
        ai_suggestion=""
    )
    hunks.append(hunk3)
    
    # Hunk 4: Structural conflict in migrations/001_init.py
    hunk4 = ConflictHunk(
        file="migrations/001_init.py",
        hunk_index=0,
        start_line=25,
        ours=["def create_user_table():\n", "    # New JWT-based schema\n", "    pass\n"],
        theirs=["def create_user_table():\n", "    # New session-based schema\n", "    pass\n"],
        base=["def create_user_table():\n", "    # Basic schema\n", "    pass\n"],
        kind="structural",
        severity=3,
        ai_summary="Database schema conflict affects multiple files and the authentication system.",
        ai_suggestion="Design a unified schema that supports both authentication methods."
    )
    hunks.append(hunk4)
    
    return hunks


def main():
    """Run the TUI with test data."""
    print("Creating test conflict hunks...")
    hunks = create_test_hunks()
    
    print(f"Created {len(hunks)} test hunks")
    print("Launching TUI...")
    
    app = MergeResolverApp(
        hunks=hunks,
        ours_branch="feature/jwt-auth",
        theirs_branch="feature/session-auth"
    )
    app.run()


if __name__ == "__main__":
    main()

# Made with Bob
