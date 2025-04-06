import numpy as np
import pandas as pd
import os
import joblib
import json
import requests
from scipy.optimize import minimize

# Import components
from data_processor import DataProcessor
from model_trainer import ModelTrainer
from flavor_predictor import FlavorPredictor
from parameter_optimizer import ParameterOptimizer
from quality_database import QualityDatabase

class CoffeeMachineLearning:
    """
    Enhanced Machine Learning framework for AI Coffee Machine
    This class handles data collection, processing, model training, and prediction
    for optimizing coffee brewing parameters based on flavor profiles,
    with integration of coffee quality database for improved predictions.
    """
    
    def __init__(self, data_path=None, model_path=None, quality_db_path=None):
        """
        Initialize the ML framework with paths for data and model storage
        
        Parameters:
        -----------
        data_path : str
            Path to store collected data
        model_path : str
            Path to store trained models
        quality_db_path : str
            Path to coffee quality database
        """
        self.data_path = data_path or 'data/'
        self.model_path = model_path or 'models/'
        
        # Core brewing parameters - modified to include cup_size and remove ground_size
        self.feature_cols = ['extraction_pressure', 'temperature', 'extraction_time', 
                            'dose_size', 'cup_size', 'bean_type']
        
        # Core flavor profiles
        self.target_cols = ['acidity', 'strength', 'sweetness', 'fruitiness', 'bitterness']
        
        # Column types - updated for new parameters
        self.numeric_cols = ['extraction_pressure', 'temperature', 'extraction_time', 
                            'dose_size', 'cup_size']
        self.categorical_cols = ['bean_type', 'processing_method', 'color', 
                                'country_of_origin', 'region']
        
        # Cup size definitions
        self.cup_sizes = {
            'small': 89.0,      # ml
            'medium': 236.588,  # ml
            'large': 354.882    # ml
        }
        
        # Available bean types
        self.available_beans = ['arabica', 'robusta', 'ethiopian']
        
        # Default water to coffee ratio (ml water : g coffee)
        self.default_ratio = 15
        
        # Fixed grind size value
        self.grind_size = 400  # microns (fixed value)
        
        # Ensure directories exist
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.model_path, exist_ok=True)
        
        # Initialize components
        self.data_processor = DataProcessor(
            feature_cols=self.feature_cols,
            target_cols=self.target_cols,
            numeric_cols=self.numeric_cols,
            categorical_cols=self.categorical_cols,
            model_path=self.model_path
        )
        
        self.quality_db = QualityDatabase(quality_db_path) if quality_db_path else None
        
        self.model_trainer = ModelTrainer(
            feature_cols=self.feature_cols,
            target_cols=self.target_cols,
            model_path=self.model_path
        )
        
        self.flavor_predictor = FlavorPredictor(
            feature_cols=self.feature_cols,
            target_cols=self.target_cols,
            model_path=self.model_path
        )
        
        self.parameter_optimizer = ParameterOptimizer(
            feature_cols=self.feature_cols,
            target_cols=self.target_cols,
            model_path=self.model_path,
            data_processor=self.data_processor,
            flavor_predictor=self.flavor_predictor,
            cup_sizes=self.cup_sizes,
            default_ratio=self.default_ratio,
            grind_size=self.grind_size
        )
        
        # Load configuration if exists
        try:
            self.load_config()
        except Exception as e:
            print(f"Error loading config: {e}. Using default configuration.")
    
    def train_models(self, data, test_size=0.2, random_state=42):
        """
        Train models for predicting flavor profiles from brewing parameters
        
        Parameters:
        -----------
        data : DataFrame
            Data containing both brewing parameters and flavor profiles
        test_size : float
            Proportion of data to use for testing
        random_state : int
            Random seed for reproducibility
            
        Returns:
        --------
        metrics : dict
            Performance metrics for each model
        """
        # Add fixed grind_size to data if not present
        if 'ground_size' not in data.columns:
            data['ground_size'] = self.grind_size
        
        # Enrich with quality database if available
        if self.quality_db:
            data = self.quality_db.enrich_data(data)
        
        # Preprocess data
        X, y = self.data_processor.preprocess_data(data, training=True)
        
        # Train models
        metrics = self.model_trainer.train_models(X, y, test_size, random_state)
        
        # Save the configuration
        self.save_config()
        
        return metrics
    
    def predict_flavor_profile(self, brewing_params):
        """
        Predict flavor profile from brewing parameters
        
        Parameters:
        -----------
        brewing_params : dict or DataFrame
            Brewing parameters to use for prediction
            
        Returns:
        --------
        predictions : dict
            Predicted flavor profile values
        """
        # Convert dict to DataFrame if needed
        if isinstance(brewing_params, dict):
            brewing_params = pd.DataFrame([brewing_params])
        
        # Add fixed grind_size
        brewing_params['ground_size'] = self.grind_size
        
        # Handle bean blend if specified
        if 'bean_blend' in brewing_params.columns:
            # Process the blend and use the primary bean type
            blend = brewing_params['bean_blend'].iloc[0]
            if isinstance(blend, dict) and len(blend) > 0:
                # Get primary bean (highest percentage)
                primary_bean = max(blend.items(), key=lambda x: x[1])[0]
                brewing_params['bean_type'] = primary_bean
                
                # Store blend info for reference
                brewing_params['blend_info'] = str(blend)
            else:
                # Default to arabica if no blend info
                brewing_params['bean_type'] = 'arabica'
        
        # Enrich with quality database if available
        if self.quality_db:
            brewing_params = self.quality_db.enrich_data(brewing_params)
        
        # Preprocess the input data
        X = self.data_processor.preprocess_data(brewing_params, training=False)
        
        # Make predictions
        predictions = self.flavor_predictor.predict(X)
        
        # Add quality database insights if available
        if self.quality_db and 'flavor_profile_cluster' in X.columns:
            cluster = int(X['flavor_profile_cluster'].iloc[0])
            additional_insights = self.quality_db.get_cluster_insights(cluster)
            predictions.update(additional_insights)
        
        return predictions
    
    def suggest_brewing_parameters(self, desired_flavor_profile, cup_size='medium', bean_list=None, processing_method=None, country=None):
        """
        Suggest brewing parameters to achieve a desired flavor profile
        
        Parameters:
        -----------
        desired_flavor_profile : dict
            Desired values for flavor attributes
        cup_size : str
            Size of cup ('small', 'medium', 'large')
        bean_list : list, optional
            List of bean types to blend (system determines optimal percentages)
        processing_method : str, optional
            Specific processing method to use
        country : str, optional
            Specific country of origin to use
            
        Returns:
        --------
        suggested_params : dict
            Suggested brewing parameters including the optimal bean blend
        """
        try:
            # Fix categorical values if specified
            fixed_params = {}
            
            # Set cup size
            if cup_size in self.cup_sizes:
                fixed_params['cup_size'] = self.cup_sizes[cup_size]
            else:
                fixed_params['cup_size'] = self.cup_sizes['medium']
            
            # Calculate dose size based on cup size and default ratio
            suggested_dose = fixed_params['cup_size'] / self.default_ratio
            
            if processing_method:
                fixed_params['processing_method'] = processing_method
                
            if country:
                fixed_params['country_of_origin'] = country
            
            # Use bitterness as temperature guide (if bitterness is specified)
            if 'bitterness' in desired_flavor_profile:
                # Adjust temperature based on bitterness (higher bitterness = higher temperature)
                bitterness = desired_flavor_profile['bitterness']
                # Linear mapping from bitterness 1-10 to temperature range 87-95°C
                suggested_temp = 87 + (bitterness - 1) * (95 - 87) / 9
                fixed_params['temperature'] = suggested_temp
            # For backward compatibility, also check for maltiness if bitterness isn't present
            elif 'maltiness' in desired_flavor_profile:
                # Adjust temperature based on maltiness (higher maltiness = higher temperature)
                maltiness = desired_flavor_profile['maltiness']
                # Linear mapping from maltiness 1-10 to temperature range 87-95°C
                suggested_temp = 87 + (maltiness - 1) * (95 - 87) / 9
                fixed_params['temperature'] = suggested_temp
            
            # Determine the optimal bean blend if beans are specified
            bean_blend = None
            if bean_list and len(bean_list) > 0:
                # Create an equal blend as fallback
                bean_blend = {}
                equal_percent = 100 // len(bean_list)
                remainder = 100 % len(bean_list)
                
                for i, bean in enumerate(bean_list):
                    # Add remainder to first bean
                    if i == 0:
                        bean_blend[bean] = equal_percent + remainder
                    else:
                        bean_blend[bean] = equal_percent
                        
                # Set primary bean type
                primary_bean = max(bean_blend.items(), key=lambda x: x[1])[0]
                fixed_params['bean_type'] = primary_bean
                fixed_params['bean_blend'] = bean_blend
            else:
                # Create an equal blend of the first 3 available beans
                bean_list = self.available_beans[:3]  # Limit to first 3 beans
                bean_blend = {}
                equal_percent = 100 // len(bean_list)
                remainder = 100 % len(bean_list)
                
                for i, bean in enumerate(bean_list):
                    # Add remainder to first bean
                    if i == 0:
                        bean_blend[bean] = equal_percent + remainder
                    else:
                        bean_blend[bean] = equal_percent
                    
                # Set primary bean type
                primary_bean = max(bean_blend.items(), key=lambda x: x[1])[0]
                fixed_params['bean_type'] = primary_bean
                fixed_params['bean_blend'] = bean_blend
            
            # Get starting recommendations from quality database
            starting_params = None
            if self.quality_db:
                try:
                    starting_params = self.quality_db.suggest_params_for_flavor(desired_flavor_profile, fixed_params)
                except:
                    pass
            
            # Optimize parameters
            params = self.parameter_optimizer.optimize(
                desired_flavor_profile, 
                fixed_params=fixed_params, 
                starting_params=starting_params
            )
            
            # Ensure dose_size is appropriate for cup_size
            params['dose_size'] = min(max(suggested_dose * 0.8, 15), min(suggested_dose * 1.2, 25))
            
            # Add bean blend to final parameters if not already there
            if bean_blend and 'bean_blend' not in params:
                params['bean_blend'] = bean_blend
            
            return params
            
        except Exception as e:
            print(f"Error suggesting brewing parameters: {e}. Using fallback parameters.")
            
            # Create fallback parameters
            params = {
                'extraction_pressure': 7.0,
                'temperature': 93.0,
                'extraction_time': 30.0,
                'cup_size': self.cup_sizes.get(cup_size, self.cup_sizes['medium']),
                'ground_size': self.grind_size,
                'bean_type': 'arabica'
            }
            
            # Adjust dose size based on cup size
            params['dose_size'] = params['cup_size'] / self.default_ratio
            
            # Adjust temperature based on bitterness or maltiness
            if 'bitterness' in desired_flavor_profile:
                bitterness = desired_flavor_profile['bitterness']
                params['temperature'] = 87 + (bitterness - 1) * (95 - 87) / 9
            elif 'maltiness' in desired_flavor_profile:
                maltiness = desired_flavor_profile['maltiness']
                params['temperature'] = 87 + (maltiness - 1) * (95 - 87) / 9
                
            # Add bean blend if provided
            if bean_list and len(bean_list) > 0:
                bean_blend = {}
                equal_percent = 100 // len(bean_list)
                remainder = 100 % len(bean_list)
                
                for i, bean in enumerate(bean_list):
                    if i == 0:
                        bean_blend[bean] = equal_percent + remainder
                    else:
                        bean_blend[bean] = equal_percent
                
                params['bean_blend'] = bean_blend
            elif hasattr(self, 'available_beans') and self.available_beans:
                bean_list = self.available_beans[:3]  # Limit to first 3 beans
                bean_blend = {}
                equal_percent = 100 // len(bean_list)
                remainder = 100 % len(bean_list)
                
                for i, bean in enumerate(bean_list):
                    if i == 0:
                        bean_blend[bean] = equal_percent + remainder
                    else:
                        bean_blend[bean] = equal_percent
                
                params['bean_blend'] = bean_blend
            
            return params
    
    def _optimize_bean_blend(self, bean_list, desired_flavor_profile, fixed_params):
        """
        Optimize blend percentages for a list of beans to achieve desired flavor profile
        
        Parameters:
        -----------
        bean_list : list
            List of bean types to blend
        desired_flavor_profile : dict
            Desired values for flavor attributes
        fixed_params : dict
            Fixed brewing parameters
            
        Returns:
        --------
        blend : dict
            Optimized bean blend with percentages
        """
        if not bean_list or len(bean_list) == 0:
            return None
        
        # If only one bean type, return 100% of that bean
        if len(bean_list) == 1:
            return {bean_list[0]: 100}
        
        # Copy fixed params to avoid modifying the original
        base_params = fixed_params.copy()
        
        # Make sure we have all basic brewing parameters to avoid alignment errors
        required_params = ['extraction_pressure', 'temperature', 'extraction_time', 
                        'dose_size', 'cup_size', 'ground_size']
        
        # Fill in missing parameters with sensible defaults
        defaults = {
            'extraction_pressure': 7.0,  # bars
            'temperature': 93.0,         # Celsius
            'extraction_time': 30.0,     # seconds
            'dose_size': 20.0,           # grams
            'cup_size': 236.588,         # ml (medium)
            'ground_size': self.grind_size  # microns
        }
        
        for param in required_params:
            if param not in base_params:
                base_params[param] = defaults[param]
        
        # Initial blend with equal percentages
        n_beans = len(bean_list)
        initial_percentages = [100/n_beans] * (n_beans - 1)
        
        # Define constraints to ensure percentages sum to 100
        def percentage_constraint(x):
            return 100 - sum(x) - (100 - sum(x))
        
        constraints = [{'type': 'eq', 'fun': percentage_constraint}]
        
        # Define bounds (0-100 for each percentage)
        bounds = [(0, 100)] * (n_beans - 1)
        
        # Define the objective function
        def objective(percentages):
            try:
                # Construct the full list of percentages (last one is calculated)
                full_percentages = list(percentages) + [100 - sum(percentages)]
                
                # Create blend dictionary
                blend = {bean: perc for bean, perc in zip(bean_list, full_percentages) if perc > 0}
                
                # If any percentages are negative (can happen due to numerical issues), return high distance
                if any(p < 0 for p in full_percentages) or not blend:
                    return float('inf')
                
                # Get primary bean (highest percentage)
                primary_bean = max(blend.items(), key=lambda x: x[1])[0]
                
                # Set up parameters for prediction
                test_params = base_params.copy()
                test_params['bean_type'] = primary_bean
                test_params['bean_blend'] = blend
                
                # Predict flavor profile with this blend
                try:
                    # Temporarily convert to DataFrame for prediction
                    test_df = pd.DataFrame([test_params])
                    predictions = self.predict_flavor_profile(test_df)
                    
                    # Calculate distance to desired profile
                    distance = 0
                    for flavor, desired_val in desired_flavor_profile.items():
                        if flavor in predictions:
                            distance += (predictions[flavor] - desired_val) ** 2
                    
                    return np.sqrt(distance)
                except Exception as e:
                    print(f"Error in prediction during blend optimization: {e}")
                    return float('inf')
            except Exception as e:
                print(f"Error in objective function: {e}")
                return float('inf')
        
        # Run optimization with some error handling
        try:
            result = minimize(
                objective,
                initial_percentages,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 50, 'disp': False, 'ftol': 1e-6}
            )
            
            # Get optimized percentages
            optimized_percentages = list(result.x) + [100 - sum(result.x)]
            
            # Make sure we don't have NaN or invalid values
            if any(np.isnan(p) for p in optimized_percentages) or any(p < 0 for p in optimized_percentages):
                print("Blend optimization produced invalid values, using equal blend instead.")
                equal_percentages = [100.0 / len(bean_list)] * len(bean_list)
                blend = {bean: perc for bean, perc in zip(bean_list, equal_percentages)}
                return blend
            
            # Round percentages to integers and adjust to ensure they sum to 100
            rounded_percentages = [round(p) for p in optimized_percentages]
            
            # Adjust to make sure they sum to 100
            while sum(rounded_percentages) != 100:
                if sum(rounded_percentages) < 100:
                    # Add to the largest percentage
                    idx = rounded_percentages.index(max(rounded_percentages))
                    rounded_percentages[idx] += 1
                else:
                    # Subtract from the smallest non-zero percentage
                    non_zero = [i for i, p in enumerate(rounded_percentages) if p > 0]
                    if non_zero:
                        idx = min(non_zero, key=lambda i: rounded_percentages[i])
                        rounded_percentages[idx] -= 1
            
            # Create blend dictionary, excluding 0% components
            blend = {bean: perc for bean, perc in zip(bean_list, rounded_percentages) if perc > 0}
            
            return blend
        except Exception as e:
            print(f"Blend optimization failed: {e}")
            # Return an equal blend as fallback
            equal_percentages = [100.0 / len(bean_list)] * len(bean_list)
            rounded_percentages = [round(p) for p in equal_percentages]
            
            # Adjust to ensure they sum to 100
            delta = 100 - sum(rounded_percentages)
            if delta != 0:
                rounded_percentages[0] += delta
            
            blend = {bean: perc for bean, perc in zip(bean_list, rounded_percentages)}
            return blend
    
    def collect_brewing_data(self, brewing_params, flavor_ratings):
        """
        Collect and store data from a brewing session
        
        Parameters:
        -----------
        brewing_params : dict
            Parameters used for brewing
        flavor_ratings : dict
            User ratings for flavor profiles
            
        Returns:
        --------
        success : bool
            Whether data was successfully stored
        """
        # Combine brewing parameters and flavor ratings
        data = {**brewing_params, **flavor_ratings}
        
        # Add timestamp
        data['timestamp'] = pd.Timestamp.now()
        
        # Add fixed grind_size
        data['ground_size'] = self.grind_size
        
        # Handle bean blend if present
        if 'bean_blend' in data and isinstance(data['bean_blend'], dict):
            # Store blend info as a string for CSV storage
            data['blend_info'] = str(data['bean_blend'])
            
            # Use primary bean as bean_type
            if len(data['bean_blend']) > 0:
                data['bean_type'] = max(data['bean_blend'].items(), key=lambda x: x[1])[0]
            
            # Remove the dict to avoid serialization issues
            del data['bean_blend']
        
        # Create DataFrame
        df = pd.DataFrame([data])
        
        # Store data (append to existing or create new)
        csv_path = f"{self.data_path}/brewing_data.csv"
        if os.path.exists(csv_path):
            try:
                existing_df = pd.read_csv(csv_path)
                
                # Ensure consistent columns between existing data and new data
                all_columns = set(existing_df.columns).union(set(df.columns))
                
                # Add missing columns to both dataframes
                for col in all_columns:
                    if col not in existing_df.columns:
                        existing_df[col] = np.nan
                    if col not in df.columns:
                        df[col] = np.nan
                
                # Ensure column order is identical
                df = df[existing_df.columns]
                
                # Append to existing file
                df.to_csv(csv_path, mode='a', header=False, index=False)
            except Exception as e:
                print(f"Error appending to existing data: {e}")
                # If there's an error, create a new file
                df.to_csv(csv_path, index=False)
        else:
            df.to_csv(csv_path, index=False)
        
        return True
    
    def load_data(self, filter_conditions=None):
        """
        Load collected brewing data
        
        Parameters:
        -----------
        filter_conditions : dict, optional
            Conditions to filter data by (e.g., {'bean_type': 'arabica'})
            
        Returns:
        --------
        data : DataFrame
            Collected brewing data
        """
        csv_path = f"{self.data_path}/brewing_data.csv"
        if os.path.exists(csv_path):
            try:
                # Use on_bad_lines='skip' to skip problematic rows
                data = pd.read_csv(csv_path, on_bad_lines='skip')
                
                # Apply filters if specified
                if filter_conditions and isinstance(filter_conditions, dict):
                    for col, value in filter_conditions.items():
                        if col in data.columns:
                            data = data[data[col] == value]
                
                return data
            except Exception as e:
                print(f"Error loading data: {e}")
                # Return empty DataFrame with expected columns
                columns = self.feature_cols + self.target_cols + ['timestamp']
                return pd.DataFrame(columns=columns)
        else:
            # Return empty DataFrame with expected columns
            columns = self.feature_cols + self.target_cols + ['timestamp']
            return pd.DataFrame(columns=columns)
    
    def save_config(self, config_path=None):
        """
        Save model configuration for future reference
        
        Parameters:
        -----------
        config_path : str, optional
            Path to save configuration
            
        Returns:
        --------
        success : bool
            Whether configuration was successfully saved
        """
        config_path = config_path or f"{self.model_path}/config.json"
        
        config = {
            'feature_cols': self.feature_cols,
            'target_cols': self.target_cols,
            'numeric_cols': self.numeric_cols,
            'categorical_cols': self.categorical_cols,
            'data_path': self.data_path,
            'model_path': self.model_path,
            'cup_sizes': self.cup_sizes,
            'available_beans': self.available_beans,
            'default_ratio': self.default_ratio,
            'grind_size': self.grind_size,
            'has_quality_db': self.quality_db is not None
        }
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        return True
    
    def load_config(self, config_path=None):
        """
        Load model configuration
        
        Parameters:
        -----------
        config_path : str, optional
            Path to load configuration from
            
        Returns:
        --------
        success : bool
            Whether configuration was successfully loaded
        """
        config_path = config_path or f"{self.model_path}/config.json"
        
        if not os.path.exists(config_path):
            return False
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.feature_cols = config.get('feature_cols', self.feature_cols)
        self.target_cols = config.get('target_cols', self.target_cols)
        self.numeric_cols = config.get('numeric_cols', self.numeric_cols)
        self.categorical_cols = config.get('categorical_cols', self.categorical_cols)
        self.data_path = config.get('data_path', self.data_path)
        self.model_path = config.get('model_path', self.model_path)
        self.cup_sizes = config.get('cup_sizes', self.cup_sizes)
        self.available_beans = config.get('available_beans', self.available_beans)
        self.default_ratio = config.get('default_ratio', self.default_ratio)
        self.grind_size = config.get('grind_size', self.grind_size)
        
        # Update components with new configuration
        self.data_processor.update_config(
            feature_cols=self.feature_cols,
            target_cols=self.target_cols,
            numeric_cols=self.numeric_cols,
            categorical_cols=self.categorical_cols
        )
        
        self.model_trainer.update_config(
            feature_cols=self.feature_cols,
            target_cols=self.target_cols
        )
        
        self.flavor_predictor.update_config(
            feature_cols=self.feature_cols,
            target_cols=self.target_cols
        )
        
        self.parameter_optimizer.update_config(
            feature_cols=self.feature_cols,
            target_cols=self.target_cols,
            cup_sizes=self.cup_sizes,
            default_ratio=self.default_ratio,
            grind_size=self.grind_size
        )
        
        return True
    
    def analyze_feature_impact(self, feature, target, range_min=None, range_max=None, n_points=20):
        """
        Analyze the impact of a single feature on a target flavor profile
        
        Parameters:
        -----------
        feature : str
            Feature to analyze (e.g., 'temperature')
        target : str
            Target flavor attribute (e.g., 'acidity')
        range_min : float, optional
            Minimum value for feature
        range_max : float, optional
            Maximum value for feature
        n_points : int
            Number of points to evaluate
            
        Returns:
        --------
        impact_data : DataFrame
            Data showing feature values and corresponding predictions
        """
        return self.flavor_predictor.analyze_feature_impact(
            feature, target, range_min, range_max, n_points,
            self.data_processor, self.load_data()
        )
    
    def connect_to_supabase(self, url, key):
        """
        Setup connection to Supabase for data storage
        
        Parameters:
        -----------
        url : str
            Supabase URL
        key : str
            Supabase API key
            
        Returns:
        --------
        success : bool
            Whether connection was successfully established
        """
        self.supabase_url = url
        self.supabase_key = key
        self.headers = {
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json'
        }
        
        # Test connection
        try:
            response = requests.get(f"{url}/rest/v1/brewing_data?limit=1", headers=self.headers)
            return response.status_code == 200
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")
            return False
    
    def sync_with_supabase(self):
        """
        Sync local data with Supabase database
        
        Returns:
        --------
        success : bool
            Whether sync was successful
        """
        if not hasattr(self, 'supabase_url') or not hasattr(self, 'supabase_key'):
            print("Supabase connection not set up. Call connect_to_supabase first.")
            return False
        
        # Load local data
        local_data = self.load_data()
        
        if len(local_data) == 0:
            print("No local data to sync.")
            return True
        
        # Upload data to Supabase
        try:
            # Convert DataFrame to list of records
            records = local_data.to_dict(orient='records')
            
            # Upload in batches of 100
            batch_size = 100
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                response = requests.post(
                    f"{self.supabase_url}/rest/v1/brewing_data",
                    headers=self.headers,
                    json=batch
                )
                
                if response.status_code not in [200, 201]:
                    print(f"Error uploading batch {i//batch_size + 1}: {response.text}")
                    return False
            
            print(f"Successfully synced {len(records)} records to Supabase.")
            return True
        
        except Exception as e:
            print(f"Error syncing data: {e}")
            return False