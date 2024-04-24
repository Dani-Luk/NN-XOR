"""
This file is used to add the src folder to the python path so that the unit tests can import the modules from the src folder.
The TestCase_ext class extends the unittest.TestCase class with additional assertIterableAlmostEqual method.
The get_seed_rng function returns a random seed and a random number generator initialized with,
which will be used to generate random but reproducible data in the unit tests.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..' , "src")))
# the unit_tests folder must be at the same level as the src folder

import numpy as np
from typing import Tuple
from itertools import zip_longest 
from unittest import TestCase

class TestCase_ext(TestCase):
    """Extends the unittest.TestCase class with additional assertIterableAlmostEqual method."""
    
    def assertIterableAlmostEqual(self, item1, item2, msg:str = "", *args, **kwargs):
        """
        Asserts that two iterables are almost equal element-wise.
        
        Args:
            item1: The first iterable to compare.
            item2: The second iterable to compare.
            msg (optional): An optional error message to display if the assertion fails.
        """
        # if hasattr(item1, '__iter__') and hasattr(item2, '__iter__'):
        try:
            _ = iter(item1) # check if iterable
            _ = iter(item2) # check if iterable
            for i1, i2 in zip_longest(item1, item2): # if not same length will fail when comparing to None 
                self.assertIterableAlmostEqual(i1, i2, msg=msg, *args, **kwargs)
        # else:
        except TypeError:
            self.assertAlmostEqual(item1, item2, msg=msg, *args, **kwargs)

    @staticmethod
    def get_seed_rng() -> Tuple[int, np.random.Generator]:
        """
        Returns a random seed and a random number generator initialized with.
        
        Returns:
            A tuple containing a seed and a random number generator.
        """
        seed = np.random.default_rng().integers(65535)
        rng = np.random.default_rng(seed=seed)
        return seed, rng

