import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import os

class QualityDatabase:
    """
    Component for working with coffee quality database
    Handles loading, processing, and extracting insights from quality data
    """
    
    def __init__(self, quality_db_path):
        """
        Initialize the quality database
        
        Parameters:
        -----------
        quality_db_path : str
            Path to coffee quality database files
        """
        self.quality_db_path = quality_db_path
        self.quality_db = None
        self.quality_clusters = None
        self.bean_profile_pca = None
        
        # Column mappings
        self.extended_quality_cols = ['aroma', 'flavor', 'aftertaste', 'acidity', 
                                    'body', 'balance', 'uniformity', 'clean_cup', 
                                    'sweetness_score']
        
        self.bean_metadata_cols = ['processing_method', 'color', 'altitude_mean_meters', 
                                  'country_of_origin', 'region']
        
        # Load database if path is valid
        if quality_db_path and os.path.exists(quality_db_path):
            self.load_database()
    
    def load_database(self):
        """
        Load and process coffee quality database
        
        Returns:
        --------
        success : bool
            Whether the quality database was successfully loaded
        """
        if not self.quality_db_path:
            print("No quality database path provided.")
            return False
        
        try:
            # Try to load Arabica data
            arabica_path = os.path.join(self.quality_db_path, 'arabica_data_cleaned.csv')
            if os.path.exists(arabica_path):
                arabica_df = pd.read_csv(arabica_path)
                # Standardize column names
                arabica_df.columns = [col.lower().replace('.', '_') for col in arabica_df.columns]
                arabica_df = self._preprocess_quality_db(arabica_df, 'arabica')
            else:
                arabica_df = pd.DataFrame()
            
            # Try to load Robusta data
            robusta_path = os.path.join(self.quality_db_path, 'robusta_data_cleaned.csv')
            if os.path.exists(robusta_path):
                robusta_df = pd.read_csv(robusta_path)
                # Standardize column names
                robusta_df.columns = [col.lower().replace('.', '_') for col in robusta_df.columns]
                robusta_df = self._preprocess_quality_db(robusta_df, 'robusta')
            else:
                robusta_df = pd.DataFrame()
            
            # Combine datasets if both exist
            if not arabica_df.empty and not robusta_df.empty:
                # Ensure compatible columns exist in both datasets
                common_cols = set(arabica_df.columns).intersection(set(robusta_df.columns))
                self.quality_db = pd.concat([arabica_df[list(common_cols)], robusta_df[list(common_cols)]])
            elif not arabica_df.empty:
                self.quality_db = arabica_df
            elif not robusta_df.empty:
                self.quality_db = robusta_df
            else:
                print("No quality database files found.")
                return False
            
            # Create bean profiles using clustering
            self._create_bean_profiles()
            
            print(f"Successfully loaded quality database with {len(self.quality_db)} samples.")
            return True
        
        except Exception as e:
            print(f"Error loading quality database: {e}")
            return False
    
    def _preprocess_quality_db(self, df, bean_type):
        """
        Preprocess coffee quality database
        
        Parameters:
        -----------
        df : DataFrame
            Raw quality database
        bean_type : str
            Type of bean ('arabica' or 'robusta')
            
        Returns:
        --------
        df : DataFrame
            Preprocessed quality database
        """
        # Map column names to standardized names
        if bean_type == 'arabica':
            column_mapping = {
                'aroma': 'aroma',
                'flavor': 'flavor',
                'aftertaste': 'aftertaste',
                'acidity': 'acidity',
                'body': 'body',
                'balance': 'balance',
                'uniformity': 'uniformity',
                'clean_cup': 'clean_cup',
                'sweetness': 'sweetness_score',
                'processing_method': 'processing_method',
                'color': 'color',
                'country_of_origin': 'country_of_origin',
                'region': 'region',
                'altitude_mean_meters': 'altitude_mean_meters'
            }
        else:  # robusta
            column_mapping = {
                'fragrance___aroma': 'aroma',
                'flavor': 'flavor',
                'aftertaste': 'aftertaste',
                'salt___acid': 'acidity',
                'mouthfeel': 'body',
                'balance': 'balance',
                'uniform_cup': 'uniformity',
                'clean_cup': 'clean_cup',
                'bitter___sweet': 'sweetness_score',
                'processing_method': 'processing_method',
                'color': 'color',
                'country_of_origin': 'country_of_origin',
                'region': 'region',
                'altitude_mean_meters': 'altitude_mean_meters'
            }
        
        # Create standardized columns based on mapping
        for orig_col, std_col in column_mapping.items():
            if orig_col in df.columns:
                df[std_col] = df[orig_col]
        
        # Add bean_type column
        df['bean_type'] = bean_type
        
        # Fill missing values for critical columns
        for col in self.extended_quality_cols:
            if col in df.columns:
                df[col] = df[col].fillna(df[col].median())
        
        for col in self.bean_metadata_cols:
            if col in df.columns:
                if df[col].dtype in [np.float64, np.int64]:
                    df[col] = df[col].fillna(df[col].median())
                else:
                    df[col] = df[col].fillna('unknown')
        
        # Lowercase string columns for consistency
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.lower()
        
        return df
    
    def _create_bean_profiles(self):
        """
        Create bean profiles using clustering on quality database
        """
        if self.quality_db is None or len(self.quality_db) < 10:
            print("Quality database not loaded or too small for clustering.")
            return
        
        try:
            # Select relevant columns for clustering
            cluster_columns = [col for col in self.extended_quality_cols 
                              if col in self.quality_db.columns]
            
            if len(cluster_columns) < 3:
                print("Not enough quality attributes for clustering.")
                return
            
            # Prepare data for clustering
            cluster_data = self.quality_db[cluster_columns].copy()
            
            # Standardize data
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(cluster_data)
            
            # Determine optimal number of clusters (simplified)
            n_clusters = min(8, len(self.quality_db) // 10)  # Max 8 clusters or 1/10 of data points
            
            # Apply K-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            self.quality_db['flavor_profile_cluster'] = kmeans.fit_predict(scaled_data)
            
            # Store the clustering model
            self.quality_clusters = kmeans
            
            # Create a bean profile PCA for dimensionality reduction
            if len(cluster_columns) > 2:
                pca = PCA(n_components=2)
                pca.fit(scaled_data)
                self.bean_profile_pca = pca
            
            print(f"Created {n_clusters} bean profile clusters based on quality data.")
        
        except Exception as e:
            print(f"Error creating bean profiles: {e}")
    
    def get_bean_profile(self, bean_metadata):
        """
        Get flavor profile cluster for given bean metadata
        
        Parameters:
        -----------
        bean_metadata : dict
            Bean metadata (bean_type, processing_method, country_of_origin, etc.)
            
        Returns:
        --------
        profile_cluster : int
            Flavor profile cluster ID
        """
        if self.quality_db is None or self.quality_clusters is None:
            return None
        
        # Find similar beans in quality database
        query = []
        for key, value in bean_metadata.items():
            if key in self.quality_db.columns:
                query.append(f"{key} == '{value}'")
        
        query_str = ' & '.join(query)
        similar_beans = self.quality_db.query(query_str) if query else pd.DataFrame()
        
        if len(similar_beans) > 0:
            # Return most common cluster among similar beans
            return similar_beans['flavor_profile_cluster'].mode()[0]
        else:
            return None
    
    def enrich_data(self, data):
        """
        Enrich brewing data with information from quality database
        
        Parameters:
        -----------
        data : DataFrame
            Brewing data to enrich
            
        Returns:
        --------
        data : DataFrame
            Enriched brewing data
        """
        if self.quality_db is None:
            return data
        
        enriched_data = data.copy()
        
        # Add flavor profile cluster if we have bean metadata
        bean_metadata_cols = [col for col in self.bean_metadata_cols if col in data.columns]
        if 'bean_type' in data.columns and len(bean_metadata_cols) > 0:
            # For each row, find the most similar bean profile
            profile_clusters = []
            
            for _, row in data.iterrows():
                bean_metadata = {}
                for col in bean_metadata_cols:
                    if col in row and pd.notna(row[col]):
                        bean_metadata[col] = row[col]
                
                # Add bean type
                bean_metadata['bean_type'] = row['bean_type']
                
                # Get profile cluster
                cluster = self.get_bean_profile(bean_metadata)
                profile_clusters.append(cluster if cluster is not None else -1)
            
            enriched_data['flavor_profile_cluster'] = profile_clusters
            
            # If we couldn't find a cluster for some rows, use most common cluster
            if -1 in enriched_data['flavor_profile_cluster'].values:
                most_common_cluster = enriched_data['flavor_profile_cluster'][
                    enriched_data['flavor_profile_cluster'] != -1
                ].mode()
                
                if len(most_common_cluster) > 0:
                    replacement = most_common_cluster[0]
                else:
                    replacement = 0
                    
                enriched_data['flavor_profile_cluster'] = enriched_data['flavor_profile_cluster'].replace(-1, replacement)
        
        return enriched_data
    
    def get_cluster_insights(self, cluster_id):
        """
        Get insights about a specific flavor profile cluster
        
        Parameters:
        -----------
        cluster_id : int
            Cluster ID to get insights for
            
        Returns:
        --------
        insights : dict
            Dictionary of insights about the cluster
        """
        if self.quality_db is None or 'flavor_profile_cluster' not in self.quality_db.columns:
            return {}
        
        cluster_data = self.quality_db[self.quality_db['flavor_profile_cluster'] == cluster_id]
        
        if len(cluster_data) == 0:
            return {}
        
        insights = {}
        
        # Add average quality scores
        for col in self.extended_quality_cols:
            if col in cluster_data.columns:
                insights[f'expected_{col}'] = cluster_data[col].mean()
        
        # Add common metadata characteristics
        for col in self.bean_metadata_cols:
            if col in cluster_data.columns and cluster_data[col].dtype == 'object':
                # Get top 3 most common values
                top_values = cluster_data[col].value_counts().head(3)
                if len(top_values) > 0:
                    insights[f'common_{col}'] = [
                        value for value, count in top_values.items() 
                        if value != 'unknown'
                    ]
        
        # Add altitude information if available
        if 'altitude_mean_meters' in cluster_data.columns:
            insights['altitude_range'] = {
                'min': cluster_data['altitude_mean_meters'].min(),
                'max': cluster_data['altitude_mean_meters'].max(),
                'mean': cluster_data['altitude_mean_meters'].mean()
            }
        
        return insights
    
    def suggest_params_for_flavor(self, desired_flavor_profile, fixed_params=None):
        """
        Suggest starting brewing parameters based on desired flavor and quality database
        
        Parameters:
        -----------
        desired_flavor_profile : dict
            Desired flavor profile values
        fixed_params : dict, optional
            Fixed parameters that must be used
            
        Returns:
        --------
        suggested_params : dict
            Suggested brewing parameters based on quality database insights
        """
        if self.quality_db is None:
            return None
        
        # Default parameter mappings based on flavor attributes
        param_suggestions = {
            'extraction_pressure': {
                'acidity': 0.7,    # Higher pressure -> higher acidity
                'strength': 0.8,   # Higher pressure -> higher strength
                'body': 0.7,       # Higher pressure -> fuller body
                'sweetness': -0.3, # Lower pressure -> more sweetness
                'fruitiness': 0.2  # Slight positive correlation
            },
            'temperature': {
                'acidity': 0.8,    # Higher temp -> higher acidity
                'fruitiness': 0.6, # Higher temp -> more fruit notes
                'sweetness': -0.5, # Lower temp -> more sweetness
                'strength': 0.4,   # Higher temp -> more strength
                'maltiness': 0.7   # Higher temp -> more malt notes
            },
            'ground_size': {
                'acidity': -0.7,   # Finer grind -> more acidity
                'strength': -0.8,  # Finer grind -> more strength
                'body': -0.6,      # Finer grind -> fuller body
                'sweetness': 0.5,  # Coarser grind -> more sweetness
                'fruitiness': -0.2 # Slight negative correlation
            },
            'extraction_time': {
                'strength': 0.7,   # Longer time -> more strength
                'body': 0.6,       # Longer time -> fuller body
                'maltiness': 0.6,  # Longer time -> more malt notes
                'acidity': -0.4,   # Shorter time -> more acidity
                'fruitiness': -0.3 # Shorter time -> more fruitiness
            },
            'dose_size': {
                'strength': 0.8,   # More coffee -> stronger
                'body': 0.7,       # More coffee -> fuller body
                'maltiness': 0.5,  # More coffee -> more malt notes
                'sweetness': -0.3, # Less coffee -> more sweetness
                'fruitiness': -0.2 # Less coffee -> more fruitiness
            }
        }
        
        # Parameter ranges
        param_ranges = {
            'extraction_pressure': (1, 10),     # bars
            'temperature': (85, 96),            # Celsius
            'ground_size': (100, 1000),         # microns
            'extraction_time': (20, 40),        # seconds
            'dose_size': (15, 25)               # grams
        }
        
        # Start with default middle values
        suggested_params = {
            'extraction_pressure': 5.5,  # bars
            'temperature': 90.5,         # Celsius
            'ground_size': 550,          # microns
            'extraction_time': 30,       # seconds
            'dose_size': 20              # grams
        }
        
        # Apply fixed parameters
        if fixed_params:
            for param, value in fixed_params.items():
                if param in suggested_params:
                    suggested_params[param] = value
        
        # Adjust parameters based on desired flavor profile
        for param, correlations in param_suggestions.items():
            if param in fixed_params:
                continue  # Skip if parameter is fixed
                
            # Calculate adjustment factor
            adjustment = 0
            count = 0
            
            for flavor, correlation in correlations.items():
                if flavor in desired_flavor_profile:
                    # Normalize flavor to 0-1 scale (assuming 0-10 rating scale)
                    normalized_flavor = desired_flavor_profile[flavor] / 10.0
                    
                    # Calculate how much to move parameter based on correlation and desired flavor
                    # More weight to extreme values (0-2 or 8-10)
                    if normalized_flavor < 0.2:
                        weight = 2.0
                    elif normalized_flavor > 0.8:
                        weight = 2.0
                    else:
                        weight = 1.0
                        
                    adjustment += correlation * (normalized_flavor - 0.5) * weight
                    count += 1
            
            if count > 0:
                adjustment = adjustment / count
                
                # Apply adjustment to parameter
                min_val, max_val = param_ranges[param]
                range_size = max_val - min_val
                
                # Move parameter up to 40% of the range
                new_value = suggested_params[param] + (adjustment * range_size * 0.4)
                
                # Keep within valid range
                suggested_params[param] = max(min_val, min(max_val, new_value))
        
        # Round values appropriately
        suggested_params['extraction_pressure'] = round(suggested_params['extraction_pressure'], 2)
        suggested_params['temperature'] = round(suggested_params['temperature'], 1)
        suggested_params['ground_size'] = round(suggested_params['ground_size'])
        suggested_params['extraction_time'] = round(suggested_params['extraction_time'], 2)
        suggested_params['dose_size'] = round(suggested_params['dose_size'], 2)
        
        # Add categorical parameters if available
        if fixed_params and 'bean_type' in fixed_params:
            suggested_params['bean_type'] = fixed_params['bean_type']
        else:
            suggested_params['bean_type'] = 'arabica'  # Default to arabica
        
        return suggested_params