#!/usr/bin/env bash
# Sets up a test repo with conflicts that match the merge-resolver demo:
#   - auth.py:   mechanical (imports) + logical (login body)
#   - api.py:    structural (to_dict shared with models.py)
#   - models.py: structural (to_dict shared with api.py)
#
# Usage: ./scripts/setup_test_repo.sh [repo-path]
#   repo-path defaults to ../test-repo (relative to this script's parent).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_PATH="${1:-$SCRIPT_DIR/../../test-repo}"

if [[ -e "$REPO_PATH" ]]; then
    echo "Path '$REPO_PATH' already exists. Remove it first or pass a different path." >&2
    exit 1
fi

mkdir -p "$REPO_PATH"
cd "$REPO_PATH"

git init -q -b main
git config user.email "test@example.com"
git config user.name  "Test User"
git config merge.conflictStyle diff3

# ============================================================================
# BASE COMMIT (main) — clean starting point
# ============================================================================

cat > auth.py <<'EOF'
"""Authentication module."""

import hashlib


def login(username, password):
    digest = hashlib.sha256(password.encode()).hexdigest()
    return digest


def get_user(user_id):
    return USERS.get(user_id)


USERS = {}
EOF

cat > api.py <<'EOF'
"""HTTP API handlers."""

from auth import get_user


def handle_request(req):
    user = get_user(req["user_id"])
    return {"status": "ok", "user": user}
EOF

cat > models.py <<'EOF'
"""Domain models."""


class User:
    def __init__(self, user_id, name):
        self.user_id = user_id
        self.name = name
EOF

git add auth.py api.py models.py
git commit -q -m "initial: auth, api, models skeleton"

# ============================================================================
# FEATURE BRANCH — adds JWT auth + email field, with a to_dict serializer
# ============================================================================

git checkout -q -b conflict-feature

cat > auth.py <<'EOF'
"""Authentication module."""

import hashlib
import jwt


def login(username, password):
    # feature: issue a signed JWT on successful credential check
    digest = hashlib.sha256(password.encode()).hexdigest()
    token = jwt.encode(
        {"sub": username, "digest": digest},
        "feature-secret",
        algorithm="HS256",
    )
    return token


def get_user(user_id):
    return USERS.get(user_id)


USERS = {}
EOF

cat > api.py <<'EOF'
"""HTTP API handlers."""

from auth import get_user


def to_dict(user):
    return {
        "id": user.user_id,
        "name": user.name,
        "email": user.email,
    }


def handle_request(req):
    user = get_user(req["user_id"])
    return {"status": "ok", "user": to_dict(user)}
EOF

cat > models.py <<'EOF'
"""Domain models."""


class User:
    def __init__(self, user_id, name, email):
        self.user_id = user_id
        self.name = name
        self.email = email

    def to_dict(self):
        return {
            "id": self.user_id,
            "name": self.name,
            "email": self.email,
        }
EOF

git commit -qam "feature: jwt login + email field + to_dict serializer"

# ============================================================================
# MAIN BRANCH — adds logging + created_at field, conflicting at the same spots
# ============================================================================

git checkout -q main

cat > auth.py <<'EOF'
"""Authentication module."""

import hashlib
import logging


def login(username, password):
    # main: log every login attempt before returning the digest
    logging.info("login attempt: user=%s", username)
    digest = hashlib.sha256(password.encode()).hexdigest()
    logging.info("login digest computed")
    return digest


def get_user(user_id):
    return USERS.get(user_id)


USERS = {}
EOF

cat > api.py <<'EOF'
"""HTTP API handlers."""

from auth import get_user


def to_dict(user):
    return {
        "id": user.user_id,
        "name": user.name,
        "created_at": user.created_at,
    }


def handle_request(req):
    user = get_user(req["user_id"])
    return {"status": "ok", "user": to_dict(user)}
EOF

cat > models.py <<'EOF'
"""Domain models."""


class User:
    def __init__(self, user_id, name, created_at):
        self.user_id = user_id
        self.name = name
        self.created_at = created_at

    def to_dict(self):
        return {
            "id": self.user_id,
            "name": self.name,
            "created_at": self.created_at,
        }
EOF

git commit -qam "main: logging on login + created_at field + to_dict serializer"

# ============================================================================
# Trigger the merge — expected to conflict in all three files
# ============================================================================

if git merge --no-edit conflict-feature; then
    echo "Unexpected: merge succeeded without conflicts." >&2
    exit 1
fi

echo
echo "Test repo ready at: $REPO_PATH"
echo "On branch 'main', mid-merge with conflict-feature."
echo
echo "Expected conflict shape (matches demo script):"
echo "  auth.py    -> 3 hunks: mechanical (imports) + mechanical/logical (login body parts)"
echo "  api.py     -> 1 hunk:  structural (to_dict shared with models.py)"
echo "  models.py  -> 2 hunks: logical (__init__) + structural (to_dict)"
echo
echo "All three severity levels represented for the demo: green, yellow, red."
