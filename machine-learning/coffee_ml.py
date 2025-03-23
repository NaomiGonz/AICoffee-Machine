import numpy as np
import pandas as pd
import os
import joblib
import json
import requests

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
        
        # Core brewing parameters
        self.feature_cols = ['extraction_pressure', 'temperature', 'ground_size', 
                           'extraction_time', 'dose_size', 'bean_type']
        
        # Core flavor profiles
        self.target_cols = ['acidity', 'strength', 'sweetness', 'fruitiness', 'maltiness']
        
        # Column types
        self.numeric_cols = ['extraction_pressure', 'temperature', 'ground_size', 
                            'extraction_time', 'dose_size']
        self.categorical_cols = ['bean_type', 'processing_method', 'color', 
                                'country_of_origin', 'region']
        
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
            flavor_predictor=self.flavor_predictor
        )
        
        # Load configuration if exists
        self.load_config()
    
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
    
    def suggest_brewing_parameters(self, desired_flavor_profile, bean_type=None, processing_method=None, country=None):
        """
        Suggest brewing parameters to achieve a desired flavor profile
        
        Parameters:
        -----------
        desired_flavor_profile : dict
            Desired values for flavor attributes
        bean_type : str, optional
            Specific bean type to use
        processing_method : str, optional
            Specific processing method to use
        country : str, optional
            Specific country of origin to use
            
        Returns:
        --------
        suggested_params : dict
            Suggested brewing parameters
        """
        # Fix categorical values if specified
        fixed_params = {}
        if bean_type:
            fixed_params['bean_type'] = bean_type
        if processing_method:
            fixed_params['processing_method'] = processing_method
        if country:
            fixed_params['country_of_origin'] = country
        
        # Get starting recommendations from quality database
        starting_params = None
        if self.quality_db:
            starting_params = self.quality_db.suggest_params_for_flavor(desired_flavor_profile, fixed_params)
        
        # Optimize parameters
        return self.parameter_optimizer.optimize(
            desired_flavor_profile, 
            fixed_params=fixed_params, 
            starting_params=starting_params
        )
    
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
            target_cols=self.target_cols
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