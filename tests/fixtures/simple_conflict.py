"""Example Python file with a realistic diff3-style merge conflict."""

import os
from pathlib import Path


def calculate_total(items):
    """Calculate the total of a list of items."""
<<<<<<< HEAD
    # Use sum with generator for efficiency
    return sum(item * 1.1 for item in items)
||||||| base
    total = 0
    for item in items:
        total += item
    return total
=======
    # Add 10% tax to each item
    total = 0
    for item in items:
        total += item * 1.1
    return total
>>>>>>> feature/tax-calculation


def get_config_path():
    """Get the path to the configuration file."""
    return Path.home() / ".config" / "app.conf"


class DataProcessor:
    """Process data from various sources."""
    
    def __init__(self, source):
        self.source = source
        self.cache = {}
    
    def process(self, data):
        """Process the input data."""
        if data in self.cache:
            return self.cache[data]
        
        result = self._transform(data)
        self.cache[data] = result
        return result
    
    def _transform(self, data):
        """Transform the data."""
        return data.upper()

# Made with Bob
