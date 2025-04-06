"""
NLP module for the Coffee Brewing Assistant.

This module handles natural language processing for coffee requests.
"""

from .request_parser import CoffeeRequestParser
from .prompt_generator import PromptGenerator
from .llm_handler import LLMHandler

__all__ = ['CoffeeRequestParser', 'PromptGenerator', 'LLMHandler']
"""
NLP module for the Coffee Brewing Assistant.

This module handles natural language processing for coffee requests.
"""

from .request_parser import CoffeeRequestParser
from .prompt_generator import PromptGenerator

__all__ = ['CoffeeRequestParser', 'PromptGenerator']