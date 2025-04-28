import numpy as np
import json
from typing import Dict, Any, List, Optional, Tuple
from .feedback_processor import FeedbackProcessor

class PreferenceOptimizer:
    """
    Advanced machine learning-based preference optimization for coffee brewing.
    """
    def __init__(
        self, 
        feedback_processor: Optional[FeedbackProcessor] = None,
        model_path: Optional[str] = None
    ):
        """
        Initialize the Preference Optimizer.
        
        Args:
            feedback_processor (FeedbackProcessor, optional): Existing feedback processor
            model_path (str, optional): Path to save/load optimization model
        """
        self.feedback_processor = feedback_processor or FeedbackProcessor()
        self.model_path = model_path or "coffee_preference_model.json"
        
        # Initialize model parameters
        self.model = self._load_model()
    
    def _load_model(self) -> Dict[str, Any]:
        """
        Load existing preference model or create a new one.
        
        Returns:
            Dict: Preference optimization model
        """
        try:
            with open(self.model_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Default model structure
            return {
                "global_preferences": {
                    "brewing_parameters": {
                        "water_temperature_c": {"mean": 92, "variance": 2},
                        "water_pressure_bar": {"mean": 9, "variance": 0.5}
                    },
                    "bean_preferences": {}
                },
                "user_specific_models": {}
            }
    
    def _save_model(self):
        """
        Save the current preference model.
        """
        try:
            with open(self.model_path, 'w') as f:
                json.dump(self.model, f, indent=2)
        except Exception as e:
            print(f"Error saving preference model: {e}")
    
    def optimize_brewing_parameters(
        self, 
        user_id: str, 
        current_brewing_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Optimize brewing parameters based on user's past preferences.
        
        Args:
            user_id (str): Unique identifier for the user
            current_brewing_details (Dict): Current brewing parameters
        
        Returns:
            Dict: Optimized brewing parameters
        """
        # Analyze user preferences
        user_preferences = self.feedback_processor.analyze_user_preferences(user_id)
        
        # If no significant preference data, use global model
        if user_preferences['preference_confidence'] < 0.3:
            return self._apply_global_model(current_brewing_details)
        
        # Prepare optimized parameters
        optimized_params = current_brewing_details.copy()
        trend_analysis = user_preferences['trend_analysis']
        
        # Optimize brewing parameters
        for param, details in trend_analysis.items():
            if param.startswith('param_'):
                param_name = param.split('_')[1]
                current_value = current_brewing_details.get(param_name)
                
                if current_value is not None and 'best_value' in details:
                    # Weighted adjustment based on user preference confidence
                    confidence = user_preferences['preference_confidence']
                    optimized_value = (
                        confidence * details['best_value'] + 
                        (1 - confidence) * current_value
                    )
                    optimized_params[param_name] = round(optimized_value, 2)
        
        return {
            "optimized_parameters": optimized_params,
            "optimization_confidence": user_preferences['preference_confidence']
        }
    
    def _apply_global_model(
        self, 
        current_brewing_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply global preference model when user-specific data is limited.
        
        Args:
            current_brewing_details (Dict): Current brewing parameters
        
        Returns:
            Dict: Globally optimized brewing parameters
        """
        global_prefs = self.model['global_preferences']['brewing_parameters']
        
        optimized_params = current_brewing_details.copy()
        
        # Adjust parameters based on global model
        for param, global_stats in global_prefs.items():
            current_value = current_brewing_details.get(param)
            
            if current_value is not None:
                # Apply slight adjustment towards global mean
                optimized_value = (current_value + global_stats['mean']) / 2
                optimized_params[param] = round(optimized_value, 2)
        
        return {
            "optimized_parameters": optimized_params,
            "optimization_confidence": 0.5  # Global model confidence
        }
    
    def update_global_model(
        self, 
        user_feedback: List[Dict[str, Any]]
    ) -> None:
        """
        Update the global preference model based on aggregated user feedback.
        
        Args:
            user_feedback (List[Dict]): Aggregated user feedback
        """
        # Collect brewing parameter data
        param_collections = {
            "water_temperature_c": [],
            "water_pressure_bar": []
        }
        
        # Aggregate parameter values
        for feedback in user_feedback:
            brewing_params = feedback.get('brewing_details', {}).get('brewing_parameters', {})
            for param, value in brewing_params.items():
                if param in param_collections:
                    param_collections[param].append(value)
        
        # Update global model with new statistics
        for param, values in param_collections.items():
            if values:
                # Calculate new mean and variance
                mean = np.mean(values)
                variance = np.var(values)
                
                # Update global model
                self.model['global_preferences']['brewing_parameters'][param] = {
                    "mean": round(mean, 2),
                    "variance": round(variance, 2)
                }
        
        # Save updated model
        self._save_model()
    
    def personalize_bean_selection(
        self, 
        user_id: str, 
        available_beans: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Personalize bean selection based on user's past preferences.
        
        Args:
            user_id (str): Unique identifier for the user
            available_beans (List[Dict]): List of available coffee beans
        
        Returns:
            List[Dict]: Personalized bean recommendations
        """
        # Analyze user preferences
        user_preferences = self.feedback_processor.analyze_user_preferences(user_id)
        
        # If no significant preference data, return available beans
        if user_preferences['preference_confidence'] < 0.3:
            return available_beans
        
        # Score beans based on user preferences
        scored_beans = []
        for bean in available_beans:
            bean_score = self._score_bean_for_user(bean, user_preferences)
            scored_beans.append({
                **bean,
                "personalization_score": bean_score
            })
        
        # Sort beans by personalization score
        personalized_beans = sorted(
            scored_beans, 
            key=lambda x: x.get('personalization_score', 0), 
            reverse=True
        )
        
        return personalized_beans
    
    def _score_bean_for_user(
        self, 
        bean: Dict[str, Any], 
        user_preferences: Dict[str, Any]
    ) -> float:
        """
        Calculate a personalization score for a bean.
        
        Args:
            bean (Dict): Bean details
            user_preferences (Dict): User's analyzed preferences
        
        Returns:
            float: Personalization score
        """
        # Initialize score
        score = 0
        
        # Check flavor notes match
        flavor_notes = bean.get('flavor_notes', [])
        trend_analysis = user_preferences.get('trend_analysis', {})
        
        for flavor in flavor_notes:
            for key, details in trend_analysis.items():
                if flavor.lower() in key.lower():
                    # Add score based on user's preference for this flavor
                    score += details.get('average_rating', 0) / 10
        
        # Consider user preference confidence
        score *= user_preferences.get('preference_confidence', 0.5)
        
        return score

    def track_user_model_evolution(
        self, 
        user_id: str, 
        time_window: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Track the evolution of a user's preferences over time.
        
        Args:
            user_id (str): Unique identifier for the user
            time_window (int, optional): Number of recent sessions to analyze
        
        Returns:
            Dict: User preference evolution insights
        """
        # Retrieve user's full feedback history
        user_feedbacks = self.feedback_processor.feedback_history.get(user_id, [])
        
        # Filter by time window if specified
        if time_window:
            user_feedbacks = user_feedbacks[-time_window:]
        
        # Analyze preference trends
        preference_evolution = {
            "overall_rating_trend": [],
            "parameter_trends": {
                "water_temperature_c": [],
                "water_pressure_bar": []
            },
            "flavor_exploration": set()
        }
        
        # Process feedback chronologically
        for feedback in user_feedbacks:
            # Track overall rating trend
            preference_evolution["overall_rating_trend"].append(feedback.get('rating', 0))
            
            # Track brewing parameter trends
            brewing_params = feedback.get('brewing_details', {}).get('brewing_parameters', {})
            for param in ["water_temperature_c", "water_pressure_bar"]:
                if param in brewing_params:
                    preference_evolution["parameter_trends"][param].append(brewing_params[param])
            
            # Track flavor exploration
            beans = feedback.get('brewing_details', {}).get('beans', [])
            for bean in beans:
                flavor_notes = bean.get('notes', '')
                if flavor_notes:
                    preference_evolution["flavor_exploration"].update(
                        [note.strip().lower() for note in flavor_notes.split(',')]
                    )
        
        # Convert flavor exploration to list
        preference_evolution["flavor_exploration"] = list(preference_evolution["flavor_exploration"])
        
        return preference_evolution

# Example usage demonstration
def main():
    # Initialize preference optimizer
    optimizer = PreferenceOptimizer()
    
    # Simulate user feedback
    user_id = "coffee_enthusiast_001"
    sample_feedback = [
        {
            "brewing_details": {
                "coffee_type": "espresso",
                "beans": [{"name": "Ethiopian Yirgacheffe", "notes": "fruity, floral"}],
                "brewing_parameters": {
                    "water_temperature_c": 94,
                    "water_pressure_bar": 9
                }
            },
            "rating": 8.5
        },
        {
            "brewing_details": {
                "coffee_type": "espresso",
                "beans": [{"name": "Brazilian Santos", "notes": "chocolatey, nutty"}],
                "brewing_parameters": {
                    "water_temperature_c": 92,
                    "water_pressure_bar": 9
                }
            },
            "rating": 7.0
        }
    ]
    
    # Demonstrate parameter optimization
    current_brewing = {
        "coffee_type": "espresso",
        "beans": [{"name": "Colombian Supremo"}],
        "brewing_parameters": {
            "water_temperature_c": 93,
            "water_pressure_bar": 9
        }
    }
    
    # Optimize brewing parameters
    optimized_params = optimizer.optimize_brewing_parameters(user_id, current_brewing)
    print("Optimized Parameters:")
    print(json.dumps(optimized_params, indent=2))
    
    # Update global model with feedback
    optimizer.update_global_model(sample_feedback)
    
    # Demonstrate bean personalization
    available_beans = [
        {
            "name": "Ethiopian Yirgacheffe",
            "flavor_notes": ["fruity", "floral"]
        },
        {
            "name": "Brazilian Santos",
            "flavor_notes": ["chocolatey", "nutty"]
        },
        {
            "name": "Guatemalan Antigua",
            "flavor_notes": ["caramel", "smooth"]
        }
    ]
    
    personalized_beans = optimizer.personalize_bean_selection(user_id, available_beans)
    print("\nPersonalized Bean Recommendations:")
    print(json.dumps(personalized_beans, indent=2))
    
    # Demonstrate preference evolution tracking
    preference_evolution = optimizer.track_user_model_evolution(user_id)
    print("\nPreference Evolution:")
    print(json.dumps(preference_evolution, indent=2))

if __name__ == "__main__":
    main()