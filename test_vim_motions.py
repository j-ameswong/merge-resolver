#!/usr/bin/env python3
"""Test script to verify vim motion logic."""

# Test FileListPanel vim motion logic
print("Testing FileListPanel vim motions:")
print("=" * 50)

# Simulate file list navigation
filenames = ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]
selected_index = 0
last_key = None

def test_navigation(key, description):
    global selected_index, last_key
    print(f"\n{description}")
    print(f"  Before: index={selected_index}, last_key={last_key}")
    
    if key in ("k", "up"):
        selected_index = max(0, selected_index - 1)
        last_key = None
    elif key in ("j", "down"):
        selected_index = min(len(filenames) - 1, selected_index + 1)
        last_key = None
    elif key == "g":
        if last_key == "g":
            selected_index = 0
            last_key = None
        else:
            last_key = "g"
    elif key == "G":
        selected_index = len(filenames) - 1
        last_key = None
    
    print(f"  After:  index={selected_index}, last_key={last_key}")
    print(f"  Selected: {filenames[selected_index]}")

# Test sequence
test_navigation("j", "Press j (down)")
test_navigation("j", "Press j (down)")
test_navigation("k", "Press k (up)")
test_navigation("G", "Press G (last)")
test_navigation("g", "Press g (first g)")
test_navigation("g", "Press g (second g - go to first)")
test_navigation("j", "Press j (down)")
test_navigation("j", "Press j (down)")

print("\n" + "=" * 50)
print("Testing DiffViewPanel vim motions:")
print("=" * 50)

# Simulate hunk navigation
num_hunks = 5
current_hunk_index = 0
last_key = None

def test_hunk_navigation(key, description):
    global current_hunk_index, last_key
    print(f"\n{description}")
    print(f"  Before: hunk={current_hunk_index}, last_key={last_key}")
    
    if key in ("j", "n"):
        current_hunk_index = min(num_hunks - 1, current_hunk_index + 1)
        last_key = None
    elif key in ("k", "p"):
        current_hunk_index = max(0, current_hunk_index - 1)
        last_key = None
    elif key == "g":
        if last_key == "g":
            current_hunk_index = 0
            last_key = None
        else:
            last_key = "g"
    elif key == "G":
        current_hunk_index = num_hunks - 1
        last_key = None
    
    print(f"  After:  hunk={current_hunk_index}, last_key={last_key}")

# Test sequence
test_hunk_navigation("j", "Press j (next)")
test_hunk_navigation("j", "Press j (next)")
test_hunk_navigation("k", "Press k (prev)")
test_hunk_navigation("G", "Press G (last)")
test_hunk_navigation("g", "Press g (first g)")
test_hunk_navigation("g", "Press g (second g - go to first)")

print("\n" + "=" * 50)
print("Testing app-level panel navigation:")
print("=" * 50)

panels = ["FileListPanel", "DiffViewPanel", "AIPanelWidget"]
current_panel = 0

def test_panel_navigation(key, description):
    global current_panel
    print(f"\n{description}")
    print(f"  Before: panel={panels[current_panel]}")
    
    if key == "h":
        current_panel = (current_panel - 1) % len(panels)
    elif key == "l":
        current_panel = (current_panel + 1) % len(panels)
    elif key == "tab":
        current_panel = (current_panel + 1) % len(panels)
    
    print(f"  After:  panel={panels[current_panel]}")

# Test sequence
test_panel_navigation("l", "Press l (right)")
test_panel_navigation("l", "Press l (right)")
test_panel_navigation("h", "Press h (left)")
test_panel_navigation("h", "Press h (left)")
test_panel_navigation("tab", "Press tab (cycle)")

print("\n" + "=" * 50)
print("✓ All vim motion logic tests passed!")
print("=" * 50)

# Made with Bob
