import json
from typing import Dict, Any, Optional, List

from src.nlp.request_parser import CoffeeRequestParser
from src.nlp.prompt_generator import PromptGenerator
from src.database.coffee_database import CoffeeDatabase
from src.database.bean_selector import BeanSelector
from src.brewing.recommendation_engine import RecommendationEngine
from src.brewing.parameter_calculator import BrewingParameterCalculator
from src.ml.feedback_processor import FeedbackProcessor
from src.ml.preference_optimizer import PreferenceOptimizer

class CoffeeBrewingAssistant:
    """
    Main application class for the Coffee Brewing Assistant.
    Integrates all components to provide a comprehensive coffee brewing experience.
    """
    def __init__(
        self, 
        user_id: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        """
        Initialize the Coffee Brewing Assistant.
        
        Args:
            user_id (str, optional): Unique identifier for the user
            config_path (str, optional): Path to configuration file
        """
        # Load configuration (placeholder for future config management)
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.user_id = user_id or "default_user"
        self.coffee_database = CoffeeDatabase()
        self.bean_selector = BeanSelector(self.coffee_database)
        self.request_parser = CoffeeRequestParser()
        self.prompt_generator = PromptGenerator()
        self.feedback_processor = FeedbackProcessor()
        self.preference_optimizer = PreferenceOptimizer(self.feedback_processor)
        self.recommendation_engine = RecommendationEngine(
            self.coffee_database, 
            self.bean_selector
        )
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration file.
        
        Args:
            config_path (str, optional): Path to configuration file
        
        Returns:
            Dict: Configuration settings
        """
        # Default configuration
        default_config = {
            "database": {
                "species": "Arabica",
                "top_results": 5
            },
            "brewing": {
                "default_serving_size": 20.0,
                "default_coffee_type": "espresso"
            },
            "ml": {
                "personalization_threshold": 0.3
            }
        }
        
        # TODO: Implement actual config file loading
        return default_config
    
    def process_request(self, user_request: str) -> Dict[str, Any]:
        """
        Process a user's coffee brewing request.
        
        Args:
            user_request (str): Natural language coffee request
        
        Returns:
            Dict: Comprehensive coffee brewing recommendation
        """
        # Parse the request
        parsed_request = self.request_parser.parse_coffee_request(user_request)
        
        # Generate recommendation
        recommendation = self.recommendation_engine.generate_recommendation(
            flavor_preferences=parsed_request.get('flavor_notes'),
            coffee_type=parsed_request.get('coffee_type', 'espresso'),
            serving_size=parsed_request.get('size', 20.0)
        )
        
        return recommendation
    
    def record_brewing_feedback(
        self, 
        brewing_details: Dict[str, Any], 
        rating: float, 
        comments: Optional[str] = None
    ) -> None:
        """
        Record user feedback for a brewing session.
        
        Args:
            brewing_details (Dict): Details of the brewing parameters
            rating (float): User's rating (0-10 scale)
            comments (str, optional): Additional user comments
        """
        self.feedback_processor.record_brewing_feedback(
            self.user_id, 
            brewing_details, 
            rating, 
            comments
        )
        
        # Optimize preferences based on feedback
        optimized_params = self.preference_optimizer.optimize_brewing_parameters(
            self.user_id, 
            brewing_details
        )
    
    def explore_flavor_profiles(
        self, 
        species: str = 'Arabica', 
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Explore top flavor profiles for a given coffee species.
        
        Args:
            species (str): Coffee species to explore
            top_n (int): Number of top flavor profiles to return
        
        Returns:
            List[Dict]: Top flavor profiles
        """
        return self.recommendation_engine.explore_flavor_profiles(species, top_n)

# Example usage demonstration
def main():
    # Initialize the Coffee Brewing Assistant
    assistant = CoffeeBrewingAssistant(user_id="coffee_lover_001")
    
    # Test different coffee requests
    test_requests = [
        "I want a fruity espresso with bright notes",
        "Make me a large cappuccino with chocolatey flavor",
        "Can I have a pour-over with nutty profile?"
    ]
    
    for request in test_requests:
        print(f"\n--- Processing Request: {request} ---")
        recommendation = assistant.process_request(request)
        
        # Pretty print recommendation
        print(json.dumps(recommendation, indent=2))
        
        # Simulate user feedback
        assistant.record_brewing_feedback(
            brewing_details=recommendation,
            rating=8.5,
            comments="Enjoyed the recommendation!"
        )
    
    # Explore flavor profiles
    print("\n--- Flavor Profile Exploration ---")
    flavor_profiles = assistant.explore_flavor_profiles()
    print(json.dumps(flavor_profiles, indent=2))

if __name__ == "__main__":
    main()