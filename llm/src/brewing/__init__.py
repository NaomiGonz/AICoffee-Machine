"""
Brewing module for the Coffee Brewing Assistant.

This module handles brewing parameter calculation and recommendations.
"""

from .parameter_calculator import BrewingParameterCalculator
from .recommendation_engine import RecommendationEngine

__all__ = ['BrewingParameterCalculator', 'RecommendationEngine']