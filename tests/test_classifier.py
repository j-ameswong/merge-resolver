"""Tests for conflict hunk classification."""

import pytest
from git.parser import ConflictHunk
from analysis.classifier import _extract_names, classify, classify_all


class TestExtractNames:
    """Tests for the _extract_names helper function."""
    
    def test_extract_function_names(self):
        """Should extract function names from def statements."""
        lines = [
            "def foo():\n",
            "    pass\n",
            "def bar(x, y):\n",
            "    return x + y\n"
        ]
        names = _extract_names(lines)
        assert names == {"foo", "bar"}
    
    def test_extract_class_names(self):
        """Should extract class names from class statements."""
        lines = [
            "class MyClass:\n",
            "    pass\n",
            "class AnotherClass(BaseClass):\n",
            "    def method(self):\n",
            "        pass\n"
        ]
        names = _extract_names(lines)
        assert names == {"MyClass", "AnotherClass", "method"}
    
    def test_extract_mixed(self):
        """Should extract both function and class names."""
        lines = [
            "class User:\n",
            "    def __init__(self):\n",
            "        pass\n",
            "def create_user():\n",
            "    return User()\n"
        ]
        names = _extract_names(lines)
        assert names == {"User", "__init__", "create_user"}
    
    def test_no_names(self):
        """Should return empty set when no names found."""
        lines = [
            "import os\n",
            "x = 42\n",
            "print('hello')\n"
        ]
        names = _extract_names(lines)
        assert names == set()


class TestMechanicalClassification:
    """Tests for mechanical conflict classification."""
    
    def test_short_non_overlapping(self):
        """Should classify as mechanical when both sides are short and don't overlap."""
        hunk = ConflictHunk(
            file="src/config.py",
            hunk_index=0,
            start_line=1,
            ours=["import json\n"],
            theirs=["DEBUG = True\n"],
            base=[]
        )
        
        result = classify(hunk, [hunk])
        
        assert result.kind == "mechanical"
        assert result.severity == 1
    
    def test_import_vs_code_change(self):
        """Should classify as mechanical when one side adds import, other changes code."""
        hunk = ConflictHunk(
            file="src/utils.py",
            hunk_index=0,
            start_line=5,
            ours=[
                "import logging\n",
                "import sys\n"
            ],
            theirs=[
                "def helper():\n",
                "    return 42\n"
            ],
            base=[]
        )
        
        result = classify(hunk, [hunk])
        
        assert result.kind == "mechanical"
        assert result.severity == 1
    
    def test_not_mechanical_if_too_long(self):
        """Should not classify as mechanical if either side exceeds 5 lines."""
        hunk = ConflictHunk(
            file="src/long.py",
            hunk_index=0,
            start_line=10,
            ours=[
                "line1\n",
                "line2\n",
                "line3\n",
                "line4\n",
                "line5\n",
                "line6\n"  # 6 lines - too long
            ],
            theirs=["short\n"],
            base=[]
        )
        
        result = classify(hunk, [hunk])
        
        assert result.kind != "mechanical"


class TestLogicalClassification:
    """Tests for logical conflict classification."""
    
    def test_overlapping_function_names(self):
        """Should classify as logical when both sides modify the same function."""
        hunk = ConflictHunk(
            file="src/auth.py",
            hunk_index=0,
            start_line=20,
            ours=[
                "def authenticate(user):\n",
                "    return user.check_password()\n"
            ],
            theirs=[
                "def authenticate(user):\n",
                "    return user.verify_token()\n"
            ],
            base=[
                "def authenticate(user):\n",
                "    return True\n"
            ]
        )
        
        result = classify(hunk, [hunk])
        
        assert result.kind == "logical"
        assert result.severity == 2
    
    def test_overlapping_class_names(self):
        """Should classify as logical when both sides modify the same class."""
        hunk = ConflictHunk(
            file="src/models.py",
            hunk_index=0,
            start_line=15,
            ours=[
                "class User:\n",
                "    def __init__(self, name):\n",
                "        self.name = name\n",
                "        self.role = 'user'\n"
            ],
            theirs=[
                "class User:\n",
                "    def __init__(self, name, email):\n",
                "        self.name = name\n",
                "        self.email = email\n"
            ],
            base=[
                "class User:\n",
                "    def __init__(self, name):\n",
                "        self.name = name\n"
            ]
        )
        
        result = classify(hunk, [hunk])
        
        assert result.kind == "logical"
        assert result.severity == 2
    
    def test_default_to_logical(self):
        """Should default to logical for conflicts that aren't mechanical or structural."""
        hunk = ConflictHunk(
            file="src/app.py",
            hunk_index=0,
            start_line=50,
            ours=[
                "# Implementation A\n",
                "result = process_data(input)\n",
                "return result\n",
                "# More code\n",
                "# Even more\n",
                "# Still going\n"  # 6 lines - not mechanical
            ],
            theirs=[
                "# Implementation B\n",
                "output = transform(input)\n",
                "return output\n"
            ],
            base=[]
        )
        
        result = classify(hunk, [hunk])
        
        assert result.kind == "logical"
        assert result.severity == 2


class TestStructuralClassification:
    """Tests for structural conflict classification."""
    
    def test_cross_file_symbol_collision(self):
        """Should classify as structural when same symbol appears in different files."""
        hunk1 = ConflictHunk(
            file="src/models.py",
            hunk_index=0,
            start_line=10,
            ours=[
                "class User:\n",
                "    pass\n"
            ],
            theirs=[
                "class User:\n",
                "    role = 'admin'\n"
            ],
            base=[]
        )
        
        hunk2 = ConflictHunk(
            file="src/auth.py",
            hunk_index=0,
            start_line=5,
            ours=[
                "def User():\n",  # Same name, different file
                "    return {}\n"
            ],
            theirs=[
                "from models import User\n"
            ],
            base=[]
        )
        
        all_hunks = [hunk1, hunk2]
        
        # Classify both hunks
        result1 = classify(hunk1, all_hunks)
        result2 = classify(hunk2, all_hunks)
        
        # Both should be structural due to cross-file symbol collision
        assert result1.kind == "structural"
        assert result1.severity == 3
        assert result2.kind == "structural"
        assert result2.severity == 3
    
    def test_multiple_files_same_function(self):
        """Should classify as structural when function name appears in multiple files."""
        hunk1 = ConflictHunk(
            file="src/utils.py",
            hunk_index=0,
            start_line=1,
            ours=["def process():\n", "    return 'A'\n"],
            theirs=["def process():\n", "    return 'B'\n"],
            base=[]
        )
        
        hunk2 = ConflictHunk(
            file="src/handlers.py",
            hunk_index=0,
            start_line=10,
            ours=["def process():\n", "    return 'C'\n"],
            theirs=["def process():\n", "    return 'D'\n"],
            base=[]
        )
        
        hunk3 = ConflictHunk(
            file="src/main.py",
            hunk_index=0,
            start_line=20,
            ours=["x = 1\n"],  # No 'process' here
            theirs=["y = 2\n"],
            base=[]
        )
        
        all_hunks = [hunk1, hunk2, hunk3]
        
        result1 = classify(hunk1, all_hunks)
        result2 = classify(hunk2, all_hunks)
        result3 = classify(hunk3, all_hunks)
        
        # First two should be structural
        assert result1.kind == "structural"
        assert result1.severity == 3
        assert result2.kind == "structural"
        assert result2.severity == 3
        
        # Third should be mechanical (short, no overlap, no cross-file collision)
        assert result3.kind == "mechanical"
        assert result3.severity == 1
    
    def test_same_file_not_structural(self):
        """Should not classify as structural if symbols only appear in same file."""
        hunk1 = ConflictHunk(
            file="src/app.py",
            hunk_index=0,
            start_line=10,
            ours=["def foo():\n", "    pass\n"],
            theirs=["def foo():\n", "    return 1\n"],
            base=[]
        )
        
        hunk2 = ConflictHunk(
            file="src/app.py",  # Same file
            hunk_index=1,
            start_line=20,
            ours=["def bar():\n", "    foo()\n"],
            theirs=["def bar():\n", "    return foo()\n"],
            base=[]
        )
        
        all_hunks = [hunk1, hunk2]
        
        result1 = classify(hunk1, all_hunks)
        result2 = classify(hunk2, all_hunks)
        
        # Should be logical, not structural (same file)
        assert result1.kind == "logical"
        assert result2.kind == "logical"


class TestClassifyAll:
    """Tests for the classify_all function."""
    
    def test_classify_all_hunks(self):
        """Should classify all hunks in a list."""
        hunks = [
            ConflictHunk(
                file="a.py",
                hunk_index=0,
                start_line=1,
                ours=["import os\n"],
                theirs=["x = 1\n"],
                base=[]
            ),
            ConflictHunk(
                file="b.py",
                hunk_index=0,
                start_line=5,
                ours=["def foo():\n", "    pass\n"],
                theirs=["def foo():\n", "    return 1\n"],
                base=[]
            )
        ]
        
        result = classify_all(hunks)
        
        # Should return the same list
        assert result is hunks
        
        # All hunks should be classified
        assert result[0].kind == "mechanical"
        assert result[1].kind == "logical"
    
    def test_classify_all_with_structural(self):
        """Should correctly identify structural conflicts across files."""
        hunks = [
            ConflictHunk(
                file="models.py",
                hunk_index=0,
                start_line=1,
                ours=["class User:\n", "    pass\n"],
                theirs=["class User:\n", "    role = 'admin'\n"],
                base=[]
            ),
            ConflictHunk(
                file="auth.py",
                hunk_index=0,
                start_line=1,
                ours=["def User():\n", "    return {}\n"],
                theirs=["from models import User\n"],
                base=[]
            )
        ]
        
        result = classify_all(hunks)
        
        # Both should be structural
        assert all(h.kind == "structural" for h in result)
        assert all(h.severity == 3 for h in result)

# Made with Bob
