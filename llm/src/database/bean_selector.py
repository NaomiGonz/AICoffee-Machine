from typing import List, Dict, Any, Optional, Tuple
from .coffee_database import CoffeeDatabase
import re

class BeanSelector:
    """
    Enhanced bean selection logic for coffee brewing with improved fallback mechanisms.
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
        
        # Define comprehensive flavor categories with more synonyms
        self.expanded_flavor_categories = {
            'smooth': ['smooth', 'mild', 'mellow', 'velvety', 'creamy', 'balanced', 'silky', 'soft', 'gentle'],
            'fruity': ['fruity', 'berry', 'citrus', 'bright', 'apple', 'peach', 'cherry', 'tropical', 'vibrant', 'lively'],
            'chocolatey': ['chocolate', 'cocoa', 'rich', 'dark chocolate', 'mocha', 'fudge'],
            'nutty': ['nutty', 'almond', 'hazelnut', 'walnut', 'pecan', 'toasty', 'roasted nuts'],
            'floral': ['floral', 'jasmine', 'rose', 'lavender', 'delicate', 'aromatic', 'fragrant'],
            'bold': ['bold', 'strong', 'intense', 'full', 'robust', 'powerful', 'full-bodied'],
            'earthy': ['earthy', 'herbal', 'woody', 'robust', 'rustic', 'mushroom', 'forest'],
            'sweet': ['sweet', 'caramel', 'honey', 'molasses', 'sugar', 'syrupy', 'candied'],
            'spicy': ['spicy', 'cinnamon', 'clove', 'cardamom', 'peppery', 'warm spice'],
            'balanced': ['balanced', 'complex', 'round', 'well-rounded', 'harmonious', 'complete']
        }
        
        # Map coffee types to roast levels and flavor profiles
        self.coffee_type_profiles = {
            'espresso': {
                'preferred_roast': 'Medium-Dark',
                'preferred_flavors': ['bold', 'chocolatey', 'nutty'],
                'grind_size': 'fine'
            },
            'cappuccino': {
                'preferred_roast': 'Medium-Dark',
                'preferred_flavors': ['chocolatey', 'nutty', 'bold'],
                'grind_size': 'fine'
            },
            'latte': {
                'preferred_roast': 'Medium-Dark',
                'preferred_flavors': ['smooth', 'chocolatey', 'sweet'],
                'grind_size': 'fine'
            },
            'drip': {
                'preferred_roast': 'Medium',
                'preferred_flavors': ['balanced', 'sweet', 'nutty'],
                'grind_size': 'medium'
            },
            'pour-over': {
                'preferred_roast': 'Light-Medium',
                'preferred_flavors': ['fruity', 'floral', 'bright'],
                'grind_size': 'medium-fine'
            },
            'french-press': {
                'preferred_roast': 'Medium-Dark',
                'preferred_flavors': ['bold', 'earthy', 'chocolatey'],
                'grind_size': 'coarse'
            },
            'cold-brew': {
                'preferred_roast': 'Medium',
                'preferred_flavors': ['smooth', 'chocolatey', 'sweet'],
                'grind_size': 'coarse'
            },
            'americano': {
                'preferred_roast': 'Medium',
                'preferred_flavors': ['balanced', 'smooth', 'mild'],
                'grind_size': 'fine'
            }
        }
        
        # Define region-roast-flavor associations for fallback recommendations
        self.region_profiles = {
            'Ethiopia': {
                'typical_roast': 'Light',
                'flavor_notes': ['fruity', 'berry', 'floral', 'citrus'],
                'body': 'Medium'
            },
            'Kenya': {
                'typical_roast': 'Light-Medium',
                'flavor_notes': ['bright', 'citrus', 'berry', 'vibrant'],
                'body': 'Medium'
            },
            'Colombia': {
                'typical_roast': 'Medium',
                'flavor_notes': ['balanced', 'nutty', 'chocolatey', 'caramel'],
                'body': 'Medium-Full'
            },
            'Brazil': {
                'typical_roast': 'Medium',
                'flavor_notes': ['nutty', 'chocolatey', 'smooth', 'low-acid'],
                'body': 'Medium-Full'
            },
            'Guatemala': {
                'typical_roast': 'Medium',
                'flavor_notes': ['chocolatey', 'spicy', 'nutty', 'balanced'],
                'body': 'Medium-Full'
            },
            'Costa Rica': {
                'typical_roast': 'Medium',
                'flavor_notes': ['bright', 'clean', 'honey', 'balanced'],
                'body': 'Medium'
            },
            'Sumatra': {
                'typical_roast': 'Dark',
                'flavor_notes': ['earthy', 'spicy', 'herbal', 'bold'],
                'body': 'Full'
            },
            'Honduras': {
                'typical_roast': 'Medium',
                'flavor_notes': ['sweet', 'nutty', 'caramel', 'balanced'],
                'body': 'Medium'
            }
        }
        
        # Fallback bean definitions for different flavor categories
        self.fallback_beans = {
            'smooth': [
                {
                    'name': 'Brazilian Santos',
                    'origin': 'Brazil',
                    'roast': 'Medium',
                    'notes': 'smooth, nutty, low acidity',
                },
                {
                    'name': 'Colombia Supremo',
                    'origin': 'Colombia',
                    'roast': 'Medium',
                    'notes': 'smooth, balanced, mild sweetness',
                }
            ],
            'bold': [
                {
                    'name': 'Sumatra Mandheling',
                    'origin': 'Indonesia',
                    'roast': 'Dark',
                    'notes': 'bold, earthy, spicy',
                },
                {
                    'name': 'French Roast Blend',
                    'origin': 'Blend',
                    'roast': 'Dark',
                    'notes': 'bold, smoky, intense',
                }
            ],
            'fruity': [
                {
                    'name': 'Ethiopian Yirgacheffe',
                    'origin': 'Ethiopia',
                    'roast': 'Light',
                    'notes': 'fruity, floral, citrus',
                },
                {
                    'name': 'Kenya AA',
                    'origin': 'Kenya',
                    'roast': 'Light-Medium',
                    'notes': 'fruity, bright, berry',
                }
            ],
            'chocolatey': [
                {
                    'name': 'Guatemala Antigua',
                    'origin': 'Guatemala',
                    'roast': 'Medium-Dark',
                    'notes': 'chocolatey, spicy, balanced',
                },
                {
                    'name': 'Mocha Java Blend',
                    'origin': 'Blend',
                    'roast': 'Medium-Dark',
                    'notes': 'chocolatey, spicy, fruity',
                }
            ],
            'nutty': [
                {
                    'name': 'Brazilian Cerrado',
                    'origin': 'Brazil',
                    'roast': 'Medium',
                    'notes': 'nutty, chocolatey, smooth',
                },
                {
                    'name': 'Honduras SHG',
                    'origin': 'Honduras',
                    'roast': 'Medium',
                    'notes': 'nutty, sweet, caramel',
                }
            ],
            'balanced': [
                {
                    'name': 'House Blend',
                    'origin': 'Blend',
                    'roast': 'Medium',
                    'notes': 'balanced, smooth, versatile',
                },
                {
                    'name': 'Breakfast Blend',
                    'origin': 'Blend',
                    'roast': 'Medium',
                    'notes': 'balanced, bright, clean',
                }
            ]
        }
    
    def select_beans(
        self,
        coffee_type: str, 
        flavor_notes: List[str], 
        serving_size: float = 7.0,
        species: str = 'Arabica'
    ) -> List[Dict[str, Any]]:
        """
        Select and proportion beans for brewing using advanced matching with reliable fallbacks.
        
        Args:
            coffee_type (str): Type of coffee being brewed
            flavor_notes (List[str]): Desired flavor characteristics
            serving_size (float): Serving size in grams
            species (str): Coffee species to select from
        
        Returns:
            List[Dict]: Selected and proportioned beans
        """
        # Make sure serving_size is not None and is a float
        if serving_size is None:
            serving_size = 20.0  # Default to 20g if serving_size is None
        
        # Convert numpy types to Python native types
        if hasattr(serving_size, 'item'):
            serving_size = serving_size.item()
        else:
            try:
                # Ensure serving_size is a float
                serving_size = float(serving_size)
            except (ValueError, TypeError):
                # If conversion fails, use default
                print(f"Could not convert {serving_size} to float, using default")
                serving_size = 20.0
        
        # Normalize coffee type
        coffee_type = self._normalize_coffee_type(coffee_type)
                
        # Get available beans from inventory
        available_beans = self.coffee_database.get_bean_inventory()
        if len(available_beans) > 3:
            available_beans = available_beans[:3]
        
        # Expand and normalize flavor notes
        expanded_flavor_notes = self._expand_flavor_notes(flavor_notes)
        
        # Determine the primary flavor category
        primary_flavor = self._determine_primary_flavor(expanded_flavor_notes)
        
        # If no beans available or no good matches in inventory, use fallback beans
        if not available_beans:
            return self._get_fallback_beans(primary_flavor, coffee_type, serving_size)
        
        # Score each available bean based on flavor preferences
        scored_beans = []
        for bean in available_beans:
            score = self._calculate_bean_score(bean, expanded_flavor_notes, coffee_type)
            scored_beans.append({
                "bean": bean,
                "score": score
            })
        
        # Sort beans by score (descending)
        scored_beans.sort(key=lambda x: x["score"], reverse=True)
        
        # Check if the best bean has a good score (>= 5.0)
        if not scored_beans or scored_beans[0]["score"] < 5.0:
            # If no good matches in inventory, use fallback beans
            return self._get_fallback_beans(primary_flavor, coffee_type, serving_size)
        
        # Calculate proportions based on scores
        total_score = sum(item["score"] for item in scored_beans)
        
        if total_score == 0:
            # If no good matches, use equal proportions
            proportions = [1.0 / len(scored_beans) for _ in scored_beans]
        else:
            # Calculate weighted proportions
            proportions = [item["score"] / total_score for item in scored_beans]
        
        # Assign gram amounts based on proportions
        blended_beans = []
        for i, item in enumerate(scored_beans):
            bean = item["bean"].copy()  # Create a copy to avoid modifying original
            bean["amount_g"] = round(proportions[i] * serving_size, 1)
            
            # Skip beans with very small amounts (less than 0.5g)
            if bean["amount_g"] >= 0.5:
                # Add grind size based on coffee type
                bean["grind_size"] = self._get_grind_size(coffee_type)
                blended_beans.append(bean)
        
        # Adjust amounts to ensure sum equals serving_size
        if blended_beans:
            current_total = sum(bean["amount_g"] for bean in blended_beans)
            if abs(current_total - serving_size) > 0.1:  # If there's a significant difference
                # Apply correction to the bean with the largest amount
                largest_bean = max(blended_beans, key=lambda x: x["amount_g"])
                largest_bean["amount_g"] += (serving_size - current_total)
                largest_bean["amount_g"] = round(largest_bean["amount_g"], 1)  # Round to one decimal
        
        return blended_beans
    
    def _get_fallback_beans(
        self, 
        primary_flavor: str, 
        coffee_type: str, 
        serving_size: float
    ) -> List[Dict[str, Any]]:
        """
        Get fallback beans when inventory doesn't have good matches.
        
        Args:
            primary_flavor (str): Primary flavor category
            coffee_type (str): Type of coffee
            serving_size (float): Serving size in grams
            
        Returns:
            List[Dict]: Fallback beans with appropriate proportions
        """
        # Determine appropriate fallback beans based on primary flavor
        if primary_flavor in self.fallback_beans:
            beans = self.fallback_beans[primary_flavor]
        else:
            # Default to balanced if no specific flavor category
            beans = self.fallback_beans['balanced']
        
        # Make a copy to avoid modifying originals
        result_beans = []
        for bean in beans[:1]:  # Use only the first bean for simplicity
            bean_copy = bean.copy()
            bean_copy["amount_g"] = serving_size
            bean_copy["grind_size"] = self._get_grind_size(coffee_type)
            result_beans.append(bean_copy)
        
        return result_beans
    
    def _normalize_coffee_type(self, coffee_type: str) -> str:
        """
        Normalize coffee type to standard format.
        
        Args:
            coffee_type (str): Raw coffee type
            
        Returns:
            str: Normalized coffee type
        """
        if not coffee_type:
            return 'espresso'
        
        coffee_type = coffee_type.lower().strip()
        
        # Handle alternative names
        mapping = {
            'americano': 'americano',
            'filter': 'drip',
            'filter coffee': 'drip',
            'pour over': 'pour-over',
            'pourover': 'pour-over',
            'french press': 'french-press',
            'cold brew': 'cold-brew',
            'iced coffee': 'cold-brew',
            'cappucino': 'cappuccino',
            'machiato': 'macchiato',
            'expresso': 'espresso'  # Common misspelling
        }
        
        # Check direct match or mapped value
        return mapping.get(coffee_type, coffee_type)
    
    def _expand_flavor_notes(self, flavor_notes: List[str]) -> List[str]:
        """
        Expand flavor notes with related terms.
        
        Args:
            flavor_notes (List[str]): Original flavor notes
            
        Returns:
            List[str]: Expanded flavor notes
        """
        if not flavor_notes:
            return ['balanced']
        
        expanded = []
        for note in flavor_notes:
            note_lower = note.lower()
            expanded.append(note_lower)
            
            # Check if this note is in our expanded categories
            for category, terms in self.expanded_flavor_categories.items():
                if note_lower == category or note_lower in terms:
                    # Add the category and a couple of terms if not already included
                    if category not in expanded:
                        expanded.append(category)
                    
                    # Add a couple of related terms that aren't already in the list
                    for term in terms[:3]:  # Limit to first 3 related terms
                        if term not in expanded:
                            expanded.append(term)
        
        return expanded
    
    def _determine_primary_flavor(self, flavor_notes: List[str]) -> str:
        """
        Determine the primary flavor category from a list of flavor notes.
        
        Args:
            flavor_notes (List[str]): List of flavor notes
            
        Returns:
            str: Primary flavor category
        """
        if not flavor_notes:
            return 'balanced'
        
        # Count occurrences of each flavor category
        category_counts = {}
        for category in self.expanded_flavor_categories:
            category_counts[category] = 0
        
        # Check each flavor note
        for note in flavor_notes:
            note_lower = note.lower()
            
            # Direct category match
            if note_lower in category_counts:
                category_counts[note_lower] += 2  # Double weight for direct match
            
            # Check against expanded categories
            for category, terms in self.expanded_flavor_categories.items():
                if note_lower in terms:
                    category_counts[category] += 1
        
        # Find category with highest count
        max_count = 0
        primary_flavor = 'balanced'  # Default
        
        for category, count in category_counts.items():
            if count > max_count:
                max_count = count
                primary_flavor = category
        
        return primary_flavor
    
    def _calculate_bean_score(
        self, 
        bean: Dict[str, Any], 
        flavor_notes: List[str],
        coffee_type: str
    ) -> float:
        """
        Calculate a match score between a bean and desired flavor preferences.
        
        Args:
            bean (Dict): Bean details
            flavor_notes (List[str]): Desired flavor characteristics
            coffee_type (str): Type of coffee
            
        Returns:
            float: Match score (0.0 to 10.0)
        """
        # Start with base score
        score = 2.0  # Base score slightly higher than before
        
        # Extract bean flavor notes
        bean_notes = bean.get("notes", "").lower()
        bean_roast = bean.get("roast", "Medium")
        bean_origin = bean.get("origin", "")
        
        # Check direct matches in flavor notes
        for flavor in flavor_notes:
            flavor_lower = flavor.lower()
            if flavor_lower in bean_notes:
                score += 2.0
        
        # Consider coffee type preferences
        if coffee_type in self.coffee_type_profiles:
            profile = self.coffee_type_profiles[coffee_type]
            
            # Check if bean roast matches preferred roast for this coffee type
            preferred_roast = profile.get('preferred_roast', 'Medium')
            if self._roasts_are_compatible(bean_roast, preferred_roast):
                score += 1.5
            
            # Check if bean flavors match preferred flavors for this coffee type
            preferred_flavors = profile.get('preferred_flavors', [])
            for flavor in preferred_flavors:
                if flavor in bean_notes:
                    score += 1.0
        
        # Check region profiles
        for region, profile in self.region_profiles.items():
            if region.lower() in bean_origin.lower():
                # Region flavor notes match requested flavors
                for note in profile['flavor_notes']:
                    if note in flavor_notes:
                        score += 1.5
                        break
                
                # Region's typical roast matches coffee type's preferred roast
                if coffee_type in self.coffee_type_profiles:
                    coffee_profile = self.coffee_type_profiles[coffee_type]
                    preferred_roast = coffee_profile.get('preferred_roast', 'Medium')
                    if self._roasts_are_compatible(profile['typical_roast'], preferred_roast):
                        score += 1.0
        
        # Normalize score to a maximum of 10
        return min(10.0, score)
    
    def _roasts_are_compatible(self, roast1: str, roast2: str) -> bool:
        """
        Check if two roast levels are compatible.
        
        Args:
            roast1 (str): First roast level
            roast2 (str): Second roast level
            
        Returns:
            bool: True if roasts are compatible
        """
        # Normalize roast names
        roast1 = roast1.lower()
        roast2 = roast2.lower()
        
        # Exact match
        if roast1 == roast2:
            return True
        
        # Group roasts by category
        light_roasts = ['light', 'light-medium', 'blonde']
        medium_roasts = ['medium', 'medium-light', 'city']
        dark_roasts = ['medium-dark', 'dark', 'french', 'italian', 'espresso']
        
        # Check if roasts are in the same category
        for category in [light_roasts, medium_roasts, dark_roasts]:
            if any(r in roast1 for r in category) and any(r in roast2 for r in category):
                return True
        
        # Check for adjacent categories (medium is compatible with light and dark)
        if any(r in roast1 for r in medium_roasts) or any(r in roast2 for r in medium_roasts):
            return True
        
        return False
    
    def _get_grind_size(self, coffee_type: str) -> str:
        """
        Get appropriate grind size for coffee type.
        
        Args:
            coffee_type (str): Type of coffee
            
        Returns:
            str: Recommended grind size
        """
        if coffee_type in self.coffee_type_profiles:
            return self.coffee_type_profiles[coffee_type].get('grind_size', 'medium')
        
        # Default grind sizes for common types
        grind_mapping = {
            'espresso': 'fine',
            'cappuccino': 'fine',
            'latte': 'fine',
            'americano': 'fine',
            'drip': 'medium',
            'pour-over': 'medium-fine',
            'french-press': 'coarse',
            'cold-brew': 'coarse'
        }
        
        return grind_mapping.get(coffee_type, 'medium')  # Default to medium
    
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
    
    def suggest_brewing_notes(
        self, 
        selected_beans: List[Dict[str, Any]],
        coffee_type: str = 'espresso'
    ) -> Dict[str, Any]:
        """
        Provide brewing suggestions based on selected beans.
        
        Args:
            selected_beans (List[Dict]): Beans selected for brewing
            coffee_type (str): Type of coffee
        
        Returns:
            Dict: Brewing suggestions and notes
        """
        if not selected_beans:
            return {
                "flavor_profile": "balanced",
                "recommended_brewing_temp": 93.0,
                "grind_size": self._get_grind_size(coffee_type),
                "additional_notes": []
            }
        
        # Normalize coffee type
        coffee_type = self._normalize_coffee_type(coffee_type)
        
        # Determine primary flavor profile from beans
        all_notes = []
        for bean in selected_beans:
            notes = bean.get('notes', '')
            all_notes.extend([n.strip() for n in notes.split(',')])
        
        # Remove duplicates and get a clean list of flavor notes
        unique_notes = []
        for note in all_notes:
            note_lower = note.lower()
            if note_lower and note_lower not in unique_notes:
                unique_notes.append(note_lower)
        
        # Generate a flavor profile string
        flavor_profile = " & ".join(unique_notes[:4])  # Limit to 4 notes for readability
        
        brewing_suggestions = {
            "flavor_profile": flavor_profile,
            "recommended_brewing_temp": self._suggest_brewing_temperature(selected_beans, coffee_type),
            "grind_size": self._get_grind_size(coffee_type),
            "additional_notes": []
        }
        
        # Add specific brewing tips based on flavor notes and coffee type
        brewing_suggestions['additional_notes'] = self._generate_brewing_notes(selected_beans, coffee_type)
        
        return brewing_suggestions
    
    def _suggest_brewing_temperature(
        self, 
        selected_beans: List[Dict[str, Any]],
        coffee_type: str
    ) -> float:
        """
        Suggest brewing temperature based on selected beans and coffee type.
        
        Args:
            selected_beans (List[Dict]): Beans selected for brewing
            coffee_type (str): Type of coffee
        
        Returns:
            float: Recommended brewing temperature in Celsius
        """
        # Base temperature by coffee type
        base_temps = {
            'espresso': 93.0,
            'cappuccino': 93.0,
            'latte': 93.0,
            'americano': 93.0,
            'drip': 93.0,
            'pour-over': 94.0,
            'french-press': 95.0,
            'cold-brew': 20.0  # Room temperature
        }
        
        # Start with base temperature for this coffee type
        base_temp = base_temps.get(coffee_type, 93.0)
        
        # Temperature ranges for different roast levels
        roast_temp_adjustments = {
            "Light": 1.0,      # Higher temp for light roasts
            "Light-Medium": 0.5,
            "Medium": 0.0,     # No adjustment for medium roasts
            "Medium-Dark": -0.5,
            "Dark": -1.0       # Lower temp for dark roasts
        }
        
        # Collect roast levels
        roast_adjustment = 0.0
        for bean in selected_beans:
            roast = bean.get('roast', 'Medium')
            for roast_level, adjustment in roast_temp_adjustments.items():
                if roast_level.lower() in roast.lower():
                    roast_adjustment += adjustment
                    break
        
        # Average the adjustment if multiple beans
        if selected_beans:
            roast_adjustment /= len(selected_beans)
        
        # Flavor temp adjustments
        flavor_temp_adjustments = {
            "fruity": 0.5,     # Slightly higher for bright flavors
            "bright": 0.5,     # Slightly higher for bright flavors
            "floral": 0.5,     # Slightly higher for delicate notes
            "bold": -0.5,      # Slightly lower for bold flavors
            "chocolatey": -0.5, # Slightly lower for rich, deep flavors
            "nutty": 0,        # Neutral adjustment for nutty
            "earthy": -0.5     # Lower for earthy flavors
        }
        
        # Calculate flavor adjustment
        flavor_adjustment = 0.0
        for bean in selected_beans:
            notes = bean.get('notes', '').lower()
            for flavor, adjustment in flavor_temp_adjustments.items():
                if flavor in notes:
                    flavor_adjustment += adjustment
        
        # Average the adjustment if multiple beans
        if selected_beans:
            flavor_adjustment /= len(selected_beans)
        
        # Apply temperature adjustments with limits to base temperature
        final_temp = base_temp + roast_adjustment + flavor_adjustment
        
        # Ensure temperature stays in reasonable range
        final_temp = max(88.0, min(96.0, final_temp))
        
        # Special case for cold brew
        if coffee_type == 'cold-brew':
            final_temp = 20.0  # Always use room temperature for cold brew
        
        return round(final_temp, 1)
    
    def _generate_brewing_notes(
        self, 
        selected_beans: List[Dict[str, Any]],
        coffee_type: str
    ) -> List[str]:
        """
        Generate brewing notes based on beans and coffee type.
        
        Args:
            selected_beans (List[Dict]): Selected beans
            coffee_type (str): Type of coffee
            
        Returns:
            List[str]: Brewing notes
        """
        notes = []
        
        # Add coffee-type specific notes
        type_notes = {
            'espresso': "For best results, aim for 25-30 seconds extraction time.",
            'cappuccino': "Steam milk to 65°C for optimal texture and sweetness.",
            'latte': "Pour steamed milk slowly to create a smooth, velvety texture.",
            'pour-over': "Start with a 30-second bloom using twice the coffee weight in water.",
            'french-press': "After 4 minutes, press slowly and decant completely to avoid over-extraction.",
            'cold-brew': "Steep for 12-24 hours in the refrigerator for best results."
        }
        
        if coffee_type in type_notes:
            notes.append(type_notes[coffee_type])
        
        # Add notes for specific flavor profiles
        flavor_categories = set()
        for bean in selected_beans:
            bean_notes = bean.get('notes', '').lower()
            
            # Check which flavor categories this bean falls into
            for category, terms in self.expanded_flavor_categories.items():
                if category in bean_notes or any(term in bean_notes for term in terms):
                    flavor_categories.add(category)
        
        # Add flavor-specific brewing tips
        flavor_tips = {
            'fruity': "To enhance the fruity notes, use water just off boil and a slightly finer grind.",
            'floral': "Preserve delicate floral notes by using a slightly lower brew temperature.",
            'chocolatey': "Bring out chocolate notes with a slightly higher brew temperature and longer extraction.",
            'nutty': "To highlight nutty flavors, try a slightly longer brew time with a medium-coarse grind.",
            'bold': "For a bolder cup, use a slightly higher coffee-to-water ratio and darker roasted beans.",
            'smooth': "For extra smoothness, use slightly cooler water and a medium grind size.",
            'balanced': "To maintain balance, follow the standard brewing parameters for your brewing method."
        }
        
        # Add applicable flavor tips
        for category in flavor_categories:
            if category in flavor_tips and flavor_tips[category] not in notes:
                notes.append(flavor_tips[category])
        
        # Add bean-specific notes
        for bean in selected_beans:
            bean_name = bean.get('name', '')
            bean_notes = bean.get('notes', '').lower()
            bean_origin = bean.get('origin', '')
            
            # Add origin-specific notes
            if 'ethiopia' in bean_origin.lower():
                if 'fruity' in bean_notes or 'berry' in bean_notes:
                    notes.append(f"{bean_name} will highlight bright berry notes.")
            elif 'colombia' in bean_origin.lower():
                if 'smooth' in bean_notes or 'balanced' in bean_notes:
                    notes.append(f"{bean_name} provides a smooth, balanced base for your coffee.")
            elif 'sumatra' in bean_origin.lower() or 'indonesia' in bean_origin.lower():
                if 'earthy' in bean_notes or 'spicy' in bean_notes:
                    notes.append(f"{bean_name} adds unique earthy, spicy character to your cup.")
        
        # Limit to most relevant 3 notes for readability
        return notes[:3]