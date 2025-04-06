#!/usr/bin/env python3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# Import the updated main framework
from coffee_ml import CoffeeMachineLearning

def generate_synthetic_data(n_samples=100, seed=42):
    """
    Generate synthetic coffee brewing data for testing with updated parameters
    
    Parameters:
    -----------
    n_samples : int
        Number of samples to generate
    seed : int
        Random seed for reproducibility
    
    Returns:
    --------
    data : DataFrame
        Synthetic data
    """
    np.random.seed(seed)
    
    # Cup sizes
    cup_sizes = [89.0, 236.588, 354.882]  # small, medium, large in ml
    cup_sizes_probs = [0.3, 0.5, 0.2]  # probability of each size
    
    # Brewing parameters
    extraction_pressure = np.random.uniform(1, 10, n_samples)  # bars
    temperatures = np.random.uniform(87, 95, n_samples)  # Celsius
    extraction_time = np.random.uniform(20, 40, n_samples)  # seconds
    
    # Cup size selection
    cup_size = np.random.choice(cup_sizes, n_samples, p=cup_sizes_probs)
    
    # Dose size based on cup size (ratio between 14-16)
    dose_size = cup_size / np.random.uniform(14, 16, n_samples)
    # Clip to reasonable range
    dose_size = np.clip(dose_size, 15, 25)
    
    # Fixed grind size
    ground_size = np.full(n_samples, 400)  # microns
    
    # Bean types with possibility of blends
    all_bean_types = ['arabica', 'robusta', 'ethiopian']
    primary_bean_types = np.random.choice(all_bean_types, n_samples)
    
    # Create blend information for 20% of samples
    bean_blends = []
    for i in range(n_samples):
        if np.random.random() < 0.2:  # 20% have blends
            # Create a random blend
            num_beans = np.random.randint(2, 4)  # 2-3 bean types
            beans = np.random.choice(all_bean_types, 
                                     size=num_beans, replace=False)
            
            # Generate random percentages that sum to 100
            percentages = np.random.randint(10, 70, num_beans)
            percentages = (percentages / percentages.sum() * 100).astype(int)
            
            # Ensure they sum to 100
            percentages[-1] = 100 - percentages[:-1].sum()
            
            # Create blend dictionary
            blend = {bean: perc for bean, perc in zip(beans, percentages)}
            bean_blends.append(str(blend))
        else:
            bean_blends.append(None)
    
    # Add some processing methods for integration with quality database
    processing_methods = np.random.choice(['washed', 'natural', 'honey'], n_samples)
    
    # Calculate bitterness primarily based on temperature
    bitterness_base = (temperatures - 87) / (95 - 87) * 9 + 1  # Map 87-95°C to 1-10 scale
    bitterness = bitterness_base + np.random.normal(0, 0.5, n_samples)
    bitterness = np.clip(bitterness, 1, 10)  # Keep in 1-10 range
    
    # Define other flavor profiles with relationships to brewing parameters
    acidity = 0.3 * temperatures - 0.2 * extraction_time + np.random.normal(0, 0.5, n_samples)
    strength = 0.4 * extraction_pressure + 0.2 * dose_size + np.random.normal(0, 0.5, n_samples)
    sweetness = 0.2 * (temperatures - 90) + 0.3 * extraction_time + np.random.normal(0, 0.5, n_samples)
    fruitiness = 0.4 * (temperatures - 90) - 0.2 * extraction_pressure + np.random.normal(0, 0.5, n_samples)
    
    # Scale to 1-10 range
    def scale_to_range(x, min_val=1, max_val=10):
        return (x - np.min(x)) / (np.max(x) - np.min(x)) * (max_val - min_val) + min_val
    
    acidity = np.clip(scale_to_range(acidity), 1, 10)
    strength = np.clip(scale_to_range(strength), 1, 10)
    sweetness = np.clip(scale_to_range(sweetness), 1, 10)
    fruitiness = np.clip(scale_to_range(fruitiness), 1, 10)
    
    # Create DataFrame
    data = pd.DataFrame({
        'extraction_pressure': extraction_pressure,
        'temperature': temperatures,
        'ground_size': ground_size,
        'extraction_time': extraction_time,
        'dose_size': dose_size,
        'cup_size': cup_size,
        'bean_type': primary_bean_types,
        'blend_info': bean_blends,
        'processing_method': processing_methods,
        'acidity': acidity,
        'strength': strength,
        'sweetness': sweetness,
        'fruitiness': fruitiness,
        'bitterness': bitterness  # Changed from maltiness to bitterness
    })
    
    return data

def run_demo():
    """
    Demonstrate the updated coffee ML framework with bean blend optimization
    """
    print("=== AI Coffee Machine ML Framework Demo (Bean Blend Optimization) ===")
    
    # Create a custom class with the right target columns from the start
    class CoffeeMLWithBitterness(CoffeeMachineLearning):
        def __init__(self, data_path=None, model_path=None, quality_db_path=None):
            # Set target columns to use bitterness before parent initialization
            self.target_cols = ['acidity', 'strength', 'sweetness', 'fruitiness', 'bitterness']
            # Call parent init
            super().__init__(data_path, model_path, quality_db_path)
    
    # Initialize framework with bitterness
    ml = CoffeeMLWithBitterness(
        data_path='data', 
        model_path='models',
        quality_db_path=None  # No quality DB for this demo
    )
    
    # Check for existing synthetic data or generate new data
    data_path = 'data/synthetic_brewing_data_updated_bitterness.csv'
    if os.path.exists(data_path):
        print("Loading existing synthetic data...")
        data = pd.read_csv(data_path)
        print(f"  Loaded dataset with {len(data)} samples")
    else:
        print("Generating synthetic data...")
        data = generate_synthetic_data(n_samples=100)
        os.makedirs('data', exist_ok=True)
        data.to_csv(data_path, index=False)
        print(f"  Generated {len(data)} synthetic samples")
    
    # Display sample data
    print("\nSample data (first 3 rows):")
    sample = data.head(3)
    print(sample[['extraction_pressure', 'temperature', 'extraction_time', 
                 'dose_size', 'cup_size', 'bean_type', 'acidity', 'strength', 
                 'sweetness', 'fruitiness', 'bitterness']])
    
    # Train models
    print("\nTraining models...")
    metrics = ml.train_models(data)
    
    print("\nModel training complete.")
    
    # Define a target flavor profile
    desired_flavor = {
        'acidity': 7.5,
        'strength': 8.0,
        'sweetness': 6.5,
        'fruitiness': 7.0,
        'bitterness': 8.0  # Using bitterness instead of maltiness
    }
    
    print("\nDesired flavor profile:")
    for flavor, value in desired_flavor.items():
        print(f"  {flavor}: {value:.2f}")
    
    # Test: Optimal bean selection from all available beans
    print("\n1. Testing optimal bean blend selection from all available beans:")
    
    auto_blend_params = ml.suggest_brewing_parameters(
        desired_flavor,
        cup_size='medium'
    )
    
    print("\nSuggested brewing parameters with automatically optimized bean blend:")
    for param, value in auto_blend_params.items():
        if param == 'ground_size':
            print(f"  {param}: {value} microns (fixed)")
        elif param == 'bean_blend':
            print(f"  {param}: {value}")
            print(f"  Explanation: The system determined this blend is optimal for your desired flavor profile")
        elif isinstance(value, (int, float)):
            print(f"  {param}: {value:.2f}")
        else:
            print(f"  {param}: {value}")
    
    # Test: Optimal blend from limited bean selection
    print("\n2. Testing optimal bean blend from a limited set of beans:")
    
    limited_beans = ['arabica', 'robusta', 'ethiopian']
    limited_blend_params = ml.suggest_brewing_parameters(
        desired_flavor,
        cup_size='medium',
        bean_list=limited_beans
    )
    
    print(f"\nSuggested brewing parameters with blend optimized from {limited_beans}:")
    for param, value in limited_blend_params.items():
        if param == 'ground_size':
            print(f"  {param}: {value} microns (fixed)")
        elif param == 'bean_blend':
            print(f"  {param}: {value}")
        elif isinstance(value, (int, float)):
            print(f"  {param}: {value:.2f}")
        else:
            print(f"  {param}: {value}")
    
    # Test: Comparing flavor profiles of different blends
    print("\n3. Comparing predicted flavor profiles for different bean blends:")
    
    # Define several bean blends to compare
    test_blends = [
        {'arabica': 100},
        {'robusta': 100},
        {'ethiopian': 100},
        auto_blend_params.get('bean_blend', {'arabica': 100}),
        limited_blend_params.get('bean_blend', {'arabica': 100})
    ]
    
    blend_names = [
        "100% Arabica",
        "100% Robusta",
        "100% Ethiopian",
        "Auto-optimized blend",
        "Limited beans blend"
    ]
    
    # Use the same brewing parameters for all tests
    base_params = {
        'extraction_pressure': auto_blend_params['extraction_pressure'],
        'temperature': auto_blend_params['temperature'],
        'extraction_time': auto_blend_params['extraction_time'],
        'dose_size': auto_blend_params['dose_size'],
        'cup_size': auto_blend_params['cup_size']
    }
    
    # Test each blend and calculate distance to desired flavor
    results = []
    
    for i, (blend, name) in enumerate(zip(test_blends, blend_names)):
        # Create test parameters
        test_params = base_params.copy()
        primary_bean = max(blend.items(), key=lambda x: x[1])[0]
        test_params['bean_type'] = primary_bean
        test_params['bean_blend'] = blend
        
        # Predict flavor profile with this blend
        predictions = ml.predict_flavor_profile(test_params)
        
        # Calculate distance to desired profile
        distance = 0
        for flavor, desired_val in desired_flavor.items():
            if flavor in predictions:
                distance += (predictions[flavor] - desired_val) ** 2
        distance = np.sqrt(distance)
        
        # Store results
        result = {
            'Name': name,
            'Blend': str(blend),
            'Distance': distance
        }
        
        for flavor in ml.target_cols:
            if flavor in predictions:
                result[flavor] = predictions[flavor]
        
        results.append(result)
    
    # Display results
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('Distance')
    
    print("\nBlend comparison results (sorted by closeness to desired flavor):")
    print(results_df[['Name', 'Blend', 'Distance'] + ml.target_cols])
    
    # Test: Different desired flavor profiles
    print("\n4. Testing different desired flavor profiles:")
    
    flavor_profiles = [
        {
            'name': 'Bright and Fruity',
            'profile': {'acidity': 8.0, 'strength': 6.0, 'sweetness': 7.5, 'fruitiness': 9.0, 'bitterness': 3.0}
        },
        {
            'name': 'Bold and Strong',
            'profile': {'acidity': 5.0, 'strength': 9.0, 'sweetness': 4.0, 'fruitiness': 3.0, 'bitterness': 8.0}
        },
        {
            'name': 'Smooth and Sweet',
            'profile': {'acidity': 4.0, 'strength': 5.0, 'sweetness': 8.5, 'fruitiness': 6.0, 'bitterness': 4.0}
        }
    ]
    
    for flavor_case in flavor_profiles:
        print(f"\nDesired flavor profile: {flavor_case['name']}")
        for flavor, value in flavor_case['profile'].items():
            print(f"  {flavor}: {value:.2f}")
        
        # Get suggestions
        suggested_params = ml.suggest_brewing_parameters(
            flavor_case['profile'],
            cup_size='medium'
        )
        
        print("\nSuggested brewing parameters and bean blend:")
        for param, value in suggested_params.items():
            if param == 'ground_size':
                print(f"  {param}: {value} microns (fixed)")
            elif param == 'bean_blend':
                print(f"  {param}: {value}")
            elif isinstance(value, (int, float)):
                print(f"  {param}: {value:.2f}")
            else:
                print(f"  {param}: {value}")
    
    # Verify temperature-bitterness relationship
    print("\n5. Verifying temperature-bitterness relationship:")
    bitterness_levels = [2, 5, 8]
    
    for bitterness in bitterness_levels:
        test_flavor = desired_flavor.copy()
        test_flavor['bitterness'] = bitterness
        
        suggested_params = ml.suggest_brewing_parameters(
            test_flavor,
            cup_size='medium'
        )
        
        print(f"Bitterness {bitterness}/10 → Temperature: {suggested_params['temperature']:.1f}°C")
    
    print("\n=== Demo completed successfully ===")

if __name__ == "__main__":
    run_demo()