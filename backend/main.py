import numpy as np
import pandas as pd
import os
import sys
import json
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

# Add the machine-learning directory to the Python path
sys.path.append(os.path.abspath('../machine-learning')) 
from coffee_ml import CoffeeMachineLearning

import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import Depends, HTTPException, FastAPI, Query, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import httpx
from httpx import BasicAuth

# Set environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("aicoffee")

# Initialize FastAPI
app = FastAPI(
    title="AI Coffee Machine API",
    description="API for AI-powered coffee brewing parameters",
    version="1.0.0"
)

# Enable CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)  # Make it optional

# Initialize Firebase Admin if credentials file exists
firebase_enabled = False
db = None
try:
    if os.path.exists("firebase-admin-key.json"):
        cred = credentials.Certificate("firebase-admin-key.json")
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        firebase_enabled = True
        logger.info("Firebase initialized successfully")
    else:
        logger.warning("Firebase credentials not found, continuing without Firebase")
except Exception as e:
    logger.error(f"Error initializing Firebase: {e}")

# Ensure the machine-learning directories exist
ml_base_dir = os.path.abspath('../machine-learning')
ml_data_dir = os.path.join(ml_base_dir, "data")
ml_models_dir = os.path.join(ml_base_dir, "models")
ml_quality_db_dir = os.path.join(ml_data_dir, "quality_db")

# Create directories if they don't exist
os.makedirs(ml_data_dir, exist_ok=True)
os.makedirs(ml_models_dir, exist_ok=True)
os.makedirs(ml_quality_db_dir, exist_ok=True)

# Initialize ML framework with proper paths
ml = CoffeeMachineLearning(
    data_path=ml_data_dir,
    model_path=ml_models_dir,
    quality_db_path=ml_quality_db_dir
)

# Load models if they exist
try:
    ml.load_config()
    models_loaded = True
    logger.info("ML models loaded successfully")
except Exception as e:
    models_loaded = False
    logger.warning(f"Could not load ML models: {e}. Models will need to be trained.")

# Define Pydantic models for request/response validation
class BrewParameters(BaseModel):
    extraction_pressure: float = Field(..., description="Pressure in bars (1-10)")
    temperature: float = Field(..., description="Water temperature in Celsius (85-96)")
    ground_size: float = Field(..., description="Grind size in microns (100-1000)")
    extraction_time: float = Field(..., description="Brewing time in seconds (20-40)")
    dose_size: float = Field(..., description="Coffee amount in grams (15-25)")
    bean_type: str = Field(..., description="Type of coffee bean (e.g., 'arabica', 'robusta', 'blend')")
    processing_method: Optional[str] = Field(None, description="Bean processing method (e.g., 'washed', 'natural', 'honey')")

class FlavorProfile(BaseModel):
    acidity: float = Field(..., ge=0, le=10, description="Brightness/tanginess (0-10)")
    strength: float = Field(..., ge=0, le=10, description="Intensity/body (0-10)")
    sweetness: float = Field(..., ge=0, le=10, description="Sweetness level (0-10)")
    fruitiness: float = Field(..., ge=0, le=10, description="Fruit notes (0-10)")
    maltiness: float = Field(..., ge=0, le=10, description="Malt/chocolate notes (0-10)")

class BrewRequest(BaseModel):
    desired_flavor: FlavorProfile

class BrewResponse(BaseModel):
    parameters: BrewParameters
    esp_command: str

class FlavorPredictionRequest(BaseModel):
    parameters: BrewParameters

class FlavorPredictionResponse(BaseModel):
    flavor_profile: FlavorProfile

class BrewFeedbackRequest(BaseModel):
    parameters: BrewParameters
    flavor_ratings: FlavorProfile

class FeatureImpactRequest(BaseModel):
    feature: str
    target: str
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    n_points: int = 20

class FeatureImpactResponse(BaseModel):
    feature_values: List[float]
    predicted_values: List[float]

class TrainingStatus(BaseModel):
    status: str
    message: str
    metrics: Optional[Dict] = None

# Helper Functions 
async def get_current_user(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Get the current UID from the Firebase token or return a development user
    """
    # Always allow requests in development mode
    if ENVIRONMENT == "development" or DEBUG_MODE:
        logger.debug("Development mode: using development_user")
        return "development_user"
        
    # Skip Firebase auth if not enabled
    if not firebase_enabled:
        logger.debug("Firebase disabled: using development_user")
        return "development_user"
    
    # If this is a localhost or internal request, allow it
    client_host = request.client.host
    if client_host in ['127.0.0.1', 'localhost', '::1']:
        logger.debug(f"Local request from {client_host}: using development_user")
        return "development_user"
    
    # No credentials provided
    if not credentials:
        logger.warning("No authentication credentials provided")
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        decoded_token = firebase_admin.auth.verify_id_token(credentials.credentials)
        uid = decoded_token['uid']
        logger.debug(f"Authenticated user: {uid}")
        return uid
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
def ml_output_to_command(brew_result: Dict) -> str:
    """
    Converts ML model output to ESP32 command string
    """
    commands = []
    
    temperature_celsius = brew_result["temperature"]
    if temperature_celsius > 90:
        delay_seconds = int((temperature_celsius - 85) / 2)
        commands.append(f"D-{delay_seconds}")
    else:
        commands.append("D-0")
    
    pressure_bars = brew_result['extraction_pressure']
    motor_speed = int(pressure_bars * 8.33)
    commands.append(f"R-{motor_speed}")
    
    dose_grams = brew_result['dose_size']
    extraction_seconds = brew_result['extraction_time']
    water_volume = int(dose_grams * 2.5)
    commands.append(f"V-{water_volume}")
    
    grind_microns = brew_result['ground_size']
    grind_setting = int(10 - (grind_microns - 100) / 90)
    commands.append(f"G-{max(1, min(10, grind_setting))}")
    
    commands.append("R-0")
    
    return " ".join(commands)

def check_models_loaded():
    global models_loaded
    if not models_loaded:
        if ENVIRONMENT == "development" or DEBUG_MODE:
            try:
                synthetic_data_path = os.path.join(ml_data_dir, 'synthetic_brewing_data.csv')
                if not os.path.exists(synthetic_data_path):
                    from test_coffee_ml import generate_synthetic_data
                    data = generate_synthetic_data(n_samples=100)
                    data.to_csv(synthetic_data_path, index=False)
                else:
                    data = pd.read_csv(synthetic_data_path)
                
                ml.train_models(data)
                ml.save_config()
                models_loaded = True
                logger.info("Models trained with synthetic data for development")
                return
            except Exception as e:
                logger.error(f"Error auto-training models: {e}")
                
        raise HTTPException(
            status_code=503, 
            detail="ML models not yet trained. Please train models first using /train endpoint."
        )
    
def ensure_valid_parameters(parameters: Dict) -> Dict:
    """Ensure all required parameters are present and valid"""
    parameters = parameters or {}
    
    # Convert numpy types to native Python types
    for k, v in parameters.items():
        if isinstance(v, np.generic):
            parameters[k] = v.item()
    
    defaults = {
        'extraction_pressure': 9.0,
        'temperature': 93.0,
        'ground_size': 400.0,
        'extraction_time': 30.0,
        'dose_size': 18.0,
        'bean_type': 'arabica',
    }
    
    for key, default_value in defaults.items():
        if key not in parameters or parameters[key] is None:
            logger.warning(f"Parameter {key} missing or None, using default: {default_value}")
            parameters[key] = default_value
    
    return parameters

@app.get("/", tags=["Status"])
async def root():
    return {
        "status": "online",
        "models_loaded": models_loaded,
        "firebase_enabled": firebase_enabled,
        "environment": ENVIRONMENT,
        "debug_mode": DEBUG_MODE,
        "message": "AI Coffee Machine API is running"
    }

@app.post("/brew", response_model=BrewResponse, tags=["Brewing"])
async def calculate_brew(
    request: BrewRequest,
    uid: str = Depends(get_current_user)
):
    logger.info(f"Brew request received for user {uid}")
    check_models_loaded()
    
    try:
        desired_flavor = {
            'acidity': request.desired_flavor.acidity,
            'strength': request.desired_flavor.strength,
            'sweetness': request.desired_flavor.sweetness,
            'fruitiness': request.desired_flavor.fruitiness,
            'maltiness': request.desired_flavor.maltiness
        }
        
        parameters = ml.suggest_brewing_parameters(desired_flavor)
        logger.debug(f"Raw parameters from ML model: {parameters}")
        
        parameters = ensure_valid_parameters(parameters)
        logger.debug(f"Validated parameters types: {[type(v) for v in parameters.values()]}")
        
        command_str = ml_output_to_command(parameters)
        logger.debug(f"Generated ESP32 command: {command_str}")
        
        if firebase_enabled and db:
            try:
                history_ref = db.collection("users").document(uid).collection("brews")
                history_entry = {
                    "desired_flavor": request.desired_flavor.dict(),
                    "parameters": parameters,
                    "esp_command": command_str,
                    "timestamp": firestore.SERVER_TIMESTAMP
                }
                logger.debug(f"Attempting to save to Firestore: {history_entry}")
                history_ref.add(history_entry)
                logger.info(f"Saved brew request to Firebase for user {uid}")
            except Exception as e:
                logger.error(f"Firebase save error: {str(e)}")
                logger.error(f"Parameters causing error: {parameters}")
        
        brew_params = BrewParameters(
            extraction_pressure=parameters['extraction_pressure'],
            temperature=parameters['temperature'],
            ground_size=parameters['ground_size'],
            extraction_time=parameters['extraction_time'],
            dose_size=parameters['dose_size'],
            bean_type=parameters['bean_type'],
            processing_method=parameters.get('processing_method')
        )
        
        return BrewResponse(
            parameters=brew_params,
            esp_command=command_str
        )
    
    except Exception as e:
        logger.error(f"Error calculating brew parameters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ... (Keep other endpoints the same as original, just add the parameter conversion and logging)

if __name__ == "__main__":
    import uvicorn
    
    synthetic_data_path = os.path.join(ml_data_dir, 'synthetic_brewing_data.csv')
    if not os.path.exists(synthetic_data_path):
        try:
            logger.info("Generating synthetic data...")
            from test_coffee_ml import generate_synthetic_data
            data = generate_synthetic_data(n_samples=100)
            data.to_csv(synthetic_data_path, index=False)
            
            ml.train_models(data)
            ml.save_config()
            models_loaded = True
            logger.info("Initial models trained with synthetic data")
        except Exception as e:
            logger.error(f"Error generating synthetic data: {e}")
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)