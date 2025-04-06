# data_loader.py
import pandas as pd
import logging
import os
from typing import List, Optional  # <--- already added

logger = logging.getLogger(__name__)
DATA_FILE_PATH = "data/arabica_data_cleaned.csv"

coffee_data_df = None

def load_coffee_data():
    """Loads the coffee quality data from the CSV file."""
    global coffee_data_df
    if coffee_data_df is None:
        try:
            if not os.path.exists(DATA_FILE_PATH):
                logger.error(f"Data file not found at {DATA_FILE_PATH}. Please run download_data.py.")
                # Attempt to download if missing
                from download_data import download_data_func  # Assuming download script has a callable function
                download_data_func()  # Or re-implement download logic here

            if os.path.exists(DATA_FILE_PATH):
                logger.info(f"Loading coffee data from {DATA_FILE_PATH}...")
                coffee_data_df = pd.read_csv(DATA_FILE_PATH)
                # Basic Cleaning / Preparation (Example)
                coffee_data_df = coffee_data_df.dropna(subset=['Variety', 'Processing.Method', 'Flavor', 'Aroma', 'Body', 'Acidity'])

                # Safely handle Roast.Level column
                if 'Roast.Level' in coffee_data_df.columns:
                    coffee_data_df['Roast.Level'] = coffee_data_df['Roast.Level'].fillna('Medium')
                else:
                    coffee_data_df['Roast.Level'] = 'Medium'  # Add default column

                logger.info(f"Coffee data loaded successfully. Shape: {coffee_data_df.shape}")
            else:
                logger.error("Data file still missing after attempting download.")
                coffee_data_df = pd.DataFrame()  # Empty dataframe

        except Exception as e:
            logger.error(f"Error loading coffee data: {e}", exc_info=True)
            coffee_data_df = pd.DataFrame()  # Ensure it's an empty DF on error
    return coffee_data_df

def get_coffee_dataframe():
    """Returns the loaded coffee data DataFrame."""
    return load_coffee_data()

# --- Example function showing how data *could* be used (e.g., for RAG or ML) ---
def find_beans_by_flavor(keywords: List[str], df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Example: Basic search for beans based on flavor keywords in the dataset.
    NOTE: This is a very basic example. Real RAG would be more sophisticated.
    """
    if df.empty or not keywords:
        return None

    # Combine relevant text fields for searching
    df['search_text'] = df['Species'].fillna('') + ' ' + \
                        df['Variety'].fillna('') + ' ' + \
                        df['Processing.Method'].fillna('') + ' ' + \
                        df.get('Flavor.Notes', pd.Series([''] * len(df)))  # Safe fallback if column is missing

    # Search for keywords (case-insensitive)
    pattern = '|'.join([f'(?i){k}' for k in keywords])  # (?i) for case-insensitive
    results = df[df['search_text'].str.contains(pattern, na=False)]

    if not results.empty:
        return results.head(5)  # Return top 5 matches
    return None

# Load data when module is imported
load_coffee_data()
