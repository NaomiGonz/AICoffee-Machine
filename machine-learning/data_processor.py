import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
import joblib
import os

class DataProcessor:
    """
    Component for processing data for the AI Coffee Machine ML framework
    Handles preprocessing of brewing parameters and flavor profiles data
    """
    
    def __init__(self, feature_cols, target_cols, numeric_cols, categorical_cols, model_path):
        """
        Initialize the data processor
        
        Parameters:
        -----------
        feature_cols : list
            Columns to use as features
        target_cols : list
            Columns to use as targets
        numeric_cols : list
            Columns that are numeric
        categorical_cols : list
            Columns that are categorical
        model_path : str
            Path to store preprocessing objects
        """
        self.feature_cols = feature_cols
        self.target_cols = target_cols
        self.numeric_cols = numeric_cols
        self.categorical_cols = categorical_cols
        self.model_path = model_path
        
        self.scalers = {}
        self.categorical_encoders = {}
    
    def update_config(self, feature_cols=None, target_cols=None, numeric_cols=None, categorical_cols=None):
        """
        Update configuration parameters
        
        Parameters:
        -----------
        feature_cols : list, optional
            Columns to use as features
        target_cols : list, optional
            Columns to use as targets
        numeric_cols : list, optional
            Columns that are numeric
        categorical_cols : list, optional
            Columns that are categorical
        """
        if feature_cols is not None:
            self.feature_cols = feature_cols
        
        if target_cols is not None:
            self.target_cols = target_cols
        
        if numeric_cols is not None:
            self.numeric_cols = numeric_cols
        
        if categorical_cols is not None:
            self.categorical_cols = categorical_cols
    
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
        X : DataFrame
            Processed feature data
        y : DataFrame (only if training=True)
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
        available_features = [col for col in self.feature_cols if col in data.columns]
        X = data[available_features].copy()
        
        # Add flavor profile cluster if available
        if 'flavor_profile_cluster' in data.columns:
            X['flavor_profile_cluster'] = data['flavor_profile_cluster']
        
        # Process categorical features
        X = self._process_categorical_features(X, training)
        
        # Scale numerical features
        X = self._scale_numerical_features(X, training)
        
        # Return processed data
        if training:
            # Process targets for training
            y = data[self.target_cols].copy()
            return X, y
        else:
            return X
    
    def _process_categorical_features(self, X, training):
        """
        Process categorical features with one-hot encoding
        
        Parameters:
        -----------
        X : DataFrame
            Feature data
        training : bool
            Whether processing is for training
            
        Returns:
        --------
        X : DataFrame
            Processed feature data with categorical features encoded
        """
        X_processed = X.copy()
        
        # Find categorical columns that are actually in the data
        categorical_in_data = [col for col in self.categorical_cols if col in X.columns]
        
        # Process each categorical column
        for col in categorical_in_data:
            if training:
                # Fit and transform
                encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
                encoded_features = encoder.fit_transform(X[[col]])
                
                # Get feature names
                feature_names = [f"{col}_{val}" for val in encoder.categories_[0]]
                
                # Save encoder
                self.categorical_encoders[col] = {'encoder': encoder, 'feature_names': feature_names}
                
                # Save to disk
                joblib.dump(self.categorical_encoders[col], f"{self.model_path}/encoder_{col}.pkl")
                
            else:
                # Transform using existing encoder
                if col in self.categorical_encoders:
                    encoder = self.categorical_encoders[col]['encoder']
                    feature_names = self.categorical_encoders[col]['feature_names']
                else:
                    try:
                        # Try to load the encoder
                        encoder_info = joblib.load(f"{self.model_path}/encoder_{col}.pkl")
                        encoder = encoder_info['encoder']
                        feature_names = encoder_info['feature_names']
                        
                        # Cache for future use
                        self.categorical_encoders[col] = encoder_info
                    except (FileNotFoundError, KeyError) as e:
                        print(f"Error loading encoder for {col}: {e}")
                        raise ValueError(f"No encoder found for {col}. Train models first.")
                
                # Apply the transformation
                encoded_features = encoder.transform(X[[col]])
            
            # Create DataFrame with proper column names
            encoded_df = pd.DataFrame(
                encoded_features, 
                columns=feature_names, 
                index=X.index
            )
            
            # Remove original column and add encoded columns
            X_processed = X_processed.drop(columns=[col])
            X_processed = pd.concat([X_processed, encoded_df], axis=1)
        
        return X_processed
    
    def _scale_numerical_features(self, X, training):
        """
        Scale numerical features
        
        Parameters:
        -----------
        X : DataFrame
            Feature data
        training : bool
            Whether processing is for training
            
        Returns:
        --------
        X : DataFrame
            Processed feature data with numerical features scaled
        """
        X_processed = X.copy()
        
        # Find numerical columns that are actually in the data
        numeric_in_data = [col for col in self.numeric_cols if col in X.columns]
        
        # Extract numeric features
        if not numeric_in_data:
            return X_processed
            
        X_numeric = X[numeric_in_data]
        
        if training:
            # Fit and transform for each target
            for target in self.target_cols:
                scaler = StandardScaler()
                X_numeric_scaled = scaler.fit_transform(X_numeric)
                self.scalers[target] = scaler
                
                # Save scaler
                joblib.dump(scaler, f"{self.model_path}/scaler_{target}.pkl")
        else:
            # Use first target's scaler for prediction (they should be similar)
            target = self.target_cols[0]
            
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
            columns=numeric_in_data,
            index=X.index
        )
        
        for col in numeric_in_data:
            X_processed[col] = X_numeric_scaled_df[col]
        
        return X_processed