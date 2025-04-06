from typing import List, Dict, Any, Union

class BrewingParameterCalculator:
    """
    Calculates precise brewing parameters based on coffee characteristics.
    """
    
    # Predefined brewing guidelines
    BREWING_GUIDELINES = {
        'espresso': {
            'pressure': 9.0,  # standard espresso pressure
            'typical_dose': 18.0,  # grams for double shot
            'extraction_time': (25, 30)  # seconds
        },
        'americano': {
            'base': 'espresso',
            'water_ratio': 2.0  # 2 parts water to 1 part espresso
        },
        'pour_over': {
            'pressure': 1.0,  # atmospheric pressure
            'typical_dose': 15.0,  # grams
            'water_ratio': 16.0  # grams of water per gram of coffee
        },
        'french_press': {
            'pressure': 1.0,
            'typical_dose': 15.0,
            'steep_time': (4, 5)  # minutes
        }
    }
    
    @classmethod
    def calculate_brewing_parameters(
        cls, 
        coffee_type: str, 
        beans: List[Dict[str, Any]], 
        total_dose: float = None
    ) -> Dict[str, Union[float, int, List[float]]]:
        """
        Calculate comprehensive brewing parameters.
        
        Args:
            coffee_type (str): Type of coffee brewing method
            beans (List[Dict]): Selected coffee beans
            total_dose (float, optional): Total coffee dose in grams
        
        Returns:
            Dict: Comprehensive brewing parameters
        """
        # Normalize coffee type
        coffee_type = coffee_type.lower().replace(' ', '_')
        
        # Get base guidelines
        base_params = cls.BREWING_GUIDELINES.get(coffee_type, {})
        
        # Determine dose
        if total_dose is None:
            total_dose = base_params.get('typical_dose', 18.0)
        
        # Calculate parameters
        params = {
            'coffee_type': coffee_type,
            'total_dose_g': total_dose,
            'bean_details': beans
        }
        
        # Add method-specific parameters
        if coffee_type == 'espresso':
            params.update({
                'pressure_bar': base_params.get('pressure', 9.0),
                'extraction_time_sec': base_params.get('extraction_time', (25, 30)),
                'ideal_grind_size': 'fine',
                'recommended_temp_c': cls._calculate_brew_temperature(beans)
            })
        
        elif coffee_type == 'americano':
            # Based on espresso with added water
            espresso_params = cls.calculate_brewing_parameters('espresso', beans, total_dose)
            params.update({
                'espresso_base': espresso_params,
                'water_ratio': base_params.get('water_ratio', 2.0),
                'total_drink_volume_ml': total_dose * (1 + base_params.get('water_ratio', 2.0))
            })
        
        elif coffee_type == 'pour_over':
            params.update({
                'pressure_bar': base_params.get('pressure', 1.0),
                'water_ratio': base_params.get('water_ratio', 16.0),
                'total_water_ml': total_dose * base_params.get('water_ratio', 16.0),
                'recommended_temp_c': cls._calculate_brew_temperature(beans),
                'pour_technique': cls._recommend_pour_over_technique(beans)
            })
        
        elif coffee_type == 'french_press':
            params.update({
                'pressure_bar': base_params.get('pressure', 1.0),
                'steep_time_min': base_params.get('steep_time', (4, 5)),
                'grind_size': 'coarse',
                'recommended_temp_c': cls._calculate_brew_temperature(beans)
            })
        
        return params
    
    @staticmethod
    def _calculate_brew_temperature(beans: List[Dict[str, Any]]) -> float:
        """
        Calculate optimal brewing temperature based on bean characteristics.
        
        Args:
            beans (List[Dict]): Selected coffee beans
        
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
        roast_levels = [bean.get('roast', 'Medium') for bean in beans]
        
        # Determine temperature based on roast levels
        if "Light" in roast_levels:
            base_range = TEMP_RANGES["Light"]
        elif "Dark" in roast_levels:
            base_range = TEMP_RANGES["Dark"]
        else:
            base_range = TEMP_RANGES["Medium"]
        
        # Fine-tune based on flavor notes
        flavor_temp_adjustments = {
            "fruity": 1,     # Slightly higher for bright flavors
            "floral": 1,     # Slightly higher for delicate notes
            "bold": -1,      # Slightly lower for bold flavors
            "chocolatey": -1 # Slightly lower for rich, deep flavors
        }
        
        temp_adjustment = 0
        for bean in beans:
            notes = bean.get('notes', '').lower()
            for flavor, adjustment in flavor_temp_adjustments.items():
                if flavor in notes:
                    temp_adjustment += adjustment
        
        # Calculate final temperature
        avg_temp = sum(base_range) / 2
        final_temp = avg_temp + max(-2, min(2, temp_adjustment))
        
        return round(final_temp, 1)
    
    @staticmethod
    def _recommend_pour_over_technique(beans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Recommend pour-over technique based on bean characteristics.
        
        Args:
            beans (List[Dict]): Selected coffee beans
        
        Returns:
            Dict: Recommended pouring technique
        """
        # Analyze bean characteristics
        technique = {
            "initial_bloom_time_sec": 30,  # standard bloom time
            "pour_style": "steady spiral"  # default technique
        }
        
        # Adjust technique based on bean notes
        for bean in beans:
            notes = bean.get('notes', '').lower()
            
            if "fruity" in notes:
                # Lighter roasts might benefit from gentler pouring
                technique["pour_style"] = "gentle circular"
            
            if "bold" in notes:
                # Bolder beans might need more aggressive extraction
                technique["initial_bloom_time_sec"] = 45
                technique["pour_style"] = "aggressive spiral"
        
        return technique

# Example usage demonstration
def main():
    # Example bean selections
    beans_fruity = [
        {
            "name": "Ethiopian Yirgacheffe",
            "roast": "Light",
            "notes": "fruity, floral"
        }
    ]
    
    beans_chocolatey = [
        {
            "name": "Brazilian Santos",
            "roast": "Medium",
            "notes": "chocolatey, nutty"
        }
    ]
    
    # Test different brewing methods
    brewing_methods = ['espresso', 'americano', 'pour_over', 'french_press']
    
    for method in brewing_methods:
        print(f"\n--- {method.upper()} Brewing Parameters ---")
        
        # Use fruity beans for some methods, chocolatey for others
        beans = beans_fruity if method in ['pour_over', 'espresso'] else beans_chocolatey
        
        # Calculate parameters
        params = BrewingParameterCalculator.calculate_brewing_parameters(
            method, beans
        )
        
        # Pretty print parameters
        import json
        print(json.dumps(params, indent=2))

if __name__ == "__main__":
    main()