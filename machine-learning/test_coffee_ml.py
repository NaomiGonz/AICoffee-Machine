#!/usr/bin/env python3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
import argparse

# Import the main framework
from coffee_ml import CoffeeMachineLearning

def generate_synthetic_data(n_samples=100, seed=42):
    """
    Generate synthetic coffee brewing data for testing
    
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
    
    # Brewing parameters
    extraction_pressure = np.random.uniform(1, 10, n_samples)  # bars
    temperature = np.random.uniform(85, 96, n_samples)  # Celsius
    ground_size = np.random.uniform(100, 1000, n_samples)  # microns
    extraction_time = np.random.uniform(20, 40, n_samples)  # seconds
    dose_size = np.random.uniform(15, 25, n_samples)  # grams
    bean_types = np.random.choice(['arabica', 'robusta', 'blend'], n_samples)
    
    # Add some processing methods for integration with quality database
    processing_methods = np.random.choice(['washed', 'natural', 'honey'], n_samples)
    
    # Define simple relationships for flavor profiles based on brewing parameters
    acidity = 0.3 * temperature - 0.2 * extraction_time + np.random.normal(0, 0.5, n_samples)
    strength = 0.4 * extraction_pressure + 0.2 * dose_size - 0.3 * ground_size / 1000 + np.random.normal(0, 0.5, n_samples)
    sweetness = 0.3 * ground_size / 1000 + 0.2 * (temperature - 90) + np.random.normal(0, 0.5, n_samples)
    fruitiness = 0.4 * (temperature - 90) - 0.2 * extraction_pressure + np.random.normal(0, 0.5, n_samples)
    maltiness = 0.3 * extraction_time + 0.2 * dose_size + np.random.normal(0, 0.5, n_samples)
    
    # Scale to 0-10 range
    def scale_to_range(x, min_val=0, max_val=10):
        return (x - np.min(x)) / (np.max(x) - np.min(x)) * (max_val - min_val) + min_val
    
    acidity = scale_to_range(acidity)
    strength = scale_to_range(strength)
    sweetness = scale_to_range(sweetness)
    fruitiness = scale_to_range(fruitiness)
    maltiness = scale_to_range(maltiness)
    
    # Create DataFrame
    data = pd.DataFrame({
        'extraction_pressure': extraction_pressure,
        'temperature': temperature,
        'ground_size': ground_size,
        'extraction_time': extraction_time,
        'dose_size': dose_size,
        'bean_type': bean_types,
        'processing_method': processing_methods,
        'acidity': acidity,
        'strength': strength,
        'sweetness': sweetness,
        'fruitiness': fruitiness,
        'maltiness': maltiness
    })
    
    return data

def run_test(with_quality_db=False):
    """
    Run comprehensive test of the AI Coffee Machine ML framework
    
    Parameters:
    -----------
    with_quality_db : bool
        Whether to include quality database in testing
    """
    print("=== AI Coffee Machine ML Framework Test ===")
    
    # Initialize framework
    quality_db_path = 'data/quality_db' if with_quality_db else None
    ml = CoffeeMachineLearning(
        data_path='data', 
        model_path='models',
        quality_db_path=quality_db_path
    )
    
    # Check for existing synthetic data or generate new data
    data_path = 'data/synthetic_brewing_data.csv'
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
    print("Sample data (first 5 rows):")
    print(data.head())
    
    # Display data statistics
    print("Data statistics:")
    print(data.describe())
    
    # Train models
    print("Training models...")
    metrics = ml.train_models(data)
    
    print("Saved model configuration")
    
    # Test predictions with different bean types
    print("Testing predictions with different bean types:")
    
    base_params = {
        'extraction_pressure': 7.0,
        'temperature': 93.0,
        'ground_size': 400.0,
        'extraction_time': 30.0,
        'dose_size': 20.0
    }
    
    for bean_type in ['arabica', 'robusta', 'blend']:
        params = base_params.copy()
        params['bean_type'] = bean_type
        
        predictions = ml.predict_flavor_profile(params)
        
        print(f"Predicted flavor profile for {bean_type}:")
        for flavor, value in predictions.items():
            if flavor in ml.target_cols:  # Only show core flavor attributes
                print(f"  {flavor}: {value:.2f}")
    
    # Test brewing parameter suggestions
    print("Testing brewing parameter suggestions:")
    
    desired_flavor = {
        'acidity': 7.5,
        'strength': 8.0,
        'sweetness': 6.5,
        'fruitiness': 7.0,
        'maltiness': 5.0
    }
    
    print("Desired flavor profile:")
    for flavor, value in desired_flavor.items():
        print(f"  {flavor}: {value:.2f}")
    
    suggested_params = ml.suggest_brewing_parameters(desired_flavor)
    
    print("Suggested brewing parameters:")
    for param, value in suggested_params.items():
        if isinstance(value, (int, float)):
            print(f"  {param}: {value:.2f}")
        else:
            print(f"  {param}: {value}")
    
    # Test data collection
    print("Testing data collection...")
    
    test_brew = {
        'extraction_pressure': 6.5,
        'temperature': 91.2,
        'ground_size': 350.0,
        'extraction_time': 28.5,
        'dose_size': 19.0,
        'bean_type': 'arabica',
        'processing_method': 'washed'
    }
    
    test_ratings = {
        'acidity': 6.8,
        'strength': 7.2,
        'sweetness': 5.9,
        'fruitiness': 6.5,
        'maltiness': 4.8
    }
    
    ml.collect_brewing_data(test_brew, test_ratings)
    print("  Data point collected")
    
    collected_data = ml.load_data()
    print(f"  Loaded {len(collected_data)} data points")
    
    # Create directories for visualizations
    os.makedirs('data/visualizations', exist_ok=True)
    
    # Feature impact analysis
    print("Analyzing temperature impact on acidity...")
    impact_data = ml.analyze_feature_impact('temperature', 'acidity', 85, 96, 10)
    
    if impact_data is not None and not impact_data.empty:
        # Plot impact
        try:
            plt.figure(figsize=(8, 5))
            plt.plot(impact_data['feature_value'], impact_data['predicted_acidity'], 'o-', linewidth=2)
            plt.xlabel('Temperature (°C)')
            plt.ylabel('Predicted Acidity')
            plt.title('Impact of Temperature on Acidity')
            plt.grid(True, alpha=0.3)
            plt.savefig('data/visualizations/temperature_acidity_impact.png')
            plt.close()
            print("  Visualization saved to data/visualizations/temperature_acidity_impact.png")
        except Exception as e:
            print(f"  Error creating visualization: {e}")
    else:
        print("  No impact data available to visualize")
    
    print("=== Test completed successfully ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test AI Coffee Machine ML Framework')
    parser.add_argument('--with-quality-db', action='store_true', 
                        help='Include quality database in testing')
    
    args = parser.parse_args()
    
    run_test(with_quality_db=args.with_quality_db)