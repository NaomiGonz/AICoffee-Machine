#!/usr/bin/env python3

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
    
    Example mapping:
    - Water volume -> V-xxx
    - Pressure -> R-xxx (motor speed)
    - Temperature -> D-xxx (pre-heat delay)
    """
    commands = []
    
    # Add pre-heat delay based on temperature 
    # TODO: Add more sophisticated using the SSR 
    temperature_celsius = brew_result["temperature"]
    if temperature_celsius > 90:
        delay_seconds = int((temperature_celsius - 85) / 2)
        commands.append(f"D-{delay_seconds}")  # Proportional delay
    else:
        commands.append("D-0")  # No delay for lower temps
    
    # Set motor speed based on pressure
    # TODO: Use equation Meches calculated to make this conversion
    pressure_bars = brew_result['extraction_pressure']
    motor_speed = int(pressure_bars * 8.33)  # Convert bars to motor speed percentage
    commands.append(f"R-{motor_speed}")
    
    # Calculate water volume based on dose size and extraction time
    dose_grams = brew_result['dose_size']
    extraction_seconds = brew_result['extraction_time']
    water_volume = int(dose_grams * 2.5)  # Rule of thumb: 2.5ml water per gram of coffee
    commands.append(f"V-{water_volume}")
    
    # Grind size setting (if the machine supports it)
    grind_microns = brew_result['ground_size']
    grind_setting = int(10 - (grind_microns - 100) / 90)  # Convert microns to 1-10 scale
    commands.append(f"G-{max(1, min(10, grind_setting))}")  # Ensure in range 1-10
    
    # Stop motor after completion
    commands.append("R-0")
    
    return " ".join(commands)

def check_models_loaded():
    """Check if models are loaded and raise exception if not"""
    global models_loaded  # Move this to the beginning of the function
    
    if not models_loaded:
        if ENVIRONMENT == "development" or DEBUG_MODE:
            # Try to generate synthetic data and train models
            try:
                synthetic_data_path = os.path.join(ml_data_dir, 'synthetic_brewing_data.csv')
                
                # Check if synthetic data exists, if not generate it
                if not os.path.exists(synthetic_data_path):
                    from test_coffee_ml import generate_synthetic_data
                    data = generate_synthetic_data(n_samples=100)
                    data.to_csv(synthetic_data_path, index=False)
                else:
                    data = pd.read_csv(synthetic_data_path)
                
                # Train models
                ml.train_models(data)
                ml.save_config()
                
                models_loaded = True  # This is fine now because we declared global at the top
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
    if parameters is None:
        parameters = {}
    
    # Default values for parameters
    defaults = {
        'extraction_pressure': 9.0,
        'temperature': 93.0,
        'ground_size': 400.0,
        'extraction_time': 30.0,
        'dose_size': 18.0,
        'bean_type': 'arabica',
    }
    
    # Apply defaults for missing or None values
    for key, default_value in defaults.items():
        if key not in parameters or parameters[key] is None:
            logger.warning(f"Parameter {key} missing or None, using default: {default_value}")
            parameters[key] = default_value
    
    return parameters

@app.get("/", tags=["Status"])
async def root():
    """Root endpoint for API status check"""
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
    """
    Get optimal brewing parameters for a desired flavor profile
    """
    logger.info(f"Brew request received for user {uid}")
    check_models_loaded()
    
    try:
        # Extract desired flavor profile
        desired_flavor = {
            'acidity': request.desired_flavor.acidity,
            'strength': request.desired_flavor.strength,
            'sweetness': request.desired_flavor.sweetness,
            'fruitiness': request.desired_flavor.fruitiness,
            'maltiness': request.desired_flavor.maltiness
        }
        
        logger.debug(f"Desired flavor profile: {desired_flavor}")
        
        # Get brewing parameters suggestion from ML model
        parameters = ml.suggest_brewing_parameters(desired_flavor)
        logger.debug(f"Raw parameters from ML model: {parameters}")
        
        # Ensure all parameters are valid
        parameters = ensure_valid_parameters(parameters)
        logger.debug(f"Validated parameters: {parameters}")
        
        # Generate ESP32 command string
        command_str = ml_output_to_command(parameters)
        logger.debug(f"Generated ESP32 command: {command_str}")
        
        # Store in Firebase if enabled
        if firebase_enabled and db:
            try:
                history_ref = db.collection("users").document(uid).collection("brews")
                history_entry = {
                    "desired_flavor": request.desired_flavor.dict(),
                    "parameters": parameters,
                    "esp_command": command_str,
                    "timestamp": firestore.SERVER_TIMESTAMP
                }
                history_ref.add(history_entry)
                logger.info(f"Saved brew request to Firebase for user {uid}")
            except Exception as e:
                logger.error(f"Error saving to Firebase: {e}")
        
        # Create response object
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

@app.post("/predict", response_model=FlavorPredictionResponse, tags=["Prediction"])
async def predict_flavor(
    request: FlavorPredictionRequest,
    uid: str = Depends(get_current_user)
):
    """
    Predict the flavor profile for given brewing parameters
    """
    check_models_loaded()
    
    try:
        # Extract brewing parameters
        brewing_params = {
            'extraction_pressure': request.parameters.extraction_pressure,
            'temperature': request.parameters.temperature,
            'ground_size': request.parameters.ground_size,
            'extraction_time': request.parameters.extraction_time,
            'dose_size': request.parameters.dose_size,
            'bean_type': request.parameters.bean_type
        }
        
        # Add processing method if provided
        if request.parameters.processing_method:
            brewing_params['processing_method'] = request.parameters.processing_method
        
        # Get flavor prediction from ML model
        flavor_profile = ml.predict_flavor_profile(brewing_params)
        
        # Create response object
        return FlavorPredictionResponse(
            flavor_profile=FlavorProfile(
                acidity=flavor_profile['acidity'],
                strength=flavor_profile['strength'],
                sweetness=flavor_profile['sweetness'],
                fruitiness=flavor_profile['fruitiness'],
                maltiness=flavor_profile['maltiness']
            )
        )
    
    except Exception as e:
        logger.error(f"Error predicting flavor profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback", tags=["Feedback"])
async def provide_feedback(
    request: BrewFeedbackRequest,
    uid: str = Depends(get_current_user)
):
    """
    Provide feedback on a brewing result to improve the ML model
    """
    try:
        # Extract brewing parameters and feedback
        brewing_params = {
            'extraction_pressure': request.parameters.extraction_pressure,
            'temperature': request.parameters.temperature,
            'ground_size': request.parameters.ground_size,
            'extraction_time': request.parameters.extraction_time,
            'dose_size': request.parameters.dose_size,
            'bean_type': request.parameters.bean_type
        }
        
        # Add processing method if provided
        if request.parameters.processing_method:
            brewing_params['processing_method'] = request.parameters.processing_method
        
        flavor_ratings = {
            'acidity': request.flavor_ratings.acidity,
            'strength': request.flavor_ratings.strength,
            'sweetness': request.flavor_ratings.sweetness,
            'fruitiness': request.flavor_ratings.fruitiness,
            'maltiness': request.flavor_ratings.maltiness
        }
        
        # Add feedback to data collection
        ml.collect_brewing_data(brewing_params, flavor_ratings)
        
        # Store in Firebase if enabled
        if firebase_enabled and db:
            try:
                feedback_ref = db.collection("users").document(uid).collection("feedback")
                feedback_entry = {
                    "parameters": request.parameters.dict(),
                    "flavor_ratings": request.flavor_ratings.dict(),
                    "timestamp": firestore.SERVER_TIMESTAMP
                }
                feedback_ref.add(feedback_entry)
                logger.info(f"Saved feedback to Firebase for user {uid}")
            except Exception as e:
                logger.error(f"Error saving feedback to Firebase: {e}")
        
        return {"status": "success", "message": "Feedback recorded successfully"}
    
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/impact", response_model=FeatureImpactResponse, tags=["Analysis"])
async def analyze_feature_impact(
    request: FeatureImpactRequest,
    uid: str = Depends(get_current_user)
):
    """
    Analyze the impact of a brewing parameter on a flavor attribute
    """
    check_models_loaded()
    
    try:
        # Run impact analysis
        impact_data = ml.analyze_feature_impact(
            request.feature, 
            request.target, 
            request.range_min, 
            request.range_max, 
            request.n_points
        )
        
        if impact_data is None or impact_data.empty:
            raise HTTPException(
                status_code=404, 
                detail=f"No impact data available for {request.feature} on {request.target}"
            )
        
        # Convert to response format
        return FeatureImpactResponse(
            feature_values=impact_data['feature_value'].tolist(),
            predicted_values=impact_data[f'predicted_{request.target}'].tolist()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing feature impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/train", response_model=TrainingStatus, tags=["Model Management"])
async def train_models(
    test_size: float = Query(0.2, ge=0.1, le=0.5),
    uid: str = Depends(get_current_user)
):
    """
    Train or retrain the ML models using collected data
    """
    global models_loaded
    
    try:
        # Load data
        data = ml.load_data()
        
        if len(data) < 10:
            return TrainingStatus(
                status="error",
                message=f"Not enough data to train models. Found {len(data)} samples, need at least 10."
            )
        
        # Train models
        metrics = ml.train_models(data, test_size=test_size)
        
        # Save configuration
        ml.save_config()
        
        # Update global status
        models_loaded = True
        
        # Return metrics
        return TrainingStatus(
            status="success",
            message=f"Models trained successfully with {len(data)} samples",
            metrics=metrics
        )
    
    except Exception as e:
        logger.error(f"Error training models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/esp/command", tags=["ESP32 Communication"])
async def send_command_to_esp(
    command: str = Query(..., description="Command string to send to ESP32"),
    uid: str = Depends(get_current_user)
):
    """
    Send a command directly to the ESP32 controller
    """
    try:
        # Send to ESP32
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                esp_response = await client.post(
                    "http://aicoffee.local/command",  # Or ESP32's IP
                    data={"cmd": command},
                    auth=BasicAuth("admin", "brewsecure123")
                )
                esp_response.raise_for_status()
                
                return {
                    "status": "success", 
                    "command": command,
                    "esp_response": esp_response.text
                }
                
            except httpx.HTTPStatusError as e:
                logger.error(f"ESP32 communication error: {e}")
                raise HTTPException(
                    status_code=502,
                    detail=f"ESP32 communication failed: {str(e)}"
                )
    
    except Exception as e:
        logger.error(f"Error sending command to ESP32: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history", tags=["User Data"])
async def get_brew_history(
    limit: int = Query(10, ge=1, le=100),
    uid: str = Depends(get_current_user)
):
    """
    Get user's brewing history
    """
    if not firebase_enabled or not db:
        # Return empty history if Firebase is not enabled
        return {"history": []}
    
    try:
        history_ref = db.collection("users").document(uid).collection("brews")
        query = history_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
        
        results = []
        for doc in query.stream():
            data = doc.to_dict()
            # Convert Firestore timestamp to string if it exists
            if "timestamp" in data and data["timestamp"]:
                data["timestamp"] = data["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            
            results.append({
                "id": doc.id,
                **data
            })
        
        return {"history": results}
    
    except Exception as e:
        logger.error(f"Error retrieving brew history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Open endpoints that don't require authentication
@app.post("/open/brew", response_model=BrewResponse, tags=["Open Endpoints"])
async def open_brew(request: BrewRequest):
    """
    Open endpoint for brew parameters (no authentication required)
    """
    global models_loaded
    try:
        # Extract desired flavor profile
        desired_flavor = {
            'acidity': request.desired_flavor.acidity,
            'strength': request.desired_flavor.strength,
            'sweetness': request.desired_flavor.sweetness,
            'fruitiness': request.desired_flavor.fruitiness,
            'maltiness': request.desired_flavor.maltiness
        }
        
        # Check models
        if not models_loaded:
            try:
                synthetic_data_path = os.path.join(ml_data_dir, 'synthetic_brewing_data.csv')
                if os.path.exists(synthetic_data_path):
                    data = pd.read_csv(synthetic_data_path)
                    ml.train_models(data)
                    ml.save_config()
                    models_loaded = True
                    logger.info("Models trained for open endpoint")
                else:
                    # Use fallback parameters
                    return BrewResponse(
                        parameters=BrewParameters(
                            extraction_pressure=9.0,
                            temperature=93.0,
                            ground_size=400.0,
                            extraction_time=30.0,
                            dose_size=18.0,
                            bean_type='arabica'
                        ),
                        esp_command="D-4 R-75 V-45 G-7 R-0"
                    )
            except Exception as e:
                logger.error(f"Error training models for open endpoint: {e}")
                # Use fallback parameters
                return BrewResponse(
                    parameters=BrewParameters(
                        extraction_pressure=9.0,
                        temperature=93.0,
                        ground_size=400.0,
                        extraction_time=30.0,
                        dose_size=18.0,
                        bean_type='arabica'
                    ),
                    esp_command="D-4 R-75 V-45 G-7 R-0"
                )
        
        # Get brewing parameters suggestion from ML model
        parameters = ml.suggest_brewing_parameters(desired_flavor)
        parameters = ensure_valid_parameters(parameters)
        
        # Generate ESP32 command string
        command_str = ml_output_to_command(parameters)
        
        # Create response object
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
        logger.error(f"Error in open brew endpoint: {e}")
        # Return reasonable defaults
        return BrewResponse(
            parameters=BrewParameters(
                extraction_pressure=9.0,
                temperature=93.0,
                ground_size=400.0,
                extraction_time=30.0,
                dose_size=18.0,
                bean_type='arabica'
            ),
            esp_command="D-4 R-75 V-45 G-7 R-0"
        )

@app.post("/debug", tags=["Debugging"])
async def debug_request(request: Request):
    """Debug endpoint to check request body"""
    body = await request.json()
    return {
        "received": body,
        "required_structure": {
            "desired_flavor": {
                "acidity": "number between 0-10",
                "strength": "number between 0-10",
                "sweetness": "number between 0-10", 
                "fruitiness": "number between 0-10",
                "maltiness": "number between 0-10"
            }
        }
    }
# TODO: Implement additional endpoints for bean quality database integration

if __name__ == "__main__":
    import uvicorn
    
    # Check if we should generate test data on startup
    synthetic_data_path = os.path.join(ml_data_dir, 'synthetic_brewing_data.csv')
    if not os.path.exists(synthetic_data_path):
        try:
            logger.info("No data found. Generating synthetic data for initial testing...")
            # Import the generate_synthetic_data function from the machine-learning directory
            from test_coffee_ml import generate_synthetic_data
            
            data = generate_synthetic_data(n_samples=100)
            data.to_csv(synthetic_data_path, index=False)
            
            # Try to train initial models
            ml.train_models(data)
            ml.save_config()
            models_loaded = True
            logger.info("Initial models trained with synthetic data")
        except Exception as e:
            logger.error(f"Error generating synthetic data: {e}")
    
    # Start the server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)