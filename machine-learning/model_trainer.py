import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import joblib
import os

class ModelTrainer:
    """
    Component for training machine learning models for the AI Coffee Machine
    Handles model selection, training, and evaluation
    """
    
    def __init__(self, feature_cols, target_cols, model_path):
        """
        Initialize the model trainer
        
        Parameters:
        -----------
        feature_cols : list
            Columns to use as features
        target_cols : list
            Columns to use as targets
        model_path : str
            Path to store trained models
        """
        self.feature_cols = feature_cols
        self.target_cols = target_cols
        self.model_path = model_path
        self.models = {}
        self.metrics = {}
    
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
    
    def train_models(self, X, y, test_size=0.2, random_state=42):
        """
        Train models for predicting flavor profiles from brewing parameters
        
        Parameters:
        -----------
        X : DataFrame
            Processed feature data
        y : DataFrame
            Target data (flavor profiles)
        test_size : float
            Proportion of data to use for testing
        random_state : int
            Random seed for reproducibility
            
        Returns:
        --------
        metrics : dict
            Performance metrics for each model
        """
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
            
            # Find the best model through cross-validation
            for name, model in models.items():
                model.fit(X_train, y_train[target])
                score = cross_val_score(
                    model, X_train, y_train[target], 
                    cv=5, scoring='neg_mean_squared_error'
                ).mean()
                
                if score > best_score:
                    best_score = score
                    best_model = model
                    best_model_name = name
            
            # Train the best model on all training data
            best_model.fit(X_train, y_train[target])
            self.models[target] = best_model
            
            # Save model
            joblib.dump(best_model, f"{self.model_path}/model_{target}.pkl")
            
            # Save model type
            with open(f"{self.model_path}/model_{target}_type.txt", 'w') as f:
                f.write(best_model_name)
            
            # Evaluate on test set
            y_pred = best_model.predict(X_test)
            mse = mean_squared_error(y_test[target], y_pred)
            mae = mean_absolute_error(y_test[target], y_pred)
            r2 = r2_score(y_test[target], y_pred)
            
            # Calculate feature importance if available
            feature_importance = None
            if hasattr(best_model, 'feature_importances_'):
                feature_importance = dict(zip(X.columns, best_model.feature_importances_))
            
            metrics[target] = {
                'model_type': best_model_name,
                'mse': mse,
                'mae': mae,
                'r2': r2,
                'feature_importance': feature_importance
            }
            
            print(f"  {target} - Model: {best_model_name}, MSE: {mse:.4f}, MAE: {mae:.4f}, R²: {r2:.4f}")
        
        self.metrics = metrics
        return metrics
    
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
    
    def generate_model_summary(self):
        """
        Generate a summary of the trained models
        
        Returns:
        --------
        summary : dict
            Summary of model performance and characteristics
        """
        if not self.metrics:
            if not self.load_models():
                return {"error": "No trained models found"}
        
        summary = {
            "models": {},
            "overall": {
                "average_r2": 0,
                "best_performing_target": "",
                "worst_performing_target": ""
            }
        }
        
        # Summarize each model
        best_r2 = -float('inf')
        worst_r2 = float('inf')
        total_r2 = 0
        
        for target, metric in self.metrics.items():
            r2 = metric['r2']
            total_r2 += r2
            
            # Track best and worst
            if r2 > best_r2:
                best_r2 = r2
                summary["overall"]["best_performing_target"] = target
            
            if r2 < worst_r2:
                worst_r2 = r2
                summary["overall"]["worst_performing_target"] = target
            
            # Add model details
            summary["models"][target] = {
                "model_type": metric['model_type'],
                "r2_score": metric['r2'],
                "mean_squared_error": metric['mse'],
                "mean_absolute_error": metric['mae']
            }
            
            # Add feature importance if available
            if metric.get('feature_importance'):
                # Get top 5 features
                top_features = dict(sorted(
                    metric['feature_importance'].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:5])
                
                summary["models"][target]["top_features"] = top_features
        
        # Calculate average R²
        if self.metrics:
            summary["overall"]["average_r2"] = total_r2 / len(self.metrics)
        
        return summary