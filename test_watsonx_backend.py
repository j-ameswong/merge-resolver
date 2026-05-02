#!/usr/bin/env python3
"""Test script to verify watsonx.ai backend integration."""

import os
import sys

# Check for required environment variables
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")

if not WATSONX_API_KEY or not WATSONX_PROJECT_ID:
    print("❌ Missing required environment variables:")
    if not WATSONX_API_KEY:
        print("   - WATSONX_API_KEY")
    if not WATSONX_PROJECT_ID:
        print("   - WATSONX_PROJECT_ID")
    print()
    print("Please set them before running this test:")
    print("  export WATSONX_API_KEY='your-api-key'")
    print("  export WATSONX_PROJECT_ID='your-project-id'")
    print("  export AI_BACKEND='watsonx'")
    sys.exit(1)

# Force watsonx backend
os.environ["AI_BACKEND"] = "watsonx"

print("=" * 70)
print("TESTING WATSONX.AI BACKEND")
print("=" * 70)
print()
print(f"✓ WATSONX_API_KEY: {WATSONX_API_KEY[:10]}...{WATSONX_API_KEY[-4:]}")
print(f"✓ WATSONX_PROJECT_ID: {WATSONX_PROJECT_ID}")
print(f"✓ AI_BACKEND: {os.getenv('AI_BACKEND')}")
print()

from git.parser import ConflictHunk
from analysis.bob import analyse_hunk

# Test 1: Simple logical conflict
print("Test 1: Analyzing a logical conflict...")
print("-" * 70)

hunk = ConflictHunk(
    file="auth.py",
    hunk_index=0,
    start_line=10,
    ours=["def authenticate(user):\n", "    return check_jwt(user)\n"],
    theirs=["def authenticate(user):\n", "    return check_session(user)\n"],
    base=["def authenticate(user):\n", "    return check_password(user)\n"],
    kind="logical",
    severity=2
)

print(f"File: {hunk.file}")
print(f"Conflict type: {hunk.kind}")
print()
print("OURS (main):")
print("".join(hunk.ours))
print()
print("THEIRS (feature):")
print("".join(hunk.theirs))
print()

print("Calling watsonx.ai API...")
result = analyse_hunk(hunk, "main", "feature-auth")

print()
print("WATSONX.AI RESPONSE:")
print("-" * 70)
print(f"Summary: {result.ai_summary}")
print()
print(f"Suggestion: {result.ai_suggestion}")
print()

# Verify it's not the mock response
if result.ai_summary == "Both branches modified the same function in incompatible ways.":
    print("⚠️  WARNING: This looks like the mock backend response!")
    print("   Make sure AI_BACKEND=watsonx is set in your environment")
    print("   The backend selection happens when the module is imported")
else:
    print("✓ Received unique response from watsonx.ai!")

print()
print("=" * 70)
print("Test complete!")
print("=" * 70)

# Made with Bob
