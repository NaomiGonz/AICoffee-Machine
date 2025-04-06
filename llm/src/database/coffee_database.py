import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

class CoffeeDatabase:
    """
    Comprehensive coffee database loader and analyzer using open-source CSV data.
    """
    def __init__(
        self, 
        data_dir: Optional[str] = None, 
        arabica_filename: str = 'arabica_data_cleaned.csv', 
        robusta_filename: str = 'robusta_data_cleaned.csv'
    ):
        """
        Initialize the database by loading both Arabica and Robusta datasets.
        
        Args:
            data_dir (str, optional): Directory containing the CSV files
            arabica_filename (str): Filename for Arabica coffee dataset
            robusta_filename (str): Filename for Robusta coffee dataset
        """
        # Define flavor mapping
        self.flavor_profile_mapping = {
            # Core flavor profiles
            'fruity': ['fruity', 'berry', 'citrus', 'bright', 'apple', 'peach', 'cherry', 'tropical'],
            'chocolatey': ['chocolate', 'cocoa', 'rich', 'dark chocolate', 'mocha'],
            'nutty': ['nutty', 'almond', 'hazelnut', 'walnut', 'pecan'],
            'floral': ['floral', 'jasmine', 'rose', 'lavender', 'delicate'],
            'bold': ['bold', 'strong', 'intense', 'full'],
            'smooth': ['smooth', 'mild', 'velvety', 'creamy'],
            'earthy': ['earthy', 'herbal', 'woody', 'robust'],
            'sweet': ['sweet', 'caramel', 'honey', 'molasses', 'sugar'],
            'spicy': ['spicy', 'cinnamon', 'clove', 'cardamom'],
            'balanced': ['balanced', 'complex', 'round']
        }
        
        # Region-flavor associations based on coffee knowledge
        self.region_flavor_mapping = {
            'Ethiopia': ['fruity', 'floral', 'bright', 'berry'],
            'Kenya': ['bright', 'fruity', 'citrus', 'acidic'],
            'Colombia': ['balanced', 'chocolatey', 'caramel', 'nutty'],
            'Brazil': ['nutty', 'chocolatey', 'smooth', 'low-acid'],
            'Guatemala': ['chocolatey', 'spicy', 'balanced'],
            'Costa Rica': ['bright', 'balanced', 'honey', 'clean'],
            'Honduras': ['sweet', 'nutty', 'caramel', 'balanced'],
            'Indonesia': ['earthy', 'spicy', 'bold', 'herbal'],
            'Yemen': ['spicy', 'bold', 'complex', 'earthy']
        }
        
        # Determine data directory
        if data_dir is None:
            # Default to a 'data' directory in the project root
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        
        # Construct full file paths
        arabica_path = os.path.join(data_dir, arabica_filename)
        robusta_path = os.path.join(data_dir, robusta_filename)
        
        # Load datasets
        try:
            self.arabica_df = pd.read_csv(arabica_path)
            self.robusta_df = pd.read_csv(robusta_path)
            
            # Ensure Flavor column is string type
            self.arabica_df['Flavor'] = self.arabica_df['Flavor'].astype(str)
            
            # Enhance the dataset with flavor tags based on country and region
            self._enhance_flavor_data()
            
        except FileNotFoundError as e:
            print(f"Warning: {e}. Using empty DataFrames.")
            self.arabica_df = pd.DataFrame()
            self.robusta_df = pd.DataFrame()
        except Exception as e:
            print(f"Error loading coffee databases: {e}")
            self.arabica_df = pd.DataFrame()
            self.robusta_df = pd.DataFrame()
    
    def _enhance_flavor_data(self):
        """
        Enhance coffee data with additional flavor information based on origin and scores.
        """
        # Create a new column for flavor tags
        self.arabica_df['flavor_tags'] = self.arabica_df.apply(self._generate_flavor_tags, axis=1)
        self.robusta_df['flavor_tags'] = self.robusta_df.apply(self._generate_flavor_tags, axis=1)
    
    def _generate_flavor_tags(self, row) -> List[str]:
        """
        Generate flavor tags based on origin, scores, and other attributes.
        
        Args:
            row: DataFrame row with coffee attributes
        
        Returns:
            List[str]: Generated flavor tags
        """
        tags = []
        
        # Add tags based on origin
        country = str(row.get('Country.of.Origin', ''))
        for region, flavors in self.region_flavor_mapping.items():
            if region.lower() in country.lower():
                tags.extend(flavors)
        
        # Add tags based on acidity and body scores
        try:
            acidity_score = float(row.get('Acidity', 0))
            body_score = float(row.get('Body', 0))
            
            if acidity_score >= 8.5:
                tags.extend(['bright', 'fruity'])
            elif acidity_score >= 7.5:
                tags.append('balanced')
            
            if body_score >= 8.5:
                tags.extend(['bold', 'full-bodied'])
            elif body_score >= 7.5:
                tags.append('medium-bodied')
        except (ValueError, TypeError):
            pass
        
        # Add tags based on cup points
        try:
            cup_points = float(row.get('Total.Cup.Points', 0))
            
            if cup_points >= 90:
                tags.extend(['complex', 'exceptional'])
            elif cup_points >= 85:
                tags.extend(['balanced', 'high-quality'])
        except (ValueError, TypeError):
            pass
        
        # Ensure unique tags and limit length
        return list(set(tags))[:10]  # Limit to 10 unique tags
    
    def get_top_coffees_by_region(
        self, 
        species: str = 'Arabica', 
        top_n: int = 10, 
        min_points: float = 85.0
    ) -> pd.DataFrame:
        """
        Retrieve top-rated coffees by region.
        
        Args:
            species (str): Coffee species ('Arabica' or 'Robusta')
            top_n (int): Number of top coffees to return
            min_points (float): Minimum total cup points to consider
        
        Returns:
            DataFrame: Top rated coffees
        """
        # Select appropriate dataframe
        df = self.arabica_df if species == 'Arabica' else self.robusta_df
        
        # Filter by minimum cup points
        filtered_df = df[df['Total.Cup.Points'] >= min_points]
        
        # If no results, return empty dataframe
        if filtered_df.empty:
            return pd.DataFrame()
        
        # Sort and select top coffees
        return filtered_df.sort_values('Total.Cup.Points', ascending=False).head(top_n)[
            ['Country.of.Origin', 'Region', 'Total.Cup.Points', 'Flavor', 'Aftertaste', 'flavor_tags']
        ]
    
    def get_bean_recommendations(
        self, 
        flavor_preferences: Optional[List[str]] = None, 
        species: str = 'Arabica', 
        top_n: int = 5
    ) -> pd.DataFrame:
        """
        Recommend coffee beans based on flavor preferences.
        
        Args:
            flavor_preferences (list, optional): List of desired flavor notes
            species (str): Coffee species ('Arabica' or 'Robusta')
            top_n (int): Number of recommendations to return
        
        Returns:
            DataFrame: Recommended coffee beans
        """
        # Select appropriate dataframe
        df = self.arabica_df if species == 'Arabica' else self.robusta_df
        
        # Debug: Print column info
        print("DataFrame Columns:", df.columns.tolist())
        print("Flavor Column Info:")
        print(df['Flavor'].head())
        print("Flavor Column Type:", df['Flavor'].dtype)
        
        # If no specific preferences, return top-rated
        if not flavor_preferences:
            return self.get_top_coffees_by_region(species, top_n)
        
        # Create a copy of the dataframe to avoid SettingWithCopyWarning
        df = df.copy()
        
        # Add expanded flavor matches
        expanded_preferences = self._expand_flavor_preferences(flavor_preferences)
        
        # Create a scoring mechanism for flavor matching
        def flavor_match_score(row):
            score = 0
            
            # First check if we have flavor tags from our enhancement
            if hasattr(row, 'flavor_tags') and row['flavor_tags']:
                tags = row['flavor_tags']
                # Add 2 points for each direct match with expanded preferences
                for pref in expanded_preferences:
                    if pref in tags:
                        score += 2
            
            # Check flavor column
            try:
                flavor_text = str(row['Flavor']).lower()
                for pref in expanded_preferences:
                    if pref in flavor_text:
                        score += 1
            except (AttributeError, TypeError):
                pass
            
            # Check Country.of.Origin for region-based flavor matches
            try:
                country = str(row['Country.of.Origin']).lower()
                for region, flavors in self.region_flavor_mapping.items():
                    if region.lower() in country:
                        for flavor in flavors:
                            if flavor in expanded_preferences:
                                score += 1.5  # Region-flavor match is valuable
            except (AttributeError, TypeError):
                pass
            
            return score
        
        # Add match score column with error handling
        try:
            # Use apply with axis=1 to pass entire row
            df['flavor_match_score'] = df.apply(flavor_match_score, axis=1)
        except Exception as e:
            print(f"Error calculating flavor match score: {e}")
            # Fallback to a default scoring method
            df['flavor_match_score'] = 0
        
        # Sort by match score and total cup points
        recommended = df[df['flavor_match_score'] > 0].sort_values(
            ['flavor_match_score', 'Total.Cup.Points'], 
            ascending=[False, False]
        ).head(top_n)
        
        # If no matches found, return top coffees
        if recommended.empty:
            return self.get_top_coffees_by_region(species, top_n)
        
        # Enhance the results with descriptive notes
        recommended['notes'] = recommended.apply(
            lambda row: self._generate_descriptive_notes(row, flavor_preferences), 
            axis=1
        )
        
        return recommended[
            ['Country.of.Origin', 'Region', 'Flavor', 'Total.Cup.Points', 'flavor_match_score', 'notes']
        ]
    
    def _expand_flavor_preferences(self, flavor_preferences: List[str]) -> List[str]:
        """
        Expand flavor preferences to include related terms.
        
        Args:
            flavor_preferences (List[str]): Original flavor preferences
        
        Returns:
            List[str]: Expanded flavor preferences
        """
        expanded = []
        for pref in flavor_preferences:
            expanded.append(pref.lower())
            # Add related terms
            for profile, terms in self.flavor_profile_mapping.items():
                if pref.lower() in [profile.lower()] + [t.lower() for t in terms]:
                    expanded.extend([t.lower() for t in terms])
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(expanded))
    
    def _generate_descriptive_notes(self, row: pd.Series, requested_flavors: List[str]) -> str:
        """
        Generate descriptive flavor notes based on row data and requested flavors.
        
        Args:
            row: DataFrame row with coffee attributes
            requested_flavors: List of requested flavor profiles
        
        Returns:
            str: Descriptive flavor notes
        """
        notes = []
        
        # Add notes from country/region
        country = str(row.get('Country.of.Origin', ''))
        region = str(row.get('Region', ''))
        
        # Add flavor notes based on origin
        for region_key, flavors in self.region_flavor_mapping.items():
            if region_key.lower() in country.lower() or (region and region_key.lower() in region.lower()):
                # Prioritize requested flavors that match this origin
                matching_flavors = [f for f in flavors if any(req.lower() in f.lower() for req in requested_flavors)]
                if matching_flavors:
                    notes.extend(matching_flavors[:2])  # Limit to 2 matching flavors
        
        # Add notes based on flavor tags if available
        if hasattr(row, 'flavor_tags') and row['flavor_tags']:
            # Prioritize requested flavors
            for req_flavor in requested_flavors:
                for tag in row['flavor_tags']:
                    if req_flavor.lower() in tag.lower():
                        notes.append(tag)
        
        # Add general descriptors based on scores
        try:
            acidity = float(row.get('Acidity', 0))
            body = float(row.get('Body', 0))
            
            if acidity >= 8.5:
                notes.append('bright')
            if body >= 8.5:
                notes.append('full-bodied')
        except (ValueError, TypeError):
            pass
        
        # Ensure we have at least something
        if not notes:
            # Add generic notes based on requested flavors
            for flavor in requested_flavors:
                if flavor.lower() in self.flavor_profile_mapping:
                    notes.append(flavor.lower())
        
        # Remove duplicates and format
        unique_notes = []
        for note in notes:
            if note not in unique_notes:
                unique_notes.append(note)
        
        # Return formatted string, default to "balanced" if nothing else
        if unique_notes:
            return ", ".join(unique_notes[:3])  # Limit to 3 notes
        else:
            return "balanced"
    
    def extract_flavor_profiles(self, species: str = 'Arabica') -> Dict[str, List[tuple]]:
        """
        Extract and analyze flavor profiles for a given coffee species.
        
        Args:
            species (str): Coffee species ('Arabica' or 'Robusta')
        
        Returns:
            dict: Flavor profile analysis
        """
        # Select appropriate dataframe
        df = self.arabica_df if species == 'Arabica' else self.robusta_df
        
        # Flavor-related columns
        flavor_columns = ['Flavor', 'Aroma', 'Aftertaste']
        
        flavor_analysis = {}
        for col in flavor_columns:
            if col in df.columns:
                # Basic text processing to extract flavor notes
                flavor_notes = df[col].dropna().astype(str).str.lower()
                
                # Find most common flavor descriptors
                common_flavors = self._extract_flavor_keywords(flavor_notes)
                flavor_analysis[col] = common_flavors
        
        return flavor_analysis
    
    def _extract_flavor_keywords(
        self, 
        flavor_series: pd.Series, 
        top_n: int = 10
    ) -> List[tuple]:
        """
        Extract and count common flavor keywords.
        
        Args:
            flavor_series (pd.Series): Series of flavor descriptions
            top_n (int): Number of top keywords to return
        
        Returns:
            list: Top flavor keywords with their counts
        """
        # Common flavor keywords to extract
        flavor_keywords = []
        for profile, terms in self.flavor_profile_mapping.items():
            flavor_keywords.append(profile)
            flavor_keywords.extend(terms)
        
        # Count occurrences of keywords
        flavor_counts = {}
        for keyword in flavor_keywords:
            count = flavor_series.str.contains(keyword).sum()
            flavor_counts[keyword] = count
        
        # Sort and return top keywords
        return sorted(flavor_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    def get_flavor_mapping(self) -> Dict[str, List[str]]:
        """
        Get the flavor profile mapping for external use.
        
        Returns:
            Dict: Mapping of flavor profiles to related terms
        """
        return self.flavor_profile_mapping

# Example usage demonstration
def main():
    # Initialize the database
    coffee_db = CoffeeDatabase()
    
    # Demonstrate various analysis methods
    print("Top Arabica Coffees:")
    print(coffee_db.get_top_coffees_by_region())
    
    print("\nFlavor Profile Analysis:")
    flavor_profiles = coffee_db.extract_flavor_profiles()
    for category, flavors in flavor_profiles.items():
        print(f"{category} Flavors: {flavors}")
    
    print("\nRecommended Beans (Fruity):")
    fruity_recommendations = coffee_db.get_bean_recommendations(
        flavor_preferences=['fruity', 'bright']
    )
    print(fruity_recommendations)

if __name__ == "__main__":
    main()