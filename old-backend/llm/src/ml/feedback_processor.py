import json
from typing import Dict, Any, List, Optional
from datetime import datetime

class FeedbackProcessor:
    """
    Processes and stores user feedback for coffee brewing preferences.
    """
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the feedback processor.
        
        Args:
            storage_path (str, optional): Path to store feedback data
        """
        self.storage_path = storage_path or "user_feedback.json"
        self.feedback_history = self._load_feedback()
    
    def _load_feedback(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load existing feedback data from storage.
        
        Returns:
            Dict: Stored user feedback
        """
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_feedback(self):
        """
        Save feedback data to storage.
        """
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.feedback_history, f, indent=2)
        except Exception as e:
            print(f"Error saving feedback: {e}")
    
    def record_brewing_feedback(
        self, 
        user_id: str, 
        brewing_details: Dict[str, Any], 
        rating: float, 
        comments: Optional[str] = None
    ) -> None:
        """
        Record feedback for a specific brewing session.
        
        Args:
            user_id (str): Unique identifier for the user
            brewing_details (Dict): Details of the brewing parameters
            rating (float): User's rating (0-10 scale)
            comments (str, optional): Additional user comments
        """
        # Validate input
        if not (0 <= rating <= 10):
            raise ValueError("Rating must be between 0 and 10")
        
        # Prepare feedback entry
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "brewing_details": brewing_details,
            "rating": rating,
            "comments": comments
        }
        
        # Store feedback
        if user_id not in self.feedback_history:
            self.feedback_history[user_id] = []
        
        self.feedback_history[user_id].append(feedback_entry)
        
        # Save to persistent storage
        self._save_feedback()
    
    def analyze_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze a user's brewing preferences based on their feedback.
        
        Args:
            user_id (str): Unique identifier for the user
        
        Returns:
            Dict: Analyzed user preferences
        """
        # Check if user has feedback history
        user_feedbacks = self.feedback_history.get(user_id, [])
        if not user_feedbacks:
            return {
                "preference_confidence": 0,
                "average_rating": None,
                "trend_analysis": {}
            }
        
        # Calculate average rating
        average_rating = sum(fb['rating'] for fb in user_feedbacks) / len(user_feedbacks)
        
        # Analyze brewing parameter trends
        preference_trends = {}
        for feedback in user_feedbacks:
            brewing_details = feedback['brewing_details']
            
            # Track bean preferences
            for bean in brewing_details.get('beans', []):
                bean_name = bean.get('name', 'Unknown')
                preference_trends.setdefault(f"bean_{bean_name}", []).append(feedback['rating'])
            
            # Track brewing parameters
            params = brewing_details.get('brewing_parameters', {})
            for param, value in params.items():
                preference_trends.setdefault(f"param_{param}", []).append({
                    'value': value,
                    'rating': feedback['rating']
                })
        
        # Calculate preference trends
        analyzed_trends = {}
        for key, ratings in preference_trends.items():
            if not ratings:
                continue
                
            if isinstance(ratings[0], dict):
                # For parameters with numeric values
                avg_rating_by_value = {}
                for entry in ratings:
                    value_key = str(entry['value'])  # Convert to string to ensure it can be a dictionary key
                    avg_rating_by_value.setdefault(value_key, []).append(entry['rating'])
                
                if avg_rating_by_value:
                    # Find the best value with highest average rating
                    best_value_key = max(
                        avg_rating_by_value.items(), 
                        key=lambda x: sum(x[1]) / len(x[1]) if x[1] else 0
                    )[0]
                    
                    # Calculate the average rating for this parameter
                    param_ratings = [entry['rating'] for entry in ratings]
                    
                    analyzed_trends[key] = {
                        "best_value": best_value_key,
                        "average_rating": sum(param_ratings) / len(param_ratings) if param_ratings else 0
                    }
            else:
                # For categorical preferences like beans
                analyzed_trends[key] = {
                    "average_rating": sum(ratings) / len(ratings) if ratings else 0,
                    "preference_count": len(ratings)
                }
        
        return {
            "preference_confidence": min(1, len(user_feedbacks) / 10),
            "average_rating": average_rating,
            "trend_analysis": analyzed_trends
        }
    
    def recommend_adjustments(
        self, 
        user_id: str, 
        current_brewing_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recommend brewing adjustments based on user's past preferences.
        
        Args:
            user_id (str): Unique identifier for the user
            current_brewing_details (Dict): Current brewing parameters
        
        Returns:
            Dict: Recommended brewing adjustments
        """
        # Analyze user preferences
        user_preferences = self.analyze_user_preferences(user_id)
        
        # If no significant preference data, return original details
        if user_preferences['preference_confidence'] < 0.3:
            return {
                "adjustments": {},
                "recommendation_confidence": user_preferences['preference_confidence']
            }
        
        # Prepare adjustments
        adjustments = {}
        trend_analysis = user_preferences['trend_analysis']
        
        # Example adjustment logic
        for param, details in trend_analysis.items():
            if param.startswith('param_'):
                # Suggest adjusting brewing parameters
                param_name = param.split('_', 1)[1]  # Get everything after the first underscore
                current_value = None
                
                # Try to find the parameter in current brewing details
                if param_name in current_brewing_details:
                    current_value = current_brewing_details[param_name]
                elif 'brewing_parameters' in current_brewing_details:
                    current_value = current_brewing_details['brewing_parameters'].get(param_name)
                
                if current_value is not None and 'best_value' in details:
                    adjustments[param_name] = details['best_value']
        
        return {
            "adjustments": adjustments,
            "recommendation_confidence": user_preferences['preference_confidence']
        }

# Example usage demonstration
def main():
    # Initialize feedback processor
    feedback_processor = FeedbackProcessor()
    
    # Simulate user brewing sessions and feedback
    user_id = "coffee_enthusiast_001"
    
    # Example brewing details
    brewing_sessions = [
        {
            "brewing_details": {
                "coffee_type": "espresso",
                "beans": [{"name": "Ethiopian Yirgacheffe"}],
                "brewing_parameters": {
                    "water_temperature_c": 94,
                    "water_pressure_bar": 9
                }
            },
            "rating": 8.5,
            "comments": "Fruity and bright!"
        },
        {
            "brewing_details": {
                "coffee_type": "espresso",
                "beans": [{"name": "Brazilian Santos"}],
                "brewing_parameters": {
                    "water_temperature_c": 92,
                    "water_pressure_bar": 9
                }
            },
            "rating": 7.0,
            "comments": "A bit less exciting"
        }
    ]
    
    # Record feedback for multiple brewing sessions
    for session in brewing_sessions:
        feedback_processor.record_brewing_feedback(
            user_id,
            session['brewing_details'],
            session['rating'],
            session['comments']
        )
    
    # Analyze user preferences
    print("User Preference Analysis:")
    preferences = feedback_processor.analyze_user_preferences(user_id)
    print(json.dumps(preferences, indent=2))
    
    # Get brewing recommendations
    print("\nBrewing Recommendations:")
    current_brewing = {
        "coffee_type": "espresso",
        "beans": [{"name": "Colombian Supremo"}],
        "brewing_parameters": {
            "water_temperature_c": 93,
            "water_pressure_bar": 9
        }
    }
    recommendations = feedback_processor.recommend_adjustments(user_id, current_brewing)
    print(json.dumps(recommendations, indent=2))

if __name__ == "__main__":
    main()