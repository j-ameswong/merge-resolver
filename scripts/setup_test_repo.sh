#!/usr/bin/env bash
# Sets up a test repo with multiple conflict hunks for merge-resolver testing.
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

# --- base commit on main ---
cat > app.py <<'EOF'
"""Sample application module."""


def greet(name):
    return f"Hello, {name}"


def add(a, b):
    return a + b


def multiply(a, b):
    return a * b


class Calculator:
    def __init__(self):
        self.history = []

    def compute(self, x, y):
        result = x + y
        self.history.append(result)
        return result

    def reset(self):
        self.history = []


def main():
    calc = Calculator()
    print(greet("world"))
    print(calc.compute(2, 3))


if __name__ == "__main__":
    main()
EOF
git add app.py
git commit -q -m "add base app.py"

# --- feature branch: modify greet, add, compute, main ---
git checkout -q -b conflict-feature
cat > app.py <<'EOF'
"""Sample application module."""


def greet(name):
    return f"Hi there, {name}!"


def add(a, b):
    # feature: validate types
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError("numeric only")
    return a + b


def multiply(a, b):
    return a * b


class Calculator:
    def __init__(self):
        self.history = []

    def compute(self, x, y):
        # feature: log every op
        result = x + y
        self.history.append(("add", x, y, result))
        return result

    def reset(self):
        self.history = []


def main():
    calc = Calculator()
    print(greet("feature-user"))
    print(calc.compute(10, 20))
    print(calc.history)


if __name__ == "__main__":
    main()
EOF
git commit -qam "feature: greet/add/compute/main updates"

# --- main branch: modify same regions differently ---
git checkout -q main
cat > app.py <<'EOF'
"""Sample application module."""


def greet(name):
    return f"Greetings, {name}."


def add(a, b):
    # main: log all additions
    print(f"adding {a} + {b}")
    return a + b


def multiply(a, b):
    return a * b


class Calculator:
    def __init__(self):
        self.history = []

    def compute(self, x, y):
        # main: support subtraction default
        result = x - y
        self.history.append(result)
        return result

    def reset(self):
        self.history = []


def main():
    calc = Calculator()
    print(greet("main-user"))
    print(calc.compute(100, 50))


if __name__ == "__main__":
    main()
EOF
git commit -qam "main: greet/add/compute/main updates"

# --- trigger the merge (expected to fail with conflicts) ---
if git merge --no-edit conflict-feature; then
    echo "Unexpected: merge succeeded without conflicts." >&2
    exit 1
fi

echo
echo "Test repo ready at: $REPO_PATH"
echo "On branch 'main', mid-merge with conflict-feature. Conflict hunks in app.py."
