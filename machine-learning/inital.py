import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, MinMaxScaler, OneHotEncoder
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
import joblib
import json
import requests
import os

class CoffeeMachineLearning:
    """
    Machine Learning framework for AI Coffee Machine
    This class handles data collection, processing, model training, and prediction
    for optimizing coffee brewing parameters based on flavor profiles.
    """
    
    def __init__(self, data_path=None, model_path=None):
        """
        Initialize the ML framework with paths for data and model storage
        
        Parameters:
        -----------
        data_path : str
            Path to store collected data
        model_path : str
            Path to store trained models
        """
        self.data_path = data_path or 'data/'
        self.model_path = model_path or 'models/'
        self.feature_cols = ['extraction_pressure', 'temperature', 'ground_size', 
                           'extraction_time', 'dose_size', 'bean_type']
        self.target_cols = ['acidity', 'strength', 'sweetness', 'fruitiness', 'maltiness']
        self.models = {}
        self.scalers = {}
        self.categorical_encoders = {}
        self.numeric_cols = ['extraction_pressure', 'temperature', 'ground_size', 
                            'extraction_time', 'dose_size']
        self.categorical_cols = ['bean_type']
        
        # Ensure directories exist
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.model_path, exist_ok=True)
        
    def preprocess_data(self, data, training=True):
        """
        Preprocess brewing data for model training or prediction
        
        Parameters:
        -----------
        data : DataFrame
            Raw data containing brewing parameters and flavor profiles
        training : bool
            Whether preprocessing is for training (True) or prediction (False)
            
        Returns:
        --------
        X : DataFrame or numpy array
            Processed feature data
        y : DataFrame or numpy array (only if training=True)
            Processed target data
        """
        # Handle missing values
        data = data.copy()
        for col in self.feature_cols:
            if col in data.columns:
                # Fill missing numerical values with median, categorical with mode
                if data[col].dtype in [np.float64, np.int64]:
                    data[col] = data[col].fillna(data[col].median())
                else:
                    data[col] = data[col].fillna(data[col].mode()[0])
        
        # Extract features
        X = data[self.feature_cols].copy()
        
        # Separate numeric and categorical features
        X_numeric = X[self.numeric_cols].copy()
        
        # Process categorical features
        # During training, fit and transform
        if training:
            for col in self.categorical_cols:
                if col in X.columns:
                    encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
                    encoded_features = encoder.fit_transform(X[[col]])
                    
                    # Get feature names
                    feature_names = [f"{col}_{val}" for val in encoder.categories_[0]]
                    
                    # Save encoder
                    self.categorical_encoders[col] = {'encoder': encoder, 'feature_names': feature_names}
                    
                    # Create DataFrame with proper column names
                    encoded_df = pd.DataFrame(encoded_features, columns=feature_names, index=X.index)
                    
                    # Remove original column and add encoded columns
                    X = X.drop(columns=[col])
                    X = pd.concat([X, encoded_df], axis=1)
        
        # During prediction, transform using existing encoders
        else:
            for col in self.categorical_cols:
                if col in X.columns:
                    if col in self.categorical_encoders:
                        encoder = self.categorical_encoders[col]['encoder']
                        feature_names = self.categorical_encoders[col]['feature_names']
                        
                        encoded_features = encoder.transform(X[[col]])
                        encoded_df = pd.DataFrame(encoded_features, columns=feature_names, index=X.index)
                        
                        # Remove original column and add encoded columns
                        X = X.drop(columns=[col])
                        X = pd.concat([X, encoded_df], axis=1)
                    else:
                        try:
                            # Try to load the encoder
                            encoder_path = f"{self.model_path}/encoder_{col}.pkl"
                            encoder_info = joblib.load(encoder_path)
                            
                            encoder = encoder_info['encoder']
                            feature_names = encoder_info['feature_names']
                            
                            encoded_features = encoder.transform(X[[col]])
                            encoded_df = pd.DataFrame(encoded_features, columns=feature_names, index=X.index)
                            
                            # Remove original column and add encoded columns
                            X = X.drop(columns=[col])
                            X = pd.concat([X, encoded_df], axis=1)
                            
                            # Cache for future use
                            self.categorical_encoders[col] = {'encoder': encoder, 'feature_names': feature_names}
                        except (FileNotFoundError, KeyError) as e:
                            print(f"Error loading encoder for {col}: {e}")
                            raise ValueError(f"No encoder found for {col}. Train models first.")
        
        # Scale numerical features
        X_numeric = X[self.numeric_cols].copy()
        
        if training:
            for target in self.target_cols:
                scaler = StandardScaler()
                X_numeric_scaled = scaler.fit_transform(X_numeric)
                self.scalers[target] = scaler
                
                # Save scaler
                joblib.dump(scaler, f"{self.model_path}/scaler_{target}.pkl")
        else:
            for target in self.target_cols:
                if target in self.scalers:
                    scaler = self.scalers[target]
                else:
                    try:
                        scaler = joblib.load(f"{self.model_path}/scaler_{target}.pkl")
                        self.scalers[target] = scaler
                    except FileNotFoundError:
                        print(f"Error: No scaler found for {target}. Train models first.")
                        raise ValueError(f"No scaler found for {target}. Train models first.")
                
                X_numeric_scaled = scaler.transform(X_numeric)
        
        # Replace original numeric columns with scaled versions
        X_numeric_scaled_df = pd.DataFrame(
            X_numeric_scaled, 
            columns=self.numeric_cols,
            index=X.index
        )
        
        for col in self.numeric_cols:
            X[col] = X_numeric_scaled_df[col]
        
        # Save all categorical encoders during training
        if training:
            for col, encoder_info in self.categorical_encoders.items():
                joblib.dump(encoder_info, f"{self.model_path}/encoder_{col}.pkl")
        
        # Return processed data
        if training:
            # Process targets for training
            y = data[self.target_cols].copy()
            return X, y
        else:
            return X
    
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
        X, y = self.preprocess_data(data, training=True)
        
        # Split data into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        metrics = {}
        
        # Train a model for each flavor profile
        for target in self.target_cols:
            print(f"Training model for {target}...")
            
            # Try different models and select the best one
            models = {
                'linear': LinearRegression(),
                'random_forest': RandomForestRegressor(random_state=random_state),
                'gradient_boosting': GradientBoostingRegressor(random_state=random_state)
            }
            
            best_model = None
            best_score = -float('inf')
            best_model_name = None
            
            for name, model in models.items():
                model.fit(X_train, y_train[target])
                score = cross_val_score(model, X_train, y_train[target], cv=5, scoring='neg_mean_squared_error').mean()
                
                if score > best_score:
                    best_score = score
                    best_model = model
                    best_model_name = name
            
            # Train the best model on all training data
            best_model.fit(X_train, y_train[target])
            self.models[target] = best_model
            
            # Save model
            joblib.dump(best_model, f"{self.model_path}/model_{target}.pkl")
            
            # Evaluate on test set
            y_pred = best_model.predict(X_test)
            mse = mean_squared_error(y_test[target], y_pred)
            mae = mean_absolute_error(y_test[target], y_pred)
            r2 = r2_score(y_test[target], y_pred)
            
            metrics[target] = {
                'model_type': best_model_name,
                'mse': mse,
                'mae': mae,
                'r2': r2
            }
            
            print(f"  {target} - Model: {best_model_name}, MSE: {mse:.4f}, MAE: {mae:.4f}, R²: {r2:.4f}")
            
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
        
        # Make sure all required columns exist
        for col in self.feature_cols:
            if col not in brewing_params.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Preprocess the input data
        X = self.preprocess_data(brewing_params, training=False)
        
        # Make predictions for each flavor attribute
        predictions = {}
        for target in self.target_cols:
            if target in self.models:
                model = self.models[target]
            else:
                try:
                    model = joblib.load(f"{self.model_path}/model_{target}.pkl")
                    self.models[target] = model
                except FileNotFoundError:
                    raise ValueError(f"No model found for {target}. Train models first.")
            
            predictions[target] = model.predict(X)[0]
        
        return predictions
    
    def suggest_brewing_parameters(self, desired_flavor_profile, bean_type=None):
        """
        Suggest brewing parameters to achieve a desired flavor profile
        This is the inverse problem - using optimization to find brewing parameters
        
        Parameters:
        -----------
        desired_flavor_profile : dict
            Desired values for flavor attributes
        bean_type : str, optional
            Specific bean type to use
            
        Returns:
        --------
        suggested_params : dict
            Suggested brewing parameters
        """
        # This is a simplified implementation using grid search
        # A more sophisticated approach would use Bayesian optimization
        
        # Define parameter ranges
        param_ranges = {
            'extraction_pressure': np.linspace(1, 10, 10),  # bars
            'temperature': np.linspace(85, 96, 12),  # Celsius
            'ground_size': np.linspace(100, 1000, 10),  # microns
            'extraction_time': np.linspace(20, 40, 10),  # seconds
            'dose_size': np.linspace(15, 25, 10)  # grams
        }
        
        # Fix bean type if specified
        if bean_type:
            fixed_params = {'bean_type': bean_type}
        else:
            fixed_params = {}
        
        # Create a grid of parameter combinations (limited for computational feasibility)
        # In practice, we'd use a more efficient optimization approach
        grid_size = 1000
        params_grid = []
        
        for _ in range(grid_size):
            params = {
                'extraction_pressure': np.random.choice(param_ranges['extraction_pressure']),
                'temperature': np.random.choice(param_ranges['temperature']),
                'ground_size': np.random.choice(param_ranges['ground_size']),
                'extraction_time': np.random.choice(param_ranges['extraction_time']),
                'dose_size': np.random.choice(param_ranges['dose_size']),
            }
            params.update(fixed_params)
            params_grid.append(params)
        
        # Convert to DataFrame for batch prediction
        grid_df = pd.DataFrame(params_grid)
        
        # If bean type is not specified, use the first available one
        if 'bean_type' not in grid_df.columns:
            # Try to find all available bean types from encoders
            if 'bean_type' in self.categorical_encoders:
                encoder = self.categorical_encoders['bean_type']['encoder']
                available_bean_types = encoder.categories_[0]
                if len(available_bean_types) > 0:
                    grid_df['bean_type'] = available_bean_types[0]
                else:
                    grid_df['bean_type'] = 'arabica'  # Default fallback
            else:
                grid_df['bean_type'] = 'arabica'  # Default fallback
        
        # Predict flavor profiles for all parameter combinations
        best_params = None
        best_distance = float('inf')
        
        for i in range(0, len(grid_df), 100):  # Process in batches
            batch = grid_df.iloc[i:i+100].copy()
            
            try:
                # Preprocess batch
                X_batch = self.preprocess_data(batch, training=False)
                
                # Calculate distance to desired flavor profile for each combination
                distances = []
                
                for j in range(len(batch)):
                    X_single = X_batch.iloc[j:j+1]
                    pred_profile = {}
                    
                    for target in self.target_cols:
                        if target in self.models:
                            model = self.models[target]
                        else:
                            model = joblib.load(f"{self.model_path}/model_{target}.pkl")
                        
                        pred_profile[target] = model.predict(X_single)[0]
                    
                    # Calculate Euclidean distance to desired profile
                    distance = 0
                    for target, desired_val in desired_flavor_profile.items():
                        if target in pred_profile:
                            distance += (pred_profile[target] - desired_val) ** 2
                    
                    distance = np.sqrt(distance)
                    distances.append(distance)
                
                # Find best parameters in this batch
                batch_best_idx = np.argmin(distances)
                if distances[batch_best_idx] < best_distance:
                    best_distance = distances[batch_best_idx]
                    best_params = batch.iloc[batch_best_idx].to_dict()
            
            except Exception as e:
                print(f"Error processing batch {i//100}: {e}")
                continue
        
        if best_params is None:
            raise ValueError("Failed to find suitable brewing parameters. Try different flavor targets.")
        
        return best_params
    
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
            existing_df = pd.read_csv(csv_path)
            # Check if columns match
            if set(existing_df.columns) != set(df.columns):
                # Add missing columns with NaN values
                for col in existing_df.columns:
                    if col not in df.columns:
                        df[col] = np.nan
                for col in df.columns:
                    if col not in existing_df.columns:
                        existing_df[col] = np.nan
            
            # Ensure column order matches
            df = df[existing_df.columns]
            df.to_csv(csv_path, mode='a', header=False, index=False)
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
            data = pd.read_csv(csv_path)
            
            # Apply filters if specified
            if filter_conditions and isinstance(filter_conditions, dict):
                for col, value in filter_conditions.items():
                    if col in data.columns:
                        data = data[data[col] == value]
            
            return data
        else:
            # Return empty DataFrame with expected columns
            columns = self.feature_cols + self.target_cols + ['timestamp']
            return pd.DataFrame(columns=columns)
    
    def evaluate_models(self, plot=True):
        """
        Evaluate model performance and generate reports
        
        Parameters:
        -----------
        plot : bool
            Whether to generate and save plots
            
        Returns:
        --------
        metrics : dict
            Model performance metrics
        """
        # Load data
        data = self.load_data()
        
        if len(data) < 10:
            print("Not enough data to evaluate models. Need at least 10 samples.")
            return None
        
        # Process data
        X, y = self.preprocess_data(data, training=True)
        
        # Split data into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        metrics = {}
        feature_importance = {}
        
        for target in self.target_cols:
            # Load model
            model_path = f"{self.model_path}/model_{target}.pkl"
            if not os.path.exists(model_path):
                print(f"No model found for {target}")
                continue
            
            model = joblib.load(model_path)
            
            # Make predictions
            y_pred = model.predict(X_test)
            
            # Calculate metrics
            mse = mean_squared_error(y_test[target], y_pred)
            mae = mean_absolute_error(y_test[target], y_pred)
            r2 = r2_score(y_test[target], y_pred)
            
            metrics[target] = {
                'mse': mse,
                'mae': mae,
                'r2': r2
            }
            
            # Generate feature importance if available
            if hasattr(model, 'feature_importances_'):
                feature_importance[target] = {
                    'importances': model.feature_importances_,
                    'features': X.columns.tolist()
                }
            
            # Generate plots
            if plot:
                plt.figure(figsize=(12, 5))
                
                # Predictions vs actual
                plt.subplot(1, 2, 1)
                plt.scatter(y_test[target], y_pred, alpha=0.5)
                plt.plot([y_test[target].min(), y_test[target].max()], 
                         [y_test[target].min(), y_test[target].max()], 'r--')
                plt.xlabel('Actual')
                plt.ylabel('Predicted')
                plt.title(f'{target} - Predictions vs Actual (R² = {r2:.4f})')
                
                # Feature importance
                if hasattr(model, 'feature_importances_'):
                    plt.subplot(1, 2, 2)
                    features = X.columns.tolist()
                    importances = model.feature_importances_
                    
                    if len(features) == len(importances):
                        indices = np.argsort(importances)
                        plt.barh(range(len(indices)), importances[indices])
                        plt.yticks(range(len(indices)), [features[i] for i in indices])
                        plt.xlabel('Feature Importance')
                        plt.title(f'{target} - Feature Importance')
                    else:
                        print(f"Warning: Feature count mismatch for {target}. Cannot plot importance.")
                
                plt.tight_layout()
                plt.savefig(f"{self.data_path}/{target}_evaluation.png")
                plt.close()
        
        return metrics
    
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
        if feature not in self.feature_cols:
            raise ValueError(f"Feature '{feature}' not found in feature columns")
        
        if target not in self.target_cols:
            raise ValueError(f"Target '{target}' not found in target columns")
        
        # Load a sample data point as a baseline
        data = self.load_data()
        if len(data) == 0:
            # Create a default data point
            baseline = {}
            for col in self.numeric_cols:
                baseline[col] = 0.5  # Normalized middle value
            baseline['bean_type'] = 'arabica'  # Default bean type
        else:
            # Use the mean of numeric features and mode of categorical features
            baseline = {}
            for col in self.numeric_cols:
                baseline[col] = data[col].mean()
            for col in self.categorical_cols:
                baseline[col] = data[col].mode()[0]
        
        # Define range for feature
        if feature in self.numeric_cols:
            if range_min is None or range_max is None:
                # Use reasonable defaults based on feature
                if feature == 'extraction_pressure':
                    range_min, range_max = 1, 10  # bars
                elif feature == 'temperature':
                    range_min, range_max = 85, 96  # Celsius
                elif feature == 'ground_size':
                    range_min, range_max = 100, 1000  # microns
                elif feature == 'extraction_time':
                    range_min, range_max = 20, 40  # seconds
                elif feature == 'dose_size':
                    range_min, range_max = 15, 25  # grams
                else:
                    range_min, range_max = 0, 1  # normalized
            
            feature_values = np.linspace(range_min, range_max, n_points)
            
            # Prepare data points
            test_points = []
            for val in feature_values:
                point = baseline.copy()
                point[feature] = val
                test_points.append(point)
            
            # Convert to DataFrame
            test_df = pd.DataFrame(test_points)
            
        else:  # Categorical feature
            # For categorical features, we'll try all possible values
            if 'bean_type' in self.categorical_encoders:
                feature_values = self.categorical_encoders['bean_type']['encoder'].categories_[0]
            else:
                feature_values = ['arabica', 'robusta', 'blend']  # Default values
            
            # Prepare data points
            test_points = []
            for val in feature_values:
                point = baseline.copy()
                point[feature] = val
                test_points.append(point)
            
            # Convert to DataFrame
            test_df = pd.DataFrame(test_points)
        
        # Make predictions
        predictions = []
        for _, row in test_df.iterrows():
            try:
                pred = self.predict_flavor_profile(row.to_dict())
                predictions.append(pred[target])
            except Exception as e:
                print(f"Error predicting for {feature}={row[feature]}: {e}")
                predictions.append(np.nan)
        
        # Create result DataFrame
        result = pd.DataFrame({
            'feature_value': feature_values,
            'predicted_' + target: predictions
        })
        
        return result
    
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
            'models': {target: str(type(model)) for target, model in self.models.items()},
            'data_path': self.data_path,
            'model_path': self.model_path,
            'numeric_cols': self.numeric_cols,
            'categorical_cols': self.categorical_cols
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
            print(f"No configuration found at {config_path}")
            return False
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.feature_cols = config['feature_cols']
        self.target_cols = config['target_cols']
        self.data_path = config['data_path']
        self.model_path = config['model_path']
        
        if 'numeric_cols' in config:
            self.numeric_cols = config['numeric_cols']
        
        if 'categorical_cols' in config:
            self.categorical_cols = config['categorical_cols']
        
        # Load models
        for target in self.target_cols:
            model_path = f"{self.model_path}/model_{target}.pkl"
            if os.path.exists(model_path):
                self.models[target] = joblib.load(model_path)
        
        # Load encoders
        for col in self.categorical_cols:
            encoder_path = f"{self.model_path}/encoder_{col}.pkl"
            if os.path.exists(encoder_path):
                self.categorical_encoders[col] = joblib.load(encoder_path)
        
        # Load scalers
        for target in self.target_cols:
            scaler_path = f"{self.model_path}/scaler_{target}.pkl"
            if os.path.exists(scaler_path):
                self.scalers[target] = joblib.load(scaler_path)
        
        return True
    
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

# Example usage
if __name__ == "__main__":
    # Create ML framework instance
    ml = CoffeeMachineLearning()
    
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
    data.to_csv('data/synthetic_brewing_data.csv', index=False)
    
    print("Synthetic data generated for testing.")
    print("To train models: ml.train_models(data)")
    print("To predict flavor profile: ml.predict_flavor_profile(brewing_params)")
    print("To suggest brewing parameters: ml.suggest_brewing_parameters(desired_flavor_profile)")