from typing import List, Dict, Any, Optional
import numpy as np

class EnhancedBeanSelector:
    """
    Enhanced bean selection system that mixes beans with different gram amounts
    while maintaining a constant grind size and using only available beans.
    """
    
    def __init__(self, available_beans: List[Dict[str, Any]]):
        """
        Initialize the bean selector with available beans.
        
        Args:
            available_beans (List[Dict]): List of beans available to the user
                Each bean should have at least 'name', 'origin', 'roast', and 'notes' fields
        """
        # Store available beans (maximum 3)
        self.available_beans = available_beans[:3] if len(available_beans) > 3 else available_beans
        
        # Flavor profile mapping for matching
        self.flavor_profile_mapping = {
            'fruity': ['fruity', 'berry', 'citrus', 'bright', 'apple', 'peach', 'cherry', 'tropical'],
            'chocolatey': ['chocolate', 'cocoa', 'rich', 'dark chocolate', 'mocha'],
            'nutty': ['nutty', 'almond', 'hazelnut', 'walnut', 'pecan'],
            'floral': ['floral', 'jasmine', 'rose', 'lavender', 'delicate'],
            'bold': ['bold', 'strong', 'intense', 'full'],
            'smooth': ['smooth', 'mild', 'velvety', 'creamy'],
            'earthy': ['earthy', 'herbal', 'woody', 'robust'],
            'sweet': ['sweet', 'caramel', 'honey', 'molasses', 'sugar'],
            'spicy': ['spicy', 'cinnamon', 'clove', 'cardamom'],
            'balanced': ['balanced', 'complex', 'round']
        }
        
        # Constant grind size - this doesn't change
        self.grind_size = "constant"
    
    def select_beans_for_brewing(
        self, 
        flavor_preferences: List[str], 
        coffee_type: str = 'espresso',
        total_dose: float = 18.0
    ) -> Dict[str, Any]:
        """
        Select and proportion beans for brewing based on desired flavor profile.
        
        Args:
            flavor_preferences (List[str]): Desired flavor characteristics
            coffee_type (str): Type of coffee being brewed
            total_dose (float): Total amount of coffee in grams
        
        Returns:
            Dict: Selected beans with proportions and brewing recommendations
        """
        # Check if we have available beans
        if not self.available_beans:
            return {
                "beans": [],
                "grind_size": self.grind_size,
                "error": "No beans available for selection"
            }
        
        # Score each available bean based on flavor preferences
        scored_beans = []
        for bean in self.available_beans:
            score = self._calculate_flavor_match_score(bean, flavor_preferences)
            scored_beans.append({
                "bean": bean,
                "score": score
            })
        
        # Sort beans by score (descending)
        scored_beans.sort(key=lambda x: x["score"], reverse=True)
        
        # Calculate proportions based on scores
        selected_beans = []
        total_score = sum(item["score"] for item in scored_beans)
        
        if total_score == 0:
            # If no good matches, use equal proportions
            proportions = [1.0 / len(scored_beans) for _ in scored_beans]
        else:
            # Calculate weighted proportions
            proportions = [item["score"] / total_score for item in scored_beans]
        
        # Assign gram amounts based on proportions
        for i, item in enumerate(scored_beans):
            bean = item["bean"].copy()  # Create a copy to avoid modifying original
            bean["amount_g"] = round(proportions[i] * total_dose, 1)
            
            # Skip beans with very small amounts (less than 0.5g)
            if bean["amount_g"] >= 0.5:
                selected_beans.append(bean)
        
        # Adjust amounts to ensure sum equals total_dose
        if selected_beans:
            current_total = sum(bean["amount_g"] for bean in selected_beans)
            if abs(current_total - total_dose) > 0.1:  # If there's a significant difference
                # Apply correction to the bean with the largest amount
                largest_bean = max(selected_beans, key=lambda x: x["amount_g"])
                largest_bean["amount_g"] += (total_dose - current_total)
                largest_bean["amount_g"] = round(largest_bean["amount_g"], 1)  # Round to one decimal
        
        # Create brewing parameters recommendation
        brewing_recommendations = self._generate_brewing_recommendations(
            selected_beans,
            coffee_type,
            flavor_preferences
        )
        
        return {
            "beans": selected_beans,
            "grind_size": self.grind_size,
            "total_dose_g": total_dose,
            "brewing_recommendations": brewing_recommendations
        }
    
    def _calculate_flavor_match_score(
        self, 
        bean: Dict[str, Any], 
        flavor_preferences: List[str]
    ) -> float:
        """
        Calculate a match score between a bean and desired flavor preferences.
        
        Args:
            bean (Dict): Bean details
            flavor_preferences (List[str]): Desired flavor characteristics
        
        Returns:
            float: Match score (0.0 to 10.0)
        """
        # Start with base score
        score = 1.0  # Ensure all beans get some score
        
        # Extract bean flavor notes
        bean_notes = bean.get("notes", "").lower()
        
        # Expand flavor preferences to include related terms
        expanded_preferences = self._expand_flavor_preferences(flavor_preferences)
        
        # Check direct matches
        for flavor in expanded_preferences:
            if flavor.lower() in bean_notes:
                score += 2.0
        
        # Check matches with expanded flavor profiles
        for category, terms in self.flavor_profile_mapping.items():
            if category.lower() in flavor_preferences:
                for term in terms:
                    if term.lower() in bean_notes:
                        score += 1.0
        
        # Consider roast level match for flavor profile
        roast_preferences = {
            'fruity': 'Light',
            'floral': 'Light',
            'bright': 'Light',
            'chocolatey': 'Medium',
            'nutty': 'Medium',
            'sweet': 'Medium',
            'bold': 'Dark',
            'earthy': 'Dark',
            'spicy': 'Dark'
        }
        
        for flavor, preferred_roast in roast_preferences.items():
            if flavor in flavor_preferences and bean.get('roast') == preferred_roast:
                score += 1.5
        
        # Normalize score to a maximum of 10
        return min(10.0, score)
    
    def _expand_flavor_preferences(self, flavor_preferences: List[str]) -> List[str]:
        """
        Expand flavor preferences to include related terms.
        
        Args:
            flavor_preferences (List[str]): Original flavor preferences
        
        Returns:
            List[str]: Expanded flavor preferences
        """
        expanded = []
        for pref in flavor_preferences:
            expanded.append(pref.lower())
            # Add related terms
            for profile, terms in self.flavor_profile_mapping.items():
                if pref.lower() in [profile.lower()] + [t.lower() for t in terms]:
                    expanded.extend([t.lower() for t in terms])
        
        # Remove duplicates while preserving order
        unique_expanded = []
        for flavor in expanded:
            if flavor not in unique_expanded:
                unique_expanded.append(flavor)
        
        return unique_expanded
    
    def _generate_brewing_recommendations(
        self, 
        selected_beans: List[Dict[str, Any]],
        coffee_type: str,
        flavor_preferences: List[str]
    ) -> Dict[str, Any]:
        """
        Generate brewing recommendations based on selected beans.
        
        Args:
            selected_beans (List[Dict]): Selected and proportioned beans
            coffee_type (str): Type of coffee being brewed
            flavor_preferences (List[str]): Desired flavor characteristics
        
        Returns:
            Dict: Brewing recommendations
        """
        # Determine recommended water temperature based on roast levels
        roast_temp_map = {
            'Light': (94, 96),
            'Medium': (92, 94),
            'Dark': (88, 91)
        }
        
        # Calculate weighted average temperature based on bean amounts
        if selected_beans:
            total_amount = sum(bean.get('amount_g', 0) for bean in selected_beans)
            
            if total_amount > 0:
                temp_sum = sum(
                    bean.get('amount_g', 0) * np.mean(roast_temp_map.get(bean.get('roast', 'Medium'), (92, 94)))
                    for bean in selected_beans
                )
                recommended_temp = round(temp_sum / total_amount, 1)
            else:
                recommended_temp = 92.0  # Default temperature
        else:
            recommended_temp = 92.0  # Default temperature
        
        # Adjust for specific flavor preferences
        flavor_temp_adjustment = 0
        
        if any(flavor in ['fruity', 'floral', 'bright'] for flavor in flavor_preferences):
            flavor_temp_adjustment += 1.0
        
        if any(flavor in ['chocolatey', 'nutty', 'bold'] for flavor in flavor_preferences):
            flavor_temp_adjustment -= 0.5
        
        recommended_temp += flavor_temp_adjustment
        
        # Coffee type specific parameters
        brew_params = {}
        
        if coffee_type == 'espresso':
            brew_params = {
                'water_temperature_c': recommended_temp,
                'water_pressure_bar': 9.0,
                'extraction_time_sec': (27, 32)
            }
        elif coffee_type == 'pour_over':
            brew_params = {
                'water_temperature_c': recommended_temp,
                'water_coffee_ratio': 16.0,  # 16:1 ratio
                'total_brew_time_sec': (180, 210)
            }
        elif coffee_type == 'french_press':
            brew_params = {
                'water_temperature_c': recommended_temp,
                'water_coffee_ratio': 15.0,
                'steep_time_min': (4, 5)
            }
        else:
            brew_params = {
                'water_temperature_c': recommended_temp,
                'water_coffee_ratio': 16.0
            }
        
        # Generate flavor profile description
        flavor_description = self._generate_flavor_profile(selected_beans, flavor_preferences)
        
        return {
            'brewing_parameters': brew_params,
            'flavor_profile': flavor_description,
            'grind_size': self.grind_size
        }
    
    def _generate_flavor_profile(
        self,
        selected_beans: List[Dict[str, Any]],
        flavor_preferences: List[str]
    ) -> str:
        """
        Generate a description of the expected flavor profile.
        
        Args:
            selected_beans (List[Dict]): Selected and proportioned beans
            flavor_preferences (List[str]): Desired flavor characteristics
        
        Returns:
            str: Flavor profile description
        """
        if not selected_beans:
            return "No beans selected"
        
        # Extract flavor notes from beans, weighted by their proportion
        flavors = []
        for bean in selected_beans:
            notes = bean.get('notes', '').lower()
            for flavor in self.flavor_profile_mapping:
                if flavor in notes or any(term in notes for term in self.flavor_profile_mapping[flavor]):
                    flavors.append(flavor)
        
        # Add requested flavors if not already present
        for pref in flavor_preferences:
            if pref not in flavors:
                flavors.append(pref)
        
        # Prioritize flavors
        prioritized = []
        for flavor in flavors:
            if flavor not in prioritized:
                prioritized.append(flavor)
        
        # Limit to top 3 flavors
        primary_flavors = prioritized[:3]
        
        # Create description
        if len(primary_flavors) >= 3:
            return f"A complex blend with {primary_flavors[0]}, {primary_flavors[1]}, and {primary_flavors[2]} notes"
        elif len(primary_flavors) == 2:
            return f"A balanced profile highlighting {primary_flavors[0]} and {primary_flavors[1]} flavors"
        elif len(primary_flavors) == 1:
            return f"A distinctive cup emphasizing {primary_flavors[0]} character"
        else:
            return "A balanced, smooth cup"


# Example usage
def test_bean_selector():
    # Sample available beans (maximum 3)
    available_beans = [
        {
            "name": "Ethiopian Yirgacheffe",
            "origin": "Ethiopia",
            "roast": "Light",
            "notes": "fruity, floral, citrus, bright"
        },
        {
            "name": "Colombian Supremo",
            "origin": "Colombia",
            "roast": "Medium",
            "notes": "chocolatey, nutty, balanced, caramel"
        },
        {
            "name": "Sumatra Mandheling",
            "origin": "Indonesia",
            "roast": "Dark",
            "notes": "earthy, spicy, bold, herbal"
        }
    ]
    
    # Initialize selector
    selector = EnhancedBeanSelector(available_beans)
    
    # Test with different flavor preferences
    test_cases = [
        {
            "flavors": ["fruity", "bright"],
            "coffee_type": "pour_over",
            "dose": 22.0
        },
        {
            "flavors": ["chocolatey", "balanced"],
            "coffee_type": "espresso",
            "dose": 18.0
        },
        {
            "flavors": ["bold", "earthy"],
            "coffee_type": "french_press",
            "dose": 30.0
        }
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {test['flavors']} for {test['coffee_type']}")
        result = selector.select_beans_for_brewing(
            test["flavors"],
            test["coffee_type"],
            test["dose"]
        )
        
        print(f"Selected Beans:")
        for bean in result["beans"]:
            print(f"  - {bean['name']} ({bean['roast']}): {bean['amount_g']}g")
        
        print(f"Grind Size: {result['grind_size']}")
        print(f"Brewing Parameters: {result['brewing_recommendations']['brewing_parameters']}")
        print(f"Flavor Profile: {result['brewing_recommendations']['flavor_profile']}")

if __name__ == "__main__":
    test_bean_selector()