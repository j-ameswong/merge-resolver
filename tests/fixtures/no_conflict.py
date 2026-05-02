"""Example Python file with no merge conflicts."""

import os
from pathlib import Path


def calculate_total(items):
    """Calculate the total of a list of items."""
    return sum(items)


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
