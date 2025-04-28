from typing import List, Dict, Any, Optional

class BrewingParameterCalculator:
    """
    Enhanced calculator for optimal brewing parameters based on coffee type
    and bean characteristics.
    """
    
    @staticmethod
    def calculate_brewing_parameters(
        coffee_type: str,
        selected_beans: List[Dict[str, Any]],
        serving_size: float = 20.0
    ) -> Dict[str, Any]:
        """
        Calculate optimal brewing parameters for a specific coffee type and beans.
        
        Args:
            coffee_type (str): Type of coffee to brew
            selected_beans (List[Dict]): Selected beans with their characteristics
            serving_size (float): Serving size in grams
            
        Returns:
            Dict: Brewing parameters
        """
        # Baseline parameters by coffee type
        baseline_params = BrewingParameterCalculator._get_baseline_parameters(coffee_type)
        
        # Adapt parameters based on bean characteristics
        adjusted_params = BrewingParameterCalculator._adjust_for_beans(baseline_params, selected_beans)
        
        # Add coffee-to-water ratio and other calculated values
        final_params = BrewingParameterCalculator._calculate_brewing_ratios(
            adjusted_params, coffee_type, serving_size
        )
        
        return final_params
    
    @staticmethod
    def _get_baseline_parameters(coffee_type: str) -> Dict[str, Any]:
        """
        Get baseline brewing parameters for different coffee types.
        
        Args:
            coffee_type (str): Type of coffee
            
        Returns:
            Dict: Baseline brewing parameters
        """
        # Normalize coffee type
        normalized_type = coffee_type.lower().replace('_', '-')
        
        # Define baseline parameters for each coffee type
        baseline_params = {
            'espresso': {
                'recommended_temp_c': 93,
                'pressure_bar': 9.0,
                'extraction_time': '25-30',
                'ideal_grind_size': 'fine',
                'coffee_water_ratio': 1/2,  # 1g coffee to 2ml water
                'tds_target': '8-12%'  # Total Dissolved Solids target
            },
            'cappuccino': {
                'recommended_temp_c': 93,
                'pressure_bar': 9.0,
                'extraction_time': '25-30',
                'ideal_grind_size': 'fine',
                'coffee_water_ratio': 1/2,
                'milk_temp_c': 65,
                'milk_ratio': '1:1'  # Espresso to milk ratio
            },
            'latte': {
                'recommended_temp_c': 93,
                'pressure_bar': 9.0,
                'extraction_time': '25-30',
                'ideal_grind_size': 'fine',
                'coffee_water_ratio': 1/2,
                'milk_temp_c': 65,
                'milk_ratio': '1:3'  # Espresso to milk ratio
            },
            'americano': {
                'recommended_temp_c': 93,
                'pressure_bar': 9.0,
                'extraction_time': '25-30',
                'ideal_grind_size': 'fine',
                'coffee_water_ratio': 1/2,
                'dilution_ratio': '1:3'  # Espresso to water ratio
            },
            'pour-over': {
                'recommended_temp_c': 94,
                'extraction_time': '180-210',
                'ideal_grind_size': 'medium-fine',
                'coffee_water_ratio': 1/16,  # 1g coffee to 16ml water
                'bloom_time': 30,  # Bloom time in seconds
                'bloom_water_ratio': 2,  # Bloom water as multiple of coffee weight
                'pour_technique': 'concentric circles'
            },
            'drip': {
                'recommended_temp_c': 93,
                'extraction_time': '240-300',
                'ideal_grind_size': 'medium',
                'coffee_water_ratio': 1/17,  # 1g coffee to 17ml water
            },
            'french-press': {
                'recommended_temp_c': 95,
                'extraction_time': '240',
                'ideal_grind_size': 'coarse',
                'coffee_water_ratio': 1/15,  # 1g coffee to 15ml water
                'steep_time': 240  # Steep time in seconds
            },
            'cold-brew': {
                'recommended_temp_c': 20,  # Room temperature
                'extraction_time': '720-1440',  # 12-24 hours
                'ideal_grind_size': 'coarse',
                'coffee_water_ratio': 1/5,  # 1g coffee to 5ml water (stronger)
                'steep_time': 1080  # 18 hours in seconds (default)
            }
        }
        
        # Return baseline parameters for the requested coffee type, or default to espresso if not found
        return baseline_params.get(normalized_type, baseline_params['espresso'])
    
    @staticmethod
    def _adjust_for_beans(
        params: Dict[str, Any],
        selected_beans: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Adjust brewing parameters based on bean characteristics.
        
        Args:
            params (Dict): Baseline brewing parameters
            selected_beans (List[Dict]): Selected beans
            
        Returns:
            Dict: Adjusted brewing parameters
        """
        # If no beans provided, return unchanged parameters
        if not selected_beans:
            return params
        
        # Make a copy to avoid modifying the original
        adjusted = params.copy()
        
        # Collect bean characteristics
        bean_characteristics = {
            'light_roast_count': 0,
            'medium_roast_count': 0,
            'dark_roast_count': 0,
            'has_fruity': False,
            'has_floral': False,
            'has_chocolatey': False,
            'has_nutty': False,
            'has_earthy': False,
            'has_bold': False,
            'has_smooth': False
        }
        
        # Analyze beans
        for bean in selected_beans:
            # Check roast levels
            roast = bean.get('roast', '').lower()
            if 'light' in roast:
                bean_characteristics['light_roast_count'] += 1
            elif 'dark' in roast:
                bean_characteristics['dark_roast_count'] += 1
            else:  # Default to medium
                bean_characteristics['medium_roast_count'] += 1
                
            # Check flavor notes
            notes = bean.get('notes', '').lower()
            bean_characteristics['has_fruity'] |= any(f in notes for f in ['fruity', 'fruit', 'berry', 'citrus'])
            bean_characteristics['has_floral'] |= any(f in notes for f in ['floral', 'flower', 'jasmine', 'rose'])
            bean_characteristics['has_chocolatey'] |= any(f in notes for f in ['chocolate', 'cocoa', 'mocha'])
            bean_characteristics['has_nutty'] |= any(f in notes for f in ['nutty', 'nut', 'almond', 'hazelnut'])
            bean_characteristics['has_earthy'] |= any(f in notes for f in ['earthy', 'earth', 'woody'])
            bean_characteristics['has_bold'] |= any(f in notes for f in ['bold', 'strong', 'intense'])
            bean_characteristics['has_smooth'] |= any(f in notes for f in ['smooth', 'mild', 'balanced'])
        
        # Adjust temperature based on roast level
        if 'recommended_temp_c' in adjusted:
            if bean_characteristics['light_roast_count'] > 0:
                # Lighter roasts need higher temperature
                adjusted['recommended_temp_c'] += min(2, bean_characteristics['light_roast_count'])
            elif bean_characteristics['dark_roast_count'] > 0:
                # Darker roasts need lower temperature
                adjusted['recommended_temp_c'] -= min(2, bean_characteristics['dark_roast_count'])
        
        # Adjust extraction time based on flavor characteristics
        if 'extraction_time' in adjusted and '-' in adjusted['extraction_time']:
            min_time, max_time = map(int, adjusted['extraction_time'].split('-'))
            
            # Fruity/floral benefits from shorter extraction
            if bean_characteristics['has_fruity'] or bean_characteristics['has_floral']:
                min_time = max(min_time - 2, min_time * 0.9)
                max_time = max(max_time - 5, max_time * 0.9)
            
            # Chocolatey/earthy benefits from longer extraction
            if bean_characteristics['has_chocolatey'] or bean_characteristics['has_earthy']:
                min_time = min(min_time + 2, min_time * 1.1)
                max_time = min(max_time + 5, max_time * 1.1)
                
            # Update extraction time
            adjusted['extraction_time'] = f"{int(min_time)}-{int(max_time)}"
        
        # Adjust espresso pressure if applicable
        if 'pressure_bar' in adjusted:
            # Lower pressure for fruity/floral to reduce acidity
            if bean_characteristics['has_fruity'] or bean_characteristics['has_floral']:
                adjusted['pressure_bar'] = max(8.0, adjusted['pressure_bar'] - 0.5)
            
            # Higher pressure for bold/earthy to increase extraction
            if bean_characteristics['has_bold'] or bean_characteristics['has_earthy']:
                adjusted['pressure_bar'] = min(10.0, adjusted['pressure_bar'] + 0.5)
        
        # Fine-tune grind size adjustment based on flavor profile
        if 'ideal_grind_size' in adjusted:
            original_grind = adjusted['ideal_grind_size']
            
            # Convert grind size to numeric scale for adjustments
            grind_scale = {
                'extra-fine': 1,
                'fine': 2,
                'medium-fine': 3,
                'medium': 4,
                'medium-coarse': 5,
                'coarse': 6,
                'extra-coarse': 7
            }
            
            # Get numeric value of original grind
            if original_grind in grind_scale:
                grind_value = grind_scale[original_grind]
                
                # Adjust for flavor characteristics
                if bean_characteristics['has_smooth'] or bean_characteristics['has_chocolatey']:
                    # Go one step coarser for smooth/chocolatey
                    grind_value += 1
                elif bean_characteristics['has_fruity'] or bean_characteristics['has_floral']:
                    # Go one step finer for fruity/floral
                    grind_value -= 1
                
                # Ensure grind value stays in range
                grind_value = max(1, min(7, grind_value))
                
                # Convert back to text description
                reverse_scale = {v: k for k, v in grind_scale.items()}
                adjusted['ideal_grind_size'] = reverse_scale[grind_value]
        
        return adjusted
    
    @staticmethod
    def _calculate_brewing_ratios(
        params: Dict[str, Any],
        coffee_type: str,
        serving_size: float
    ) -> Dict[str, Any]:
        """
        Calculate water amounts and ratios based on coffee weight.
        
        Args:
            params (Dict): Brewing parameters
            coffee_type (str): Type of coffee
            serving_size (float): Serving size in grams
            
        Returns:
            Dict: Complete brewing parameters with calculated values
        """
        # Make a copy to avoid modifying the original
        final_params = params.copy()
        
        # Get coffee-to-water ratio
        ratio = params.get('coffee_water_ratio', 1/16)  # Default to 1:16
        
        # Calculate water amount in ml
        water_ml = serving_size / ratio
        final_params['water_ml'] = round(water_ml)
        
        # Add brewing instructions based on coffee type
        if coffee_type == 'espresso':
            final_params['brew_instructions'] = f"Grind {serving_size}g coffee {params['ideal_grind_size']}. Extract with {final_params['water_ml']}ml water at {params['recommended_temp_c']}°C for {params['extraction_time']} seconds."
        
        elif coffee_type == 'pour-over':
            bloom_water = serving_size * params.get('bloom_water_ratio', 2)
            final_params['bloom_water_ml'] = round(bloom_water)
            final_params['brew_instructions'] = f"Grind {serving_size}g coffee {params['ideal_grind_size']}. Bloom with {final_params['bloom_water_ml']}ml water for {params.get('bloom_time', 30)} seconds, then pour remaining {final_params['water_ml'] - final_params['bloom_water_ml']}ml in {params.get('pour_technique', 'spiral')} motion."
        
        elif coffee_type == 'french-press':
            final_params['brew_instructions'] = f"Grind {serving_size}g coffee {params['ideal_grind_size']}. Add {final_params['water_ml']}ml water at {params['recommended_temp_c']}°C. Steep for {params.get('steep_time', 240)} seconds, then press slowly."
        
        elif coffee_type == 'cold-brew':
            steep_hours = params.get('steep_time', 1080) / 60 / 60
            final_params['brew_instructions'] = f"Grind {serving_size}g coffee {params['ideal_grind_size']}. Combine with {final_params['water_ml']}ml room temperature water. Steep for {steep_hours} hours, then filter."
        
        else:
            # Generic instructions for other brew methods
            final_params['brew_instructions'] = f"Use {serving_size}g coffee with {final_params['water_ml']}ml water at {params['recommended_temp_c']}°C."
        
        # Add yield information
        if coffee_type in ['espresso', 'cappuccino', 'latte']:
            final_params['yield_ml'] = round(serving_size * 2)  # Espresso yield is typically 2x the coffee weight
            
            if coffee_type == 'cappuccino':
                milk_ratio = params.get('milk_ratio', '1:1')
                milk_parts = int(milk_ratio.split(':')[1])
                final_params['milk_ml'] = final_params['yield_ml'] * milk_parts
                final_params['total_yield_ml'] = final_params['yield_ml'] + final_params['milk_ml']
            
            elif coffee_type == 'latte':
                milk_ratio = params.get('milk_ratio', '1:3')
                milk_parts = int(milk_ratio.split(':')[1])
                final_params['milk_ml'] = final_params['yield_ml'] * milk_parts
                final_params['total_yield_ml'] = final_params['yield_ml'] + final_params['milk_ml']
        
        else:
            # For other brew methods, yield is roughly the water amount
            # Accounting for some absorption by coffee grounds
            absorption_factor = 1.8  # Coffee typically absorbs ~1.8x its weight in water
            final_params['yield_ml'] = round(final_params['water_ml'] - (serving_size * absorption_factor))
        
        return final_params