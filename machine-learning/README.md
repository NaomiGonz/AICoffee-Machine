# AI Coffee Machine ML Framework

A machine learning framework for optimizing coffee brewing parameters based on desired flavor profiles. This framework can predict flavor outcomes from brewing parameters and suggest optimal brewing settings to achieve target flavor attributes.

## Features

- Predict flavor profiles based on brewing parameters
- Suggest optimal brewing parameters for desired flavor profiles
- Continuous learning through data collection
- Quality database integration for enhanced predictions
- Feature impact analysis and visualization
- Support for multiple bean types

## File Structure

```
ai-coffee-machine/
├── coffee_ml.py                # Main framework class
├── data_processor.py           # Data preprocessing component
├── model_trainer.py            # Model training component
├── flavor_predictor.py         # Flavor prediction component
├── parameter_optimizer.py      # Parameter optimization component
├── quality_database.py         # Coffee quality database component
├── test_coffee_ml.py           # Test script
```

## Function Sequence Guide

### Predict Flavor Profiles

```python
# Define brewing parameters
brewing_params = {
    'extraction_pressure': 8.5,  # bars
    'temperature': 92.0,         # Celsius
    'ground_size': 500,          # microns
    'extraction_time': 30,       # seconds
    'dose_size': 20,             # grams
    'bean_type': 'arabica'       # 'arabica', 'robusta', or 'blend'
}

# Predict flavor profile
flavor_profile = ml.predict_flavor_profile(brewing_params)
```

**Example Output:**
```python
{
    'acidity': 5.92,      # Scale of 0-10
    'strength': 5.70,     # Scale of 0-10
    'sweetness': 5.42,    # Scale of 0-10
    'fruitiness': 6.03,   # Scale of 0-10
    'maltiness': 4.81     # Scale of 0-10
}
```

### Suggest Brewing Parameters

```python
# Define desired flavor profile
desired_flavor = {
    'acidity': 7.5,       # Scale of 0-10
    'strength': 8.0,      # Scale of 0-10
    'sweetness': 6.5,     # Scale of 0-10
    'fruitiness': 7.0,    # Scale of 0-10
    'maltiness': 5.0      # Scale of 0-10
}

# Get suggested brewing parameters
suggested_params = ml.suggest_brewing_parameters(desired_flavor)
```

**Example Output:**
```python
{
    'extraction_pressure': 9.03,    # bars
    'temperature': 95.70,           # Celsius
    'ground_size': 611.00,          # microns
    'extraction_time': 27.81,       # seconds
    'dose_size': 24.42,             # grams
    'bean_type': 'arabica'          # 'arabica', 'robusta', or 'blend'
}
```

### Collect Brewing Data

```python
# After brewing coffee with suggested parameters,
# collect user flavor ratings
flavor_ratings = {
    'acidity': 7.2,       # Scale of 0-10
    'strength': 7.8,      # Scale of 0-10
    'sweetness': 6.3,     # Scale of 0-10
    'fruitiness': 6.8,    # Scale of 0-10
    'maltiness': 5.1      # Scale of 0-10
}

# Store this data point for continuous learning
ml.collect_brewing_data(brewing_params, flavor_ratings)
```

## Running the Test Script

A comprehensive test script is included to verify all functionality:

```bash
# Run standard version
python test_coffee_ml.py

# Run with quality database integration
python test_coffee_ml.py --with-quality-db
```

## Data Format

### Brewing Parameters (Inputs)

| Parameter | Unit | Range | Description |
|-----------|------|-------|-------------|
| extraction_pressure | bars | 1-10 | Pressure applied during extraction |
| temperature | °C | 85-96 | Water temperature |
| ground_size | microns | 100-1000 | Coffee grind size (lower = finer) |
| extraction_time | seconds | 15-45 | Duration of extraction |
| dose_size | grams | 10-30 | Amount of coffee used |
| bean_type | string | 'arabica', 'robusta', 'blend' | Type of coffee bean |

### Flavor Attributes (Outputs)

| Attribute | Scale | Description |
|-----------|-------|-------------|
| acidity | 0-10 | Brightness, tartness, or fruitiness |
| strength | 0-10 | Overall intensity and body |
| sweetness | 0-10 | Natural sweetness perception |
| fruitiness | 0-10 | Presence of fruit notes |
| maltiness | 0-10 | Chocolate, caramel, or malty notes |

### Using with the Quality Database

When using the quality database integration:

1. Ensure arabica and robusta CSV files are in the `data/quality_db/` directory
2. Initialize with `use_quality_db=True`
3. The framework will automatically enhance predictions using the reference data