from typing import List, Dict, Any, Optional
from ..database.coffee_database import CoffeeDatabase
from ..database.bean_selector import BeanSelector
from ..brewing.parameter_calculator import BrewingParameterCalculator

class RecommendationEngine:
    """
    Provides comprehensive coffee brewing recommendations.
    """
    def __init__(
        self, 
        coffee_database: Optional[CoffeeDatabase] = None,
        bean_selector: Optional[BeanSelector] = None
    ):
        """
        Initialize the recommendation engine.
        
        Args:
            coffee_database (CoffeeDatabase, optional): Database of coffee information
            bean_selector (BeanSelector, optional): Bean selection module
        """
        self.coffee_database = coffee_database or CoffeeDatabase()
        self.bean_selector = bean_selector or BeanSelector(self.coffee_database)
        
        # Map mood-based flavor enhancements
        self.mood_flavor_map = {
            "energetic": ["bold", "bright", "fruity"],
            "relaxed": ["smooth", "chocolatey", "balanced"],
            "creative": ["fruity", "complex", "floral"],
            "stressed": ["nutty", "smooth", "sweet"],
            "morning": ["bright", "bold"],
            "afternoon": ["balanced", "sweet"],
            "evening": ["smooth", "chocolatey", "decaf"]
        }
        
        # Temperature preferences by mood
        self.mood_temp_preferences = {
            "energetic": 1.0,  # Slightly hotter
            "relaxed": -0.5,   # Slightly cooler
            "stressed": -1.0,  # Cooler
            "creative": 0      # Neutral
        }
    
    def generate_recommendation(
        self,
        flavor_preferences: Optional[List[str]] = None,
        coffee_type: str = 'espresso',
        serving_size: float = 7.0,
        user_mood: Optional[str] = None,
        roast_preference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive coffee recommendation with enhanced handling
        of various coffee types and flavor profiles.
        """
        # Start with empty flavor notes list if none provided
        if flavor_preferences is None:
            flavor_preferences = []
        
        # Normalize coffee type
        normalized_coffee_type = self._normalize_coffee_type(coffee_type)
        
        # Enhance with mood-based flavor preferences
        enhanced_flavor_notes = self._enhance_with_mood(flavor_preferences, user_mood)
        
        # If still no flavor notes, provide defaults based on coffee type
        if not enhanced_flavor_notes:
            enhanced_flavor_notes = self._get_default_flavors(normalized_coffee_type)
        
        # Select beans with serving size
        selected_beans = self.bean_selector.select_beans(
            normalized_coffee_type, 
            enhanced_flavor_notes, 
            serving_size=serving_size
        )
        
        # Calculate brewing parameters
        brewing_params = BrewingParameterCalculator.calculate_brewing_parameters(
            normalized_coffee_type, 
            selected_beans, 
            serving_size=serving_size
        )
        
        # Get brewing suggestions from bean selector
        brewing_suggestions = self.bean_selector.suggest_brewing_notes(
            selected_beans,
            normalized_coffee_type
        )
        
        # Enhance flavor profile description
        enhanced_flavor_profile = self._enhance_flavor_profile_for_coffee_type(
            brewing_suggestions.get("flavor_profile", ""),
            normalized_coffee_type,
            enhanced_flavor_notes
        )
        
        # Generate brewing instructions
        brewing_instructions = self._generate_brewing_instructions(
            normalized_coffee_type,
            enhanced_flavor_notes,
            user_mood
        )
        
        # Compile comprehensive recommendation
        recommendation = {
            "coffee_type": normalized_coffee_type,
            "recommended_beans": selected_beans,
            "brewing_parameters": brewing_params,
            "flavor_profile": enhanced_flavor_profile,
            "recommended_temperature": brewing_suggestions.get("recommended_brewing_temp", brewing_params.get("recommended_temp_c", 93)),
            "additional_notes": brewing_suggestions.get("additional_notes", []),
            "brewing_instructions": brewing_instructions
        }
        
        return recommendation
    
    def _normalize_coffee_type(self, coffee_type: str) -> str:
        """
        Normalize coffee type to standard format.
        """
        if not coffee_type:
            return 'espresso'
        
        # Convert to lowercase and strip whitespace
        normalized = coffee_type.lower().strip()
        
        # Check for known aliases
        coffee_type_aliases = {
            "americano": "americano",
            "filter": "drip",
            "filter coffee": "drip",
            "pour over": "pour-over",
            "pourover": "pour-over",
            "french press": "french-press",
            "cold brew": "cold-brew",
            "iced coffee": "cold-brew",
            "cappucino": "cappuccino",
            "machiato": "macchiato",
            "expresso": "espresso"  # Common misspelling
        }
        
        if normalized in coffee_type_aliases:
            return coffee_type_aliases[normalized]
        
        # Replace underscore with hyphen
        if '_' in normalized:
            normalized = normalized.replace('_', '-')
            
        return normalized
    
    def _enhance_flavor_profile_for_coffee_type(
        self,
        flavor_profile: str,
        coffee_type: str,
        flavor_notes: List[str]
    ) -> str:
        """
        Enhance flavor profile description based on coffee type presentation.
        """
        # Coffee presentation flavor enhancements
        coffee_presentation_flavors = {
            "cappuccino": {
                "smooth": "extra smooth and creamy",
                "bold": "bold with creamy texture",
                "chocolatey": "rich chocolate with creamy milk",
                "nutty": "nutty character complemented by steamed milk",
                "fruity": "subtle fruit notes balanced with milk"
            },
            "latte": {
                "smooth": "exceptionally smooth and mild",
                "bold": "bold undertones with creamy mouthfeel",
                "chocolatey": "milk chocolate smoothness",
                "nutty": "delicate nutty notes with silky texture",
                "fruity": "subtle fruit essence with creamy finish"
            },
            "americano": {
                "smooth": "smooth with clean finish",
                "bold": "bold character diluted to perfect strength",
                "chocolatey": "subtle chocolate notes with medium body",
                "nutty": "gentle nutty flavor with medium body",
                "fruity": "bright fruit notes with clean finish"
            }
        }
        
        # If coffee type doesn't need special enhancement, return as is
        if coffee_type not in coffee_presentation_flavors:
            return flavor_profile
            
        # Look for primary flavor to enhance
        primary_flavor = None
        for note in flavor_notes:
            if note in coffee_presentation_flavors[coffee_type]:
                primary_flavor = note
                break
        
        # If no match found, use first flavor note if available
        if not primary_flavor and flavor_notes:
            primary_flavor = flavor_notes[0]
            
        # If still no primary flavor or no specific enhancement available, return as is
        if not primary_flavor or primary_flavor not in coffee_presentation_flavors[coffee_type]:
            return flavor_profile
            
        # Return enhanced description
        return coffee_presentation_flavors[coffee_type][primary_flavor]

    def _enhance_with_mood(
        self, 
        flavor_preferences: List[str],
        user_mood: Optional[str]
    ) -> List[str]:
        """
        Enhance flavor preferences with mood-based suggestions.
        
        Args:
            flavor_preferences (List[str]): Explicit flavor preferences
            user_mood (str, optional): User's current mood or occasion
        
        Returns:
            List[str]: Enhanced flavor preferences
        """
        enhanced_flavors = flavor_preferences.copy()
        
        # Add mood-based flavors if applicable
        if user_mood and user_mood.lower() in self.mood_flavor_map:
            mood_flavors = self.mood_flavor_map[user_mood.lower()]
            
            # Prioritize explicit preferences, but add mood flavors if they don't conflict
            for flavor in mood_flavors:
                # Check for contradictory flavors
                if flavor == "bold" and "smooth" in enhanced_flavors:
                    continue
                if flavor == "smooth" and "bold" in enhanced_flavors:
                    continue
                
                # Add non-contradictory mood flavors
                if flavor not in enhanced_flavors:
                    enhanced_flavors.append(flavor)
        
        # Remove duplicates while preserving order
        unique_flavors = []
        for flavor in enhanced_flavors:
            if flavor not in unique_flavors:
                unique_flavors.append(flavor)
        
        return unique_flavors
    
    def _get_default_flavors(self, coffee_type: str) -> List[str]:
        """
        Get default flavor preferences based on coffee type.
        """
        # Default flavor profiles by coffee type
        default_flavors = {
            'espresso': ['bold', 'chocolatey'],
            'cappuccino': ['balanced', 'chocolatey'],
            'latte': ['smooth', 'sweet'],
            'americano': ['balanced', 'smooth'],
            'pour-over': ['fruity', 'floral'],
            'french-press': ['bold', 'earthy'],
            'cold-brew': ['smooth', 'chocolatey'],
            'drip': ['balanced', 'nutty'],
            'macchiato': ['bold', 'intense'],
            'flat-white': ['smooth', 'creamy'],
            'mocha': ['chocolatey', 'sweet']
        }
        
        return default_flavors.get(coffee_type, ['balanced'])
    
    def _adjust_for_roast_preference(
        self, 
        selected_beans: List[Dict[str, Any]], 
        roast_preference: str
    ) -> List[Dict[str, Any]]:
        """
        Adjust selected beans based on roast preference.
        
        Args:
            selected_beans (List[Dict]): Selected beans
            roast_preference (str): Preferred roast level
        
        Returns:
            List[Dict]: Adjusted selected beans
        """
        adjusted_beans = []
        
        for bean in selected_beans:
            # Create a copy of the bean to modify
            adjusted_bean = bean.copy()
            
            # Adjust roast level if it doesn't match preference
            if bean.get('roast', '').lower() != roast_preference.lower():
                adjusted_bean['roast'] = roast_preference.capitalize()
                
                # Adjust flavor notes based on roast change
                if roast_preference.lower() == 'light':
                    adjusted_bean['notes'] = self._adjust_notes_for_light_roast(bean.get('notes', ''))
                elif roast_preference.lower() == 'dark':
                    adjusted_bean['notes'] = self._adjust_notes_for_dark_roast(bean.get('notes', ''))
            
            # Ensure grind size is constant
            adjusted_bean['grind_size'] = 'constant'
            
            adjusted_beans.append(adjusted_bean)
        
        return adjusted_beans
    
    def _adjust_notes_for_light_roast(self, notes: str) -> str:
        """
        Adjust flavor notes for light roast.
        
        Args:
            notes (str): Original flavor notes
        
        Returns:
            str: Adjusted flavor notes for light roast
        """
        # Split the notes into individual flavors
        flavors = [f.strip() for f in notes.split(',')]
        
        # Replace darker notes with lighter ones
        flavor_map = {
            'chocolatey': 'bright',
            'bold': 'lively',
            'earthy': 'floral',
            'caramel': 'citrusy',
            'nutty': 'fruity'
        }
        
        adjusted_flavors = []
        for flavor in flavors:
            adjusted = False
            for dark, light in flavor_map.items():
                if dark in flavor.lower():
                    adjusted_flavors.append(light)
                    adjusted = True
                    break
            if not adjusted:
                adjusted_flavors.append(flavor)
        
        # Add bright or fruity if not already present
        if 'bright' not in adjusted_flavors and 'fruity' not in adjusted_flavors:
            adjusted_flavors.insert(0, 'bright')
        
        return ', '.join(adjusted_flavors[:3])  # Limit to 3 notes
    
    def _adjust_notes_for_dark_roast(self, notes: str) -> str:
        """
        Adjust flavor notes for dark roast.
        
        Args:
            notes (str): Original flavor notes
        
        Returns:
            str: Adjusted flavor notes for dark roast
        """
        # Split the notes into individual flavors
        flavors = [f.strip() for f in notes.split(',')]
        
        # Replace lighter notes with darker ones
        flavor_map = {
            'bright': 'bold',
            'fruity': 'chocolatey',
            'floral': 'earthy',
            'citrusy': 'caramel',
            'light': 'rich'
        }
        
        adjusted_flavors = []
        for flavor in flavors:
            adjusted = False
            for light, dark in flavor_map.items():
                if light in flavor.lower():
                    adjusted_flavors.append(dark)
                    adjusted = True
                    break
            if not adjusted:
                adjusted_flavors.append(flavor)
        
        # Add bold or chocolatey if not already present
        if 'bold' not in adjusted_flavors and 'chocolatey' not in adjusted_flavors:
            adjusted_flavors.insert(0, 'bold')
        
        return ', '.join(adjusted_flavors[:3])  # Limit to 3 notes
    
    def _suggest_mood_pairing(self, mood: str) -> Dict[str, str]:
        """
        Suggest food or activity pairings based on mood.
        
        Args:
            mood (str): User's current mood
        
        Returns:
            Dict: Suggested pairings and activities
        """
        mood_pairings = {
            "energetic": {
                "food_pairing": "Light pastry or energy bar",
                "activity": "Morning workout or productive work session"
            },
            "relaxed": {
                "food_pairing": "Chocolate croissant or light dessert",
                "activity": "Reading a book or gentle meditation"
            },
            "creative": {
                "food_pairing": "Fruit tart or light breakfast",
                "activity": "Writing, painting, or brainstorming"
            },
            "stressed": {
                "food_pairing": "Comforting sweet treat",
                "activity": "Deep breathing or short walk"
            },
            "morning": {
                "food_pairing": "Whole grain toast or fruit",
                "activity": "Planning your day ahead"
            },
            "afternoon": {
                "food_pairing": "Small cookie or pastry",
                "activity": "Short break to recharge"
            },
            "evening": {
                "food_pairing": "Small dessert",
                "activity": "Unwinding with a book or show"
            }
        }
        
        # Default pairing if mood not recognized
        return mood_pairings.get(mood.lower(), {
            "food_pairing": "Neutral snack",
            "activity": "Take a moment to relax"
        })
    
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
            List[Dict]: Top flavor profiles with recommended brewing approaches
        """
        # Get top coffees by region
        top_coffees = self.coffee_database.get_top_coffees_by_region(species, top_n)
        
        flavor_profiles = []
        for _, coffee in top_coffees.iterrows():
            # Extract the main flavor notes
            flavor_notes = "balanced"
            if 'flavor_tags' in coffee and coffee['flavor_tags']:
                # Use flavor tags if available
                if isinstance(coffee['flavor_tags'], list) and coffee['flavor_tags']:
                    flavor_notes = ", ".join(coffee['flavor_tags'][:3])
                else:
                    # Try to extract from Flavor column
                    flavor_notes = str(coffee['Flavor'])
            
            # Create a flavor profile recommendation
            flavor_profile = {
                "origin": f"{coffee['Country.of.Origin']} {coffee['Region']}",
                "flavor_notes": flavor_notes,
                "cup_points": coffee['Total.Cup.Points'],
                "recommended_brewing": self._get_brewing_recommendation(flavor_notes, coffee),
                "grind_size": "constant"  # Add constant grind size
            }
            
            flavor_profiles.append(flavor_profile)
        
        return flavor_profiles
    
    def _generate_brewing_instructions(
        self, 
        coffee_type: str, 
        flavor_notes: List[str],
        user_mood: Optional[str] = None
    ) -> str:
        """
        Generate detailed brewing instructions.
        """
        # Base instructions by coffee type
        base_instructions = {
            'espresso': "Pull an espresso shot using 9 bars of pressure. Aim for 25-30 seconds extraction.",
            'cappuccino': "Pull an espresso shot as base. Steam milk to 65°C with sufficient microfoam for texture.",
            'latte': "Extract espresso shot, then add steamed milk with minimal foam.",
            'americano': "Pull an espresso shot, then add hot water to reach desired strength.",
            'pour-over': "Use circular pouring motion, starting in center. Begin with 30-second bloom using twice the coffee weight in water.",
            'french-press': "Add coffee, then hot water. Stir gently, steep for 4 minutes, then press slowly.",
            'cold-brew': "Combine coffee and room temperature water. Steep for 12-24 hours in refrigerator, then filter.",
            'drip': "Add coffee to filter, ensure even grounds, and brew according to machine instructions."
        }
        
        # Start with base instructions for this coffee type
        instructions = base_instructions.get(coffee_type, "Brew according to your brewing device's standard instructions.")
        
        # Add flavor-specific tips
        primary_flavor = flavor_notes[0] if flavor_notes else "balanced"
        
        if primary_flavor == "smooth":
            instructions += " For a smoother cup, use slightly cooler water and ensure an even extraction."
        elif primary_flavor == "bold":
            instructions += " For bolder flavor, use a slightly higher coffee-to-water ratio."
        elif primary_flavor == "fruity":
            instructions += " To highlight fruity notes, use water just off boil and a slightly finer grind."
        elif primary_flavor == "chocolatey":
            instructions += " For enhanced chocolate notes, try a slightly longer extraction time."
        
        return instructions
    
    def _get_brewing_recommendation(
        self, 
        flavor_notes: str, 
        coffee_data
    ) -> Dict[str, Any]:
        """
        Get brewing recommendations based on flavor notes and coffee data.
        
        Args:
            flavor_notes (str): Flavor notes
            coffee_data: Coffee data
        
        Returns:
            Dict: Brewing recommendations
        """
        flavor_notes_lower = flavor_notes.lower()
        
        # Default recommendation
        recommendation = {
            "method": "pour_over",
            "temperature": 94,
            "notes": "Highlights delicate flavor nuances",
            "grind_size": "constant"  # Add constant grind size
        }
        
        # Adjust based on flavor profile
        if any(term in flavor_notes_lower for term in ['fruity', 'floral', 'bright', 'citrus']):
            recommendation.update({
                "method": "pour_over",
                "temperature": 96,
                "notes": "Use gentle pour to accentuate bright, fruity notes"
            })
        elif any(term in flavor_notes_lower for term in ['chocolatey', 'cocoa', 'rich', 'caramel']):
            recommendation.update({
                "method": "french_press",
                "temperature": 92,
                "notes": "Full immersion to develop rich chocolate tones"
            })
        elif any(term in flavor_notes_lower for term in ['nutty', 'almond', 'hazelnut']):
            recommendation.update({
                "method": "pour_over",
                "temperature": 93,
                "notes": "Medium extraction to balance nutty character"
            })
        elif any(term in flavor_notes_lower for term in ['bold', 'earthy', 'spicy']):
            recommendation.update({
                "method": "espresso",
                "temperature": 91,
                "notes": "Pressure extraction brings out rich character"
            })
        
        # Adjust for origin
        try:
            origin = str(coffee_data['Country.of.Origin']).lower()
            if 'ethiopia' in origin:
                if 'method' not in recommendation or recommendation['method'] != 'espresso':
                    recommendation["method"] = "pour_over"
                    recommendation["notes"] = "Pour over brings out Ethiopian florals and fruits"
            elif 'colombia' in origin:
                recommendation["notes"] = f"Excellent for {recommendation['method']} with balanced profile"
            elif 'brazil' in origin and recommendation['method'] == 'pour_over':
                recommendation["method"] = "espresso"
                recommendation["notes"] = "Brazilian beans shine in espresso with chocolatey body"
        except (KeyError, AttributeError, TypeError):
            # If there's an error accessing origin, keep the default recommendation
            pass
        
        return recommendation

# Example usage demonstration
def main():
    # Initialize recommendation engine
    recommendation_engine = RecommendationEngine()
    
    # Test different recommendation scenarios
    scenarios = [
        {
            "flavor_preferences": ["fruity"],
            "coffee_type": "espresso",
            "user_mood": "creative"
        },
        {
            "flavor_preferences": ["chocolatey"],
            "coffee_type": "pour_over",
            "user_mood": "relaxed"
        },
        {
            "flavor_preferences": ["nutty", "balanced"],
            "coffee_type": "cappuccino",
            "user_mood": "morning"
        }
    ]
    
    for scenario in scenarios:
        print("\n--- Coffee Recommendation ---")
        recommendation = recommendation_engine.generate_recommendation(
            flavor_preferences=scenario.get("flavor_preferences"),
            coffee_type=scenario.get("coffee_type", "espresso"),
            user_mood=scenario.get("user_mood")
        )
        
        # Pretty print recommendation
        import json
        print(json.dumps(recommendation, indent=2))
    
    # Explore flavor profiles
    print("\n--- Flavor Profile Exploration ---")
    flavor_profiles = recommendation_engine.explore_flavor_profiles()
    import json
    print(json.dumps(flavor_profiles, indent=2))

if __name__ == "__main__":
    main()