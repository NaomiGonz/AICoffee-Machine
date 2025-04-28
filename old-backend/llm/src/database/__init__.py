"""
Database module for the Coffee Brewing Assistant.

This module handles loading, processing, and managing coffee-related datasets.
"""

from .coffee_database import CoffeeDatabase
from .bean_selector import BeanSelector

__all__ = ['CoffeeDatabase', 'BeanSelector']