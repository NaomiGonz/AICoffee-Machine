import numpy as np
import pandas as pd
from scipy.optimize import minimize
import matplotlib.pyplot as plt

class ParameterOptimizer:
    """
    Component for optimizing brewing parameters to achieve desired flavor profiles
    Handles the inverse problem of finding brewing parameters for a target flavor
    """
    
    def __init__(self, feature_cols, target_cols, model_path, data_processor, flavor_predictor, 
                 cup_sizes=None, default_ratio=15, grind_size=400):
        """
        Initialize the parameter optimizer
        
        Parameters:
        -----------
        feature_cols : list
            Columns to use as features
        target_cols : list
            Columns to use as targets
        model_path : str
            Path to load trained models from
        data_processor : DataProcessor
            Component for data preprocessing
        flavor_predictor : FlavorPredictor
            Component for flavor prediction
        cup_sizes : dict, optional
            Dictionary of cup sizes (small, medium, large) and their volumes in ml
        default_ratio : float, optional
            Default water to coffee ratio (ml water : g coffee)
        grind_size : int, optional
            Fixed grind size value in microns
        """
        self.feature_cols = feature_cols
        self.target_cols = target_cols
        self.model_path = model_path
        self.data_processor = data_processor
        self.flavor_predictor = flavor_predictor
        
        # Cup sizes and ratios
        self.cup_sizes = cup_sizes or {
            'small': 89.0,
            'medium': 236.588,
            'large': 354.882
        }
        self.default_ratio = default_ratio
        self.grind_size = grind_size
        
        # Default parameter ranges (modified to remove ground_size and add cup_size)
        self.param_ranges = {
            'extraction_pressure': (1, 10),     # bars
            'temperature': (85, 96),            # Celsius
            'extraction_time': (20, 40),        # seconds
            'dose_size': (15, 25),              # grams
            'cup_size': (min(self.cup_sizes.values()), max(self.cup_sizes.values()))  # ml
        }
    
    def update_config(self, feature_cols=None, target_cols=None, param_ranges=None, 
                      cup_sizes=None, default_ratio=None, grind_size=None):
        """
        Update configuration parameters
        
        Parameters:
        -----------
        feature_cols : list, optional
            Columns to use as features
        target_cols : list, optional
            Columns to use as targets
        param_ranges : dict, optional
            Ranges for brewing parameters (min, max)
        cup_sizes : dict, optional
            Dictionary of cup sizes and their volumes
        default_ratio : float, optional
            Water to coffee ratio
        grind_size : int, optional
            Fixed grind size value
        """
        if feature_cols is not None:
            self.feature_cols = feature_cols
        
        if target_cols is not None:
            self.target_cols = target_cols
            
        if param_ranges is not None:
            self.param_ranges.update(param_ranges)
            
        if cup_sizes is not None:
            self.cup_sizes = cup_sizes
            
        if default_ratio is not None:
            self.default_ratio = default_ratio
            
        if grind_size is not None:
            self.grind_size = grind_size
    
    def optimize(self, desired_flavor_profile, fixed_params=None, starting_params=None):
        """
        Find optimal brewing parameters for a desired flavor profile
        
        Parameters:
        -----------
        desired_flavor_profile : dict
            Desired values for flavor attributes
        fixed_params : dict, optional
            Parameters to keep fixed (e.g., {'bean_type': 'arabica'})
        starting_params : dict, optional
            Starting point for optimization
            
        Returns:
        --------
        optimal_params : dict
            Optimized brewing parameters
        """
        try:
            fixed_params = fixed_params or {}
            
            # Handle multi-bean blend if specified in fixed_params
            bean_blend = None
            if 'bean_blend' in fixed_params:
                bean_blend = fixed_params['bean_blend']
                # Keep primary bean type for optimization
                if 'bean_type' not in fixed_params and bean_blend:
                    fixed_params['bean_type'] = max(bean_blend.items(), key=lambda x: x[1])[0]
            
            # Use grid search for initial optimization
            best_params, best_distance = self._grid_search(
                desired_flavor_profile, 
                fixed_params,
                starting_params
            )
            
            # Refine with local optimization if possible
            try:
                refined_params = self._local_optimization(
                    best_params, 
                    desired_flavor_profile,
                    fixed_params
                )
                
                # Check if refined solution is better
                refined_distance = self._calculate_distance(
                    refined_params, 
                    desired_flavor_profile
                )
                
                if refined_distance < best_distance:
                    best_params = refined_params
                    
            except Exception as e:
                print(f"Local optimization failed: {e}. Using grid search result.")
            
            # Ensure results are within bounds and rounded appropriately
            best_params = self._format_parameters(best_params)
            
            # Add fixed grind size
            best_params['ground_size'] = self.grind_size
            
            # Add back bean blend information if it was provided
            if bean_blend:
                best_params['bean_blend'] = bean_blend
            elif 'bean_blend' not in best_params:
                # Check if a blend was specified elsewhere
                if 'bean_blend' in fixed_params:
                    best_params['bean_blend'] = fixed_params['bean_blend']
            
            return best_params
            
        except Exception as e:
            print(f"Overall optimization failed: {e}. Using default parameters.")
            
            # Create reasonable default parameters
            default_params = {
                'extraction_pressure': 7.0,
                'temperature': 93.0,
                'extraction_time': 30.0,
                'dose_size': 20.0,
                'cup_size': fixed_params.get('cup_size', 236.588),  # medium cup
                'bean_type': fixed_params.get('bean_type', 'arabica'),
                'ground_size': self.grind_size
            }
            
            # Use temperature from bitterness if specified
            if 'bitterness' in desired_flavor_profile:
                bitterness = desired_flavor_profile['bitterness']
                default_params['temperature'] = 87 + (bitterness - 1) * (95 - 87) / 9
            elif 'maltiness' in desired_flavor_profile:
                maltiness = desired_flavor_profile['maltiness']
                default_params['temperature'] = 87 + (maltiness - 1) * (95 - 87) / 9
                
            # Add bean blend if provided
            if 'bean_blend' in fixed_params:
                default_params['bean_blend'] = fixed_params['bean_blend']
            
            return default_params
    
    def _grid_search(self, desired_flavor_profile, fixed_params, starting_params=None):
        """
        Perform grid search to find optimal brewing parameters
        
        Parameters:
        -----------
        desired_flavor_profile : dict
            Desired values for flavor attributes
        fixed_params : dict
            Parameters to keep fixed
        starting_params : dict, optional
            Starting point for optimization
            
        Returns:
        --------
        best_params : dict
            Best parameters found
        best_distance : float
            Distance to desired profile
        """
        try:
            # Create a grid of parameter combinations
            grid_size = 1000
            params_grid = []
            
            # Adjust ranges if starting parameters are provided
            param_ranges = self.param_ranges.copy()
            
            if starting_params:
                for param, value in starting_params.items():
                    if param in param_ranges:
                        # Narrow range around starting value
                        min_val, max_val = param_ranges[param]
                        range_width = max_val - min_val
                        new_min = max(min_val, value - range_width * 0.25)
                        new_max = min(max_val, value + range_width * 0.25)
                        param_ranges[param] = (new_min, new_max)
            
            # Generate grid points, ensuring cup_size and dose_size relationship
            for _ in range(grid_size):
                params = {}
                
                # First select cup size (if not fixed)
                if 'cup_size' not in fixed_params:
                    cup_sizes = list(self.cup_sizes.values())
                    params['cup_size'] = np.random.choice(cup_sizes)
                else:
                    params['cup_size'] = fixed_params['cup_size']
                
                # Calculate appropriate dose size based on cup size and ratio
                suggested_dose = params['cup_size'] / self.default_ratio
                dose_min = max(self.param_ranges['dose_size'][0], suggested_dose * 0.8)
                dose_max = min(self.param_ranges['dose_size'][1], suggested_dose * 1.2)
                
                # Generate other parameters
                for param, (min_val, max_val) in param_ranges.items():
                    if param not in fixed_params and param != 'cup_size':
                        if param == 'dose_size':
                            params[param] = np.random.uniform(dose_min, dose_max)
                        elif param == 'temperature':
                            # Check if bitterness or maltiness is specified to link to temperature
                            if 'temperature' in fixed_params:
                                # If temperature is fixed, use that value
                                params[param] = fixed_params['temperature']
                            elif 'bitterness' in desired_flavor_profile:
                                # Link temperature to desired bitterness
                                bitterness = desired_flavor_profile['bitterness']
                                # Map bitterness 1-10 to temperature 87-95°C with some randomness
                                base_temp = 87 + (bitterness - 1) * (95 - 87) / 9
                                # Add small random variation (±1°C)
                                params[param] = np.random.uniform(base_temp - 1, base_temp + 1)
                            elif 'maltiness' in desired_flavor_profile:
                                # For backward compatibility, check for maltiness too
                                maltiness = desired_flavor_profile['maltiness']
                                base_temp = 87 + (maltiness - 1) * (95 - 87) / 9
                                params[param] = np.random.uniform(base_temp - 1, base_temp + 1)
                            else:
                                # If neither is specified, use random temperature
                                params[param] = np.random.uniform(min_val, max_val)
                        else:
                            params[param] = np.random.uniform(min_val, max_val)
                    else:
                        params[param] = fixed_params[param]
                
                # Fill in fixed params
                params.update(fixed_params)
                params_grid.append(params)
            
            # Convert to DataFrame for batch prediction
            grid_df = pd.DataFrame(params_grid)
            
            # Default bean_type if not specified
            if 'bean_type' not in grid_df.columns and 'bean_type' not in fixed_params:
                grid_df['bean_type'] = 'arabica'
            
            # Add fixed grind_size
            grid_df['ground_size'] = self.grind_size
            
            # Add flavor_profile_cluster if needed (since our model was trained with it)
            if 'flavor_profile_cluster' not in grid_df.columns:
                grid_df['flavor_profile_cluster'] = 0  # Default cluster value
            
            # Predict flavor profiles for all parameter combinations
            best_params = None
            best_distance = float('inf')
            
            found_valid_params = False
            
            for i in range(0, len(grid_df), 100):  # Process in batches
                batch = grid_df.iloc[i:i+100].copy()
                
                try:
                    # Preprocess batch
                    X_batch = self.data_processor.preprocess_data(batch, training=False)
                    
                    # Calculate distance to desired flavor profile for each combination
                    for j in range(len(batch)):
                        try:
                            X_single = X_batch.iloc[[j]]
                            pred_profile = self._predict_with_feature_alignment(X_single)
                            
                            # Calculate Euclidean distance to desired profile
                            distance = 0
                            for target, desired_val in desired_flavor_profile.items():
                                if target in pred_profile:
                                    distance += (pred_profile[target] - desired_val) ** 2
                            
                            distance = np.sqrt(distance)
                            
                            if distance < best_distance:
                                best_distance = distance
                                best_params = batch.iloc[j].to_dict()
                                found_valid_params = True
                        except Exception as e:
                            # Skip this individual prediction if there's an error
                            continue
                
                except Exception as e:
                    # Skip this batch if preprocessing fails
                    continue
            
            if not found_valid_params:
                # Provide sensible defaults if no valid parameters were found
                default_params = {
                    'extraction_pressure': 7.0,
                    'temperature': 93.0,
                    'extraction_time': 30.0,
                    'dose_size': 20.0,
                    'cup_size': 236.588,  # medium cup
                    'bean_type': fixed_params.get('bean_type', 'arabica')
                }
                return default_params, float('inf')
            
            return best_params, best_distance
            
        except Exception as e:
            print(f"Grid search failed: {e}")
            # Provide sensible defaults if grid search fails
            default_params = {
                'extraction_pressure': 7.0,
                'temperature': 93.0,
                'extraction_time': 30.0,
                'dose_size': 20.0,
                'cup_size': 236.588,  # medium cup
                'bean_type': fixed_params.get('bean_type', 'arabica')
            }
            return default_params, float('inf')
    
    def _predict_with_feature_alignment(self, X):
        """
        Make predictions with proper feature alignment
        
        Parameters:
        -----------
        X : DataFrame
            Input features
            
        Returns:
        --------
        predictions : dict
            Predicted flavor profiles
        """
        predictions = {}
        
        for target in self.target_cols:
            if target in self.flavor_predictor.models:
                model = self.flavor_predictor.models[target]
                
                # Check if model has feature names information
                if hasattr(model, 'feature_names_in_'):
                    # Create a dataframe with the exact columns and order expected by the model
                    X_aligned = pd.DataFrame(index=X.index)
                    
                    # Add each feature in the correct order
                    for feature in model.feature_names_in_:
                        if feature in X.columns:
                            X_aligned[feature] = X[feature]
                        else:
                            # Add missing feature with a default value (0)
                            X_aligned[feature] = 0
                    
                    # Use the aligned features for prediction
                    predictions[target] = model.predict(X_aligned)[0]
                else:
                    # Fallback if model doesn't have feature_names_in_
                    predictions[target] = model.predict(X)[0]
            else:
                try:
                    model = joblib.load(f"{self.model_path}/model_{target}.pkl")
                    self.flavor_predictor.models[target] = model
                    
                    # Same alignment process after loading
                    if hasattr(model, 'feature_names_in_'):
                        X_aligned = pd.DataFrame(index=X.index)
                        for feature in model.feature_names_in_:
                            if feature in X.columns:
                                X_aligned[feature] = X[feature]
                            else:
                                X_aligned[feature] = 0
                        predictions[target] = model.predict(X_aligned)[0]
                    else:
                        predictions[target] = model.predict(X)[0]
                except Exception:
                    # If we can't predict this target, set a default value
                    predictions[target] = 5.0  # Middle of the range
        
        return predictions
    
    def _local_optimization(self, initial_params, desired_flavor_profile, fixed_params):
        """
        Refine parameters using local optimization
        
        Parameters:
        -----------
        initial_params : dict
            Initial parameter values from grid search
        desired_flavor_profile : dict
            Desired values for flavor attributes
        fixed_params : dict
            Parameters to keep fixed
            
        Returns:
        --------
        optimized_params : dict
            Locally optimized parameters
        """
        # Define parameters to optimize (exclude fixed and categorical params)
        # We'll only optimize numeric parameters to avoid encoding issues
        param_names = [p for p in self.param_ranges.keys() 
                     if p not in fixed_params and p not in ['bean_type']]
        
        # Define initial values and bounds
        x0 = [initial_params[p] for p in param_names]
        bounds = [self.param_ranges[p] for p in param_names]
        
        # Define objective function (only optimizing numeric params)
        def objective(x):
            # Create parameter dict with both numeric and fixed params
            params = {p: v for p, v in zip(param_names, x)}
            params.update(fixed_params)
            
            # Fill in non-optimized categorical params from initial values
            for key, value in initial_params.items():
                if key not in params and key not in ['bean_type']:
                    params[key] = value
            
            # Ensure bean_type is set
            if 'bean_type' not in params:
                params['bean_type'] = initial_params.get('bean_type', 'arabica')
            
            # Add flavor_profile_cluster
            params['flavor_profile_cluster'] = initial_params.get('flavor_profile_cluster', 0)
                
            return self._calculate_distance(params, desired_flavor_profile)
        
        # Run optimization
        result = minimize(
            objective, 
            x0, 
            method='L-BFGS-B', 
            bounds=bounds
        )
        
        # Convert result back to parameter dictionary
        optimized_params = {p: v for p, v in zip(param_names, result.x)}
        
        # Add fixed params and categorical params from initial values
        optimized_params.update(fixed_params)
        
        # Copy non-optimized params from initial values
        for key, value in initial_params.items():
            if key not in optimized_params:
                optimized_params[key] = value
        
        return optimized_params
    
    def _calculate_distance(self, params, desired_flavor_profile):
        """
        Calculate distance between predicted flavor profile and desired flavor profile
        
        Parameters:
        -----------
        params : dict
            Brewing parameters
        desired_flavor_profile : dict
            Desired flavor profile
            
        Returns:
        --------
        distance : float
            Euclidean distance between predicted and desired profiles
        """
        # Create DataFrame with single row
        params_df = pd.DataFrame([params])
        
        # Add flavor_profile_cluster if missing
        if 'flavor_profile_cluster' not in params_df.columns:
            params_df['flavor_profile_cluster'] = 0
        
        # Add fixed grind_size
        if 'ground_size' not in params_df.columns:
            params_df['ground_size'] = self.grind_size
        
        # Preprocess data
        try:
            X = self.data_processor.preprocess_data(params_df, training=False)
            
            # Predict flavor profile with feature alignment
            predicted = self._predict_with_feature_alignment(X)
            
            # Calculate Euclidean distance
            distance = 0
            for target, desired_val in desired_flavor_profile.items():
                if target in predicted:
                    distance += (predicted[target] - desired_val) ** 2
            
            return np.sqrt(distance)
        except Exception as e:
            # Return a high distance value if prediction fails
            print(f"Error calculating distance: {e}")
            return float('inf')
    
    def _format_parameters(self, params):
        """
        Format parameters to ensure they are within bounds and properly rounded
        
        Parameters:
        -----------
        params : dict
            Parameters to format
            
        Returns:
        --------
        formatted_params : dict
            Formatted parameters
        """
        formatted = {}
        
        for param, value in params.items():
            if param in self.param_ranges:
                min_val, max_val = self.param_ranges[param]
                
                # Ensure value is within bounds
                value = max(min_val, min(max_val, value))
                
                # Round appropriately
                if param == 'temperature':
                    value = round(value, 1)  # One decimal for temperature
                elif param in ['extraction_pressure', 'dose_size']:
                    value = round(value, 2)  # Two decimals for pressure and dose
                elif param == 'extraction_time':
                    value = round(value, 2)  # Two decimals for time
                elif param == 'cup_size':
                    # Find closest standard cup size
                    cup_sizes = list(self.cup_sizes.values())
                    value = min(cup_sizes, key=lambda x: abs(x - value))
                
                formatted[param] = value
            else:
                # Keep non-brewing parameters as-is
                formatted[param] = value
        
        # Remove feature_profile_cluster as it's not a brewing parameter
        if 'flavor_profile_cluster' in formatted:
            del formatted['flavor_profile_cluster']
        
        return formatted