import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import json
from inital import CoffeeMachineLearning

def test_framework():
    """
    Test the CoffeeMachineLearning framework with synthetic data
    """
    print("=== AI Coffee Machine ML Framework Test ===")

    # Create an instance of the ML framework
    ml = CoffeeMachineLearning()

    # Check if synthetic data exists, if not generate it
    data_path = 'data/synthetic_brewing_data.csv'
    if not os.path.exists(data_path):
        print("\nGenerating synthetic data...")
        # Generate synthetic data for testing
        np.random.seed(42)
        n_samples = 100
        
        # Brewing parameters
        extraction_pressure = np.random.uniform(1, 10, n_samples)  # bars
        temperature = np.random.uniform(85, 96, n_samples)  # Celsius
        ground_size = np.random.uniform(100, 1000, n_samples)  # microns
        extraction_time = np.random.uniform(20, 40, n_samples)  # seconds
        dose_size = np.random.uniform(15, 25, n_samples)  # grams
        bean_types = np.random.choice(['arabica', 'robusta', 'blend'], n_samples)
        
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
            'acidity': acidity,
            'strength': strength,
            'sweetness': sweetness,
            'fruitiness': fruitiness,
            'maltiness': maltiness
        })
        
        # Save synthetic data
        os.makedirs('data', exist_ok=True)
        data.to_csv(data_path, index=False)
        print(f"  Created synthetic dataset with {n_samples} samples")
    else:
        print("\nLoading existing synthetic data...")
        data = pd.read_csv(data_path)
        print(f"  Loaded dataset with {len(data)} samples")

    # Print sample data
    print("\nSample data (first 5 rows):")
    print(data.head())

    print("\nData statistics:")
    print(data.describe().round(2))

    # Train models
    print("\nTraining models...")
    metrics = ml.train_models(data)
    
    # Print metrics summary
    print("\nModel Performance Summary:")
    print("=" * 60)
    print(f"{'Flavor Attribute':<20} {'Model Type':<20} {'R²':>8} {'MSE':>8}")
    print("=" * 60)
    for attr, result in metrics.items():
        print(f"{attr:<20} {result['model_type']:<20} {result['r2']:>8.4f} {result['mse']:>8.4f}")
    print("=" * 60)

    # Save configuration
    ml.save_config()
    print("\nSaved model configuration")

    # Test prediction with various bean types
    print("\nTesting predictions with different bean types:")

    for bean_type in ['arabica', 'robusta', 'blend']:
        params = {
            'extraction_pressure': 8.5,
            'temperature': 92.0,
            'ground_size': 500,
            'extraction_time': 30,
            'dose_size': 20,
            'bean_type': bean_type
        }
        
        try:
            # Predict flavor profile
            flavor_profile = ml.predict_flavor_profile(params)
            print(f"\nPredicted flavor profile for {bean_type}:")
            for flavor, value in flavor_profile.items():
                print(f"  {flavor}: {value:.2f}")
        except Exception as e:
            print(f"Error predicting for {bean_type}: {e}")

    # Test suggesting brewing parameters for a desired flavor profile
    print("\nTesting brewing parameter suggestions:")
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
    print("\nSuggested brewing parameters:")
    for param, value in suggested_params.items():
        if param != 'bean_type':
            print(f"  {param}: {value:.2f}")
        else:
            print(f"  {param}: {value}")

    # Test data collection
    print("\nTesting data collection...")
    brewing_params = {
        'extraction_pressure': 7.5,
        'temperature': 93.0,
        'ground_size': 450,
        'extraction_time': 28,
        'dose_size': 18,
        'bean_type': 'arabica'
    }

    flavor_ratings = {
        'acidity': 6.8,
        'strength': 7.2,
        'sweetness': 5.9,
        'fruitiness': 6.5,
        'maltiness': 4.8
    }

    ml.collect_brewing_data(brewing_params, flavor_ratings)
    print("  Data point collected")

    # Test loading data
    loaded_data = ml.load_data()
    print(f"  Loaded {len(loaded_data)} data points")

    # Test model evaluation if we have enough data
    if len(loaded_data) >= 10:
        print("\nEvaluating model performance...")
        eval_metrics = ml.evaluate_models()
        
        for target, metrics in eval_metrics.items():
            print(f"  {target}: R² = {metrics['r2']:.4f}, MSE = {metrics['mse']:.4f}")
    else:
        print("\nNot enough data for model evaluation (need at least 10 samples)")
    
    # Test analyzing feature impact
    print("\nAnalyzing feature impact:")
    try:
        # Analyze impact of temperature on acidity
        temp_impact = ml.analyze_feature_impact('temperature', 'acidity', 85, 96, 10)
        print("\nImpact of temperature on acidity:")
        print(temp_impact)
        
        # Plot the relationship
        plt.figure(figsize=(10, 6))
        plt.plot(temp_impact['feature_value'], temp_impact['predicted_acidity'])
        plt.xlabel('Temperature (°C)')
        plt.ylabel('Predicted Acidity')
        plt.title('Effect of Temperature on Acidity')
        plt.grid(True)
        plt.savefig('data/temperature_acidity_impact.png')
        plt.close()
        print("  Generated impact analysis plot in 'data/temperature_acidity_impact.png'")
    except Exception as e:
        print(f"  Error analyzing feature impact: {e}")

    print("\n=== Test completed successfully ===")

if __name__ == "__main__":
    test_framework()