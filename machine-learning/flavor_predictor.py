import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
import os

class FlavorPredictor:
    """
    Component for predicting flavor profiles based on brewing parameters
    Handles loading models and making predictions
    """
    
    def __init__(self, feature_cols, target_cols, model_path):
        """
        Initialize the flavor predictor
        
        Parameters:
        -----------
        feature_cols : list
            Columns to use as features
        target_cols : list
            Columns to use as targets
        model_path : str
            Path to load trained models from
        """
        self.feature_cols = feature_cols
        self.target_cols = target_cols
        self.model_path = model_path
        self.models = {}
    
    def update_config(self, feature_cols=None, target_cols=None):
        """
        Update configuration parameters
        
        Parameters:
        -----------
        feature_cols : list, optional
            Columns to use as features
        target_cols : list, optional
            Columns to use as targets
        """
        if feature_cols is not None:
            self.feature_cols = feature_cols
        
        if target_cols is not None:
            self.target_cols = target_cols
    
    def load_models(self):
        """
        Load trained models from disk
        
        Returns:
        --------
        success : bool
            Whether models were successfully loaded
        """
        success = True
        
        for target in self.target_cols:
            model_path = f"{self.model_path}/model_{target}.pkl"
            
            if os.path.exists(model_path):
                try:
                    self.models[target] = joblib.load(model_path)
                except Exception as e:
                    print(f"Error loading model for {target}: {e}")
                    success = False
            else:
                print(f"Model for {target} not found at {model_path}")
                success = False
        
        return success
    
    def predict(self, X):
        """
        Predict flavor profiles for the given brewing parameters
        
        Parameters:
        -----------
        X : DataFrame
            Processed brewing parameters
            
        Returns:
        --------
        predictions : dict
            Predicted flavor profile values
        """
        # Ensure models are loaded
        if not self.models:
            self.load_models()
        
        predictions = {}
        
        for target in self.target_cols:
            if target in self.models:
                model = self.models[target]
                
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
                    self.models[target] = model
                    
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
                except FileNotFoundError:
                    raise ValueError(f"No model found for {target}. Train models first.")
        
        return predictions
    
    def analyze_feature_impact(self, feature, target, range_min=None, range_max=None, 
                              n_points=20, data_processor=None, sample_data=None):
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
        data_processor : DataProcessor
            Data processor component for preprocessing
        sample_data : DataFrame
            Sample data to use as baseline
            
        Returns:
        --------
        impact_data : DataFrame
            Data showing feature values and corresponding predictions
        """
        if feature not in self.feature_cols:
            raise ValueError(f"Feature '{feature}' not found in feature columns")
        
        if target not in self.target_cols:
            raise ValueError(f"Target '{target}' not found in target columns")
        
        # Ensure models are loaded
        if not self.models:
            self.load_models()
            
        if target not in self.models:
            raise ValueError(f"No model found for {target}. Train models first.")
        
        # Create a baseline data point or use sample data
        if sample_data is None or len(sample_data) == 0:
            # Create a default data point
            baseline = {}
            for col in self.feature_cols:
                if col == 'bean_type':
                    baseline[col] = 'arabica'
                elif col in ['processing_method', 'color', 'country_of_origin', 'region']:
                    baseline[col] = 'unknown'
                else:
                    baseline[col] = 0.5  # Normalized middle value
            
            # Add flavor_profile_cluster if the model needs it
            model = self.models[target]
            if hasattr(model, 'feature_names_in_') and 'flavor_profile_cluster' in model.feature_names_in_:
                baseline['flavor_profile_cluster'] = 0
                
            baseline_df = pd.DataFrame([baseline])
        else:
            # Use the mean/mode of sample data
            baseline = {}
            for col in self.feature_cols:
                if col in sample_data.columns:
                    if sample_data[col].dtype in [np.float64, np.int64]:
                        baseline[col] = sample_data[col].mean()
                    else:
                        baseline[col] = sample_data[col].mode()[0]
                elif col == 'bean_type':
                    baseline[col] = 'arabica'
                else:
                    baseline[col] = 0.5
            
            # Add flavor_profile_cluster if needed
            model = self.models[target]
            if hasattr(model, 'feature_names_in_') and 'flavor_profile_cluster' in model.feature_names_in_:
                baseline['flavor_profile_cluster'] = 0
                
            baseline_df = pd.DataFrame([baseline])
        
        # Define range for feature
        if feature in ['extraction_pressure', 'temperature', 'ground_size', 
                     'extraction_time', 'dose_size']:
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
            if feature == 'bean_type':
                feature_values = ['arabica', 'robusta', 'blend']
            elif feature == 'processing_method':
                feature_values = ['washed', 'natural', 'honey', 'pulped natural', 'unknown']
            elif feature == 'color':
                feature_values = ['green', 'blue-green', 'yellow', 'unknown']
            elif feature == 'country_of_origin':
                # Limit to major coffee producing countries
                feature_values = ['ethiopia', 'colombia', 'brazil', 'costa rica', 
                                'guatemala', 'kenya', 'rwanda', 'unknown']
            else:
                feature_values = ['unknown']
            
            # Prepare data points
            test_points = []
            for val in feature_values:
                point = baseline.copy()
                point[feature] = val
                test_points.append(point)
            
            # Convert to DataFrame
            test_df = pd.DataFrame(test_points)
        
        # Preprocess test data
        if data_processor:
            try:
                X_test = data_processor.preprocess_data(test_df, training=False)
            except Exception as e:
                print(f"Error preprocessing data: {e}")
                X_test = test_df
        else:
            X_test = test_df
        
        # Make predictions
        predictions = []
        for i in range(len(X_test)):
            try:
                X_single = X_test.iloc[[i]]
                
                # Ensure feature alignment
                model = self.models[target]
                if hasattr(model, 'feature_names_in_'):
                    X_aligned = pd.DataFrame(index=X_single.index)
                    for feature_name in model.feature_names_in_:
                        if feature_name in X_single.columns:
                            X_aligned[feature_name] = X_single[feature_name]
                        else:
                            X_aligned[feature_name] = 0
                    
                    pred = model.predict(X_aligned)[0]
                else:
                    pred = model.predict(X_single)[0]
                
                predictions.append(pred)
            except Exception as e:
                print(f"Error predicting for {feature}={test_df.iloc[i][feature]}: {e}")
                predictions.append(np.nan)
        
        # Create result DataFrame
        result = pd.DataFrame({
            'feature_value': feature_values,
            f'predicted_{target}': predictions
        })
        
        return result
    
    def plot_feature_impact(self, feature_impact_data, feature, target, title=None):
        """
        Plot the impact of a feature on a target flavor profile
        
        Parameters:
        -----------
        feature_impact_data : DataFrame
            Data from analyze_feature_impact method
        feature : str
            Feature name
        target : str
            Target name
        title : str, optional
            Plot title
            
        Returns:
        --------
        fig : matplotlib Figure
            The generated figure
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        feature_impact_data.plot(
            x='feature_value', 
            y=f'predicted_{target}',
            kind='line',
            marker='o',
            ax=ax
        )
        
        # Set labels and title
        ax.set_xlabel(feature.capitalize())
        ax.set_ylabel(f'Predicted {target.capitalize()}')
        
        if title:
            ax.set_title(title)
        else:
            ax.set_title(f'Impact of {feature.capitalize()} on {target.capitalize()}')
        
        # Set y-axis to reasonable range (0-10 for flavor attributes)
        if target in ['acidity', 'strength', 'sweetness', 'fruitiness', 'maltiness']:
            ax.set_ylim(0, 10)
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        return fig