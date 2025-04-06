import os
import sys
import json
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from pydantic import BaseModel, Field

# Add the LLM directory to the Python path
LLM_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'llm'))
sys.path.append(LLM_DIR)

# Import LLM components
try:
    from src.nlp.request_parser import CoffeeRequestParser
    from src.nlp.prompt_generator import PromptGenerator
    from src.database.coffee_database import CoffeeDatabase
    from src.database.bean_selector import BeanSelector
    from src.brewing.recommendation_engine import RecommendationEngine
    from src.brewing.parameter_calculator import BrewingParameterCalculator
    llm_components_loaded = True
except ImportError as e:
    print(f"Error importing LLM components: {e}")
    llm_components_loaded = False

from fastapi import Depends, HTTPException, FastAPI, Query, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("coffee-brewing-assistant")

app = FastAPI(
    title="Coffee Brewing Assistant API",
    description="API for LLM-powered coffee brewing recommendations",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

# Conversion constants
OZ_TO_ML = 29.5735  # 1 fluid ounce = 29.5735 ml
G_PER_ML = 0.75     # Approximate density of ground coffee

# Size definitions with conversions
SERVING_SIZES = {
    3.0: {
        'oz': 3.0, 
        'ml': 89.0,  # 3 oz converted to ml
        'coffee_g': 21.0,  # Approximate 7g per oz
        'water_ml': 60.0,  # Slightly less water than volume
    },
    7.0: {
        'oz': 7.0, 
        'ml': 207.0,  # 7 oz converted to ml
        'coffee_g': 49.0,  # Approximate 7g per oz
        'water_ml': 180.0,  # Slightly less water than volume
    },
    10.0: {
        'oz': 10.0, 
        'ml': 295.0,  # 10 oz converted to ml
        'coffee_g': 70.0,  # Approximate 7g per oz
        'water_ml': 260.0,  # Slightly less water than volume
    }
}

# Initialize LLM components if available
if llm_components_loaded:
    try:
        coffee_db = CoffeeDatabase()
        bean_selector = BeanSelector(coffee_db)
        recommendation_engine = RecommendationEngine(coffee_db, bean_selector)
        request_parser = CoffeeRequestParser()
        prompt_generator = PromptGenerator()
        logger.info("LLM components initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing LLM components: {e}")
        llm_components_loaded = False

class BrewRequest(BaseModel):
    """Request with either flavor profile or natural language query."""
    desired_flavor: Optional[Dict[str, float]] = None
    query: Optional[str] = None
    serving_size: Optional[float] = Field(
        default=7.0, 
        description="Serving size in fluid ounces (3, 7, or 10)",
        ge=3.0, 
        le=10.0
    )

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Simple user authentication function.
    In development mode, returns a default user ID.
    """
    if ENVIRONMENT == "development" or DEBUG_MODE:
        return "development_user"
    
    # In a real implementation, you would verify the token
    if credentials:
        return credentials.credentials  # This would be the token or user ID
    
    raise HTTPException(status_code=401, detail="Authentication required")

def ml_output_to_command(brew_params: Dict, serving_details: Dict) -> str:
    """Convert brewing parameters to machine command."""
    commands = []

    # Temperature command
    temperature_celsius = brew_params.get("recommended_temp_c", 93)
    if temperature_celsius > 90:
        delay_seconds = int((temperature_celsius - 85) / 2)
        commands.append(f"D-{delay_seconds}")
    else:
        commands.append("D-0")

    # Pressure command
    pressure_bars = brew_params.get('pressure_bar', 9.0)
    motor_speed = int(pressure_bars * 8.33)
    commands.append(f"R-{motor_speed}")

    # Water volume command (using ml from serving details)
    water_volume = int(serving_details['water_ml'])
    commands.append(f"V-{water_volume}")

    # Grind size command
    grind_map = {
        'fine': 1, 'medium-fine': 3, 'medium': 5, 
        'medium-coarse': 7, 'coarse': 9
    }
    grind_setting = grind_map.get(brew_params.get('ideal_grind_size', 'medium').lower(), 5)
    commands.append(f"G-{grind_setting}")

    commands.append("R-0")

    return " ".join(commands)

@app.get("/")
async def status():
    """API status endpoint."""
    return {
        "status": "online",
        "environment": ENVIRONMENT,
        "debug_mode": DEBUG_MODE,
        "llm_components_loaded": llm_components_loaded,
        "message": "Coffee Brewing Assistant API is running"
    }

@app.post("/brew")
async def brew(
    request: BrewRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Unified brewing endpoint that supports both flavor profile and natural language inputs.
    """
    logger.info(f"Brew request received from user {user_id}")
    
    # Validate and retrieve serving size details
    serving_details = SERVING_SIZES.get(request.serving_size, SERVING_SIZES[7.0])
    
    try:
        # Check if LLM components are loaded
        if not llm_components_loaded:
            raise HTTPException(
                status_code=503, 
                detail="LLM components not available. Please check server logs."
            )
        
        # Check which input method is being used
        if request.query:
            # Natural language query path
            logger.info(f"Natural language query: '{request.query}'")
            
            # Parse the natural language request
            parsed_request = request_parser.parse_coffee_request(request.query)
            logger.debug(f"Parsed request: {parsed_request}")
            
            # Extract key information
            coffee_type = parsed_request.get('coffee_type', 'espresso')
            flavor_notes = parsed_request.get('flavor_notes', [])
            roast_preference = parsed_request.get('roast_level')
            user_mood = parsed_request.get('user_mood')
            
            # Generate recommendation
            recommendation = recommendation_engine.generate_recommendation(
                flavor_preferences=flavor_notes,
                coffee_type=coffee_type,
                serving_size=serving_details['coffee_g'],  # Pass coffee weight in grams
                user_mood=user_mood,
                roast_preference=roast_preference
            )
            
            # Store the query with the recommendation
            recommendation["query"] = request.query
            recommendation["serving_details"] = serving_details
            
            # Generate machine command
            command_str = ml_output_to_command(
                recommendation.get("brewing_parameters", {}), 
                serving_details
            )
            recommendation["esp_command"] = command_str
            
            return recommendation
            
        elif request.desired_flavor:
            # Traditional flavor profile path for backward compatibility
            desired_flavor = request.desired_flavor
            logger.info(f"Flavor profile request: {desired_flavor}")
            
            # Map the traditional inputs to flavor notes
            flavor_mapping = {
                "acidity": ["bright", "fruity"],
                "strength": ["bold", "strong"],
                "sweetness": ["sweet", "smooth"],
                "fruitiness": ["fruity", "berry"],
                "maltiness": ["nutty", "chocolate"]
            }
            
            flavor_notes = []
            for param, flavors in flavor_mapping.items():
                if desired_flavor.get(param, 5) > 7:  # Consider high values as preference
                    flavor_notes.append(flavors[0])
            
            # Default to balanced if no strong preferences
            if not flavor_notes:
                flavor_notes = ["balanced"]
            
            # Generate recommendation using the recommendation engine
            recommendation = recommendation_engine.generate_recommendation(
                flavor_preferences=flavor_notes,
                coffee_type="espresso",  # Default
                serving_size=serving_details['coffee_g'],  # Pass coffee weight in grams
                user_mood=None
            )
            
            # Add serving details to recommendation
            recommendation["serving_details"] = serving_details
            
            return recommendation
        
        else:
            raise HTTPException(status_code=400, detail="Either 'query' or 'desired_flavor' must be provided")
        
    except Exception as e:
        logger.error(f"Error processing brew request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Coffee Brewing Assistant API")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)