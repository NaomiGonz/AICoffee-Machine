from typing import List, Dict, Any
from .coffee_database import CoffeeDatabase
import numpy as np
import re

class BeanSelector:
    """
    Manages bean selection logic for coffee brewing.
    """
    def __init__(self, coffee_database: CoffeeDatabase = None):
        """
        Initialize BeanSelector with a coffee database.
        
        Args:
            coffee_database (CoffeeDatabase, optional): Existing database instance
        """
        self.coffee_database = coffee_database or CoffeeDatabase()
        # Get flavor profile mapping
        self.flavor_profiles = self.coffee_database.get_flavor_mapping()
    
    def select_beans(
        self,
        coffee_type: str, 
        flavor_notes: List[str], 
        total_dose: float = 20.0,
        species: str = 'Arabica'
    ) -> List[Dict[str, Any]]:
        """
        Select and proportion beans for brewing using advanced matching.
        
        Args:
            coffee_type (str): Type of coffee being brewed
            flavor_notes (List[str]): Desired flavor characteristics
            total_dose (float): Total amount of coffee in grams
            species (str): Coffee species to select from
        
        Returns:
            List[Dict]: Selected and proportioned beans
        """
        # Make sure total_dose is not None and is a float
        if total_dose is None:
            total_dose = 20.0  # Default to 20g if total_dose is None
        
        # Handle string values for total_dose
        if isinstance(total_dose, str):
            # Check for size indicators
            if 'large' in total_dose.lower():
                total_dose = 24.0  # Large size - use more coffee
            elif 'small' in total_dose.lower():
                total_dose = 14.0  # Small size - use less coffee
            elif 'medium' in total_dose.lower():
                total_dose = 18.0  # Medium size
            else:
                # Try to extract numeric part if present
                try:
                    # Find any numbers in the string
                    import re
                    numbers = re.findall(r'\d+\.?\d*', total_dose)
                    if numbers:
                        total_dose = float(numbers[0])
                    else:
                        total_dose = 20.0  # Default if no numbers found
                except:
                    total_dose = 20.0  # Default to 20g if conversion fails
        
        # Convert numpy types to Python native types
        if hasattr(total_dose, 'item'):
            total_dose = total_dose.item()  # Convert numpy type to native Python type
        else:
            try:
                # Ensure total_dose is a float
                total_dose = float(total_dose)
            except (ValueError, TypeError):
                # If conversion fails, use default
                print(f"Could not convert {total_dose} to float, using default")
                total_dose = 20.0
        
        # Get recommended beans based on flavor preferences
        try:
            recommended_beans = self.coffee_database.get_bean_recommendations(
                flavor_preferences=flavor_notes,
                species=species,
                top_n=3  # Allow more options for blending
            )
        except Exception as e:
            print(f"Error getting bean recommendations: {e}")
            # Fallback to default bean with primary requested flavor
            return [{
                "name": "House Blend",
                "origin": "Mixed Origin",
                "roast": "Medium",
                "notes": self._get_primary_flavor(flavor_notes),
                "amount_g": total_dose if total_dose is not None else 20.0
            }]
        
        # If no beans found, return a default blend with requested flavor
        if recommended_beans.empty:
            return [{
                "name": "House Blend",
                "origin": "Mixed Origin",
                "roast": "Medium",
                "notes": self._get_primary_flavor(flavor_notes),
                "amount_g": total_dose if total_dose is not None else 20.0
            }]
        
        # Check if flavor_match_score column exists
        if 'flavor_match_score' not in recommended_beans.columns:
            # Add a default flavor match score if not present
            recommended_beans['flavor_match_score'] = 1.0
        
        # Prepare blended beans
        blended_beans = []
        
        # Determine number of beans to blend (max 2)
        num_beans = min(2, len(recommended_beans))
        
        for i in range(num_beans):
            bean = recommended_beans.iloc[i]
            
            # Calculate proportional dosing based on flavor match score
            total_match_score = recommended_beans['flavor_match_score'].sum()
            
            # Convert numpy types to Python native types
            if hasattr(total_match_score, 'item'):
                total_match_score = total_match_score.item()
            
            # Calculate bean_dose
            if total_match_score > 0:
                match_score = bean['flavor_match_score']
                if hasattr(match_score, 'item'):
                    match_score = match_score.item()
                bean_dose = (match_score / total_match_score) * total_dose
            else:
                bean_dose = total_dose / num_beans
            
            # Convert bean_dose to a standard Python float
            bean_dose = float(bean_dose)
            
            # Create a meaningful name if possible
            try:
                name = f"{bean['Country.of.Origin']} {bean['Region']}"
                name = name.strip()
                if not name:
                    name = f"Coffee #{i+1}"
            except:
                name = f"Coffee #{i+1}"
            
            # Try to get origin information
            try:
                origin = bean['Country.of.Origin']
                if isinstance(origin, float) or not origin:
                    origin = "Unknown"
            except:
                origin = "Unknown"
            
            # Try to get cup points for roast inference
            try:
                roast = self._infer_roast(bean['Total.Cup.Points'])
            except:
                roast = "Medium"  # Default roast
            
            # Get flavor notes from the bean data or generate based on requested flavors
            try:
                if 'notes' in bean and bean['notes'] and str(bean['notes']) != 'nan':
                    notes = str(bean['notes'])
                else:
                    # Use the requested flavor notes to create a description
                    notes = self._create_flavor_description(flavor_notes, origin)
            except Exception as e:
                print(f"Error getting notes: {e}")
                notes = self._get_primary_flavor(flavor_notes)
            
            blended_beans.append({
                "name": name,
                "origin": origin,
                "roast": roast,
                "notes": notes,
                "amount_g": round(bean_dose, 1)
            })
        
        return blended_beans
    
    def _get_primary_flavor(self, flavor_notes: List[str]) -> str:
        """
        Get the primary flavor from a list of flavor notes.
        
        Args:
            flavor_notes (List[str]): List of flavor notes
        
        Returns:
            str: Primary flavor description
        """
        if not flavor_notes:
            return "balanced"
        
        # Start with the first flavor note
        primary = flavor_notes[0]
        
        # Add a couple of related terms if available
        related_terms = []
        if primary in self.flavor_profiles:
            related_terms = self.flavor_profiles[primary][:2]  # Get up to 2 related terms
        
        if related_terms:
            return f"{primary}, {', '.join(related_terms[:2])}"
        else:
            return primary
    
    def _create_flavor_description(self, flavor_notes: List[str], origin: str) -> str:
        """
        Create a rich flavor description based on requested notes and coffee origin.
        
        Args:
            flavor_notes (List[str]): Requested flavor notes
            origin (str): Origin of the coffee
        
        Returns:
            str: Rich flavor description
        """
        if not flavor_notes:
            return "balanced, smooth"
        
        # Start with the primary requested flavor
        description = [flavor_notes[0]]
        
        # Add a secondary flavor from the list if available
        if len(flavor_notes) > 1:
            description.append(flavor_notes[1])
        
        # Add origin-specific flavor notes
        origin_lower = origin.lower()
        if 'ethiopia' in origin_lower:
            if 'fruity' in flavor_notes:
                description.append('berry')
            elif 'floral' in flavor_notes:
                description.append('jasmine')
        elif 'colombia' in origin_lower:
            if 'chocolatey' in flavor_notes:
                description.append('caramel')
            else:
                description.append('nutty')
        elif 'brazil' in origin_lower:
            if 'nutty' in flavor_notes:
                description.append('hazelnut')
            else:
                description.append('chocolatey')
        
        # Ensure uniqueness
        unique_descriptors = []
        for desc in description:
            if desc not in unique_descriptors:
                unique_descriptors.append(desc)
        
        return ", ".join(unique_descriptors)
    
    def _infer_roast(self, cup_points: float) -> str:
        """
        Infer roast level based on total cup points.
        
        Args:
            cup_points (float): Total cup points of the coffee
        
        Returns:
            str: Inferred roast level
        """
        # Convert numpy types to Python native types
        if hasattr(cup_points, 'item'):
            cup_points = cup_points.item()
        
        if cup_points >= 90:
            return "Light"
        elif cup_points >= 85:
            return "Medium"
        else:
            return "Dark"
    
    def suggest_brewing_notes(
        self, 
        selected_beans: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Provide brewing suggestions based on selected beans.
        
        Args:
            selected_beans (List[Dict]): Beans selected for brewing
        
        Returns:
            Dict: Brewing suggestions and notes
        """
        # Aggregate flavor notes
        all_notes = [bean.get('notes', '') for bean in selected_beans]
        
        # Determine primary flavor profile
        brewing_suggestions = {
            "flavor_profile": " & ".join(all_notes),
            "recommended_brewing_temp": self._suggest_brewing_temperature(selected_beans),
            "additional_notes": []
        }
        
        # Add specific brewing tips based on flavor notes
        for bean in selected_beans:
            notes_lower = bean.get('notes', '').lower()
            
            if any(term in notes_lower for term in ['fruity', 'berry', 'bright', 'citrus']):
                brewing_suggestions['additional_notes'].append(
                    f"The {bean['name']} will highlight bright, fruity notes at a slightly higher brewing temperature."
                )
            
            if any(term in notes_lower for term in ['chocolate', 'chocolatey', 'cocoa']):
                brewing_suggestions['additional_notes'].append(
                    f"The {bean['name']} will provide rich, chocolate notes with a smooth body."
                )
                
            if any(term in notes_lower for term in ['nutty', 'almond', 'hazelnut']):
                brewing_suggestions['additional_notes'].append(
                    f"The {bean['name']} offers a pleasant nutty character that pairs well with milk-based drinks."
                )
                
            if any(term in notes_lower for term in ['floral', 'jasmine', 'delicate']):
                brewing_suggestions['additional_notes'].append(
                    f"The {bean['name']} has delicate floral notes - brew with care to preserve these subtle flavors."
                )
        
        # Ensure uniqueness of notes
        unique_notes = []
        for note in brewing_suggestions['additional_notes']:
            if note not in unique_notes:
                unique_notes.append(note)
        
        brewing_suggestions['additional_notes'] = unique_notes
        
        return brewing_suggestions
    
    def _suggest_brewing_temperature(
        self, 
        selected_beans: List[Dict[str, Any]]
    ) -> float:
        """
        Suggest brewing temperature based on selected beans.
        
        Args:
            selected_beans (List[Dict]): Beans selected for brewing
        
        Returns:
            float: Recommended brewing temperature in Celsius
        """
        # Temperature ranges for different roast levels
        TEMP_RANGES = {
            "Light": (94, 96),
            "Medium": (92, 94),
            "Dark": (88, 91)
        }
        
        # Collect roast levels
        roast_levels = [bean.get('roast', 'Medium') for bean in selected_beans]
        
        # Determine temperature based on roast levels
        if "Light" in roast_levels:
            base_range = TEMP_RANGES["Light"]
        elif "Dark" in roast_levels:
            base_range = TEMP_RANGES["Dark"]
        else:
            base_range = TEMP_RANGES["Medium"]
        
        # Calculate average temperature
        avg_temp = sum(base_range) / 2
        
        # Fine-tune based on flavor notes
        flavor_temp_adjustments = {
            "fruity": 1.0,     # Slightly higher for bright flavors
            "bright": 1.0,     # Slightly higher for bright flavors
            "floral": 0.5,     # Slightly higher for delicate notes
            "bold": -0.5,      # Slightly lower for bold flavors
            "chocolatey": -0.5, # Slightly lower for rich, deep flavors
            "nutty": 0,        # Neutral adjustment for nutty
            "earthy": -1.0     # Lower for earthy flavors
        }
        
        temp_adjustment = 0
        for bean in selected_beans:
            notes = bean.get('notes', '').lower()
            for flavor, adjustment in flavor_temp_adjustments.items():
                if flavor in notes:
                    temp_adjustment += adjustment
        
        # Apply temperature adjustment with limits
        final_temp = avg_temp + max(-2, min(2, temp_adjustment))
        
        return round(final_temp, 1)

# Example usage demonstration
def main():
    # Initialize the database and bean selector
    coffee_db = CoffeeDatabase()
    bean_selector = BeanSelector(coffee_db)
    
    # Test scenarios
    test_scenarios = [
        {
            "coffee_type": "espresso",
            "flavor_notes": ["fruity"],
            "total_dose": 20.0
        },
        {
            "coffee_type": "cappuccino", 
            "flavor_notes": ["chocolatey", "nutty"],
            "total_dose": 20.0
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\nScenario: {scenario}")
        
        # Select beans
        selected_beans = bean_selector.select_beans(
            scenario["coffee_type"],
            scenario["flavor_notes"],
            scenario["total_dose"]
        )
        
        print("Selected Beans:")
        for bean in selected_beans:
            print(f"- {bean['name']} ({bean['roast']}): {bean['amount_g']}g - Notes: {bean['notes']}")
        
        # Get brewing suggestions
        brewing_suggestions = bean_selector.suggest_brewing_notes(selected_beans)
        print("\nBrewing Suggestions:")
        print(f"Flavor Profile: {brewing_suggestions['flavor_profile']}")
        print(f"Recommended Brewing Temp: {brewing_suggestions['recommended_brewing_temp']}°C")
        
        if brewing_suggestions['additional_notes']:
            print("Additional Notes:")
            for note in brewing_suggestions['additional_notes']:
                print(f"- {note}")

if __name__ == "__main__":
    main()