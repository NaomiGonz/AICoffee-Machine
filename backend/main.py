from pydantic import BaseModel
from typing import Optional
import joblib  # For loading ML model later
import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import Depends, HTTPException, FastAPI
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import httpx
from httpx import BasicAuth 

# Enable CORS 
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Initialize Firebase Admin
cred = credentials.Certificate("../firebase-admin-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

'''
# Load ML model
# model = joblib.load("model.pkl")
'''

# Define structures for request and response
class BrewRequest(BaseModel):
    bitterness: int
    acidity: int
    sweetness: int
    strength: int
    fruitiness: int

class BrewResponse(BaseModel):
    temperature: float
    water_ml: float
    pressure_bars: float
    beans: dict  # e.g., {"Brazilian": 60, "Colombian": 40}

class BrewHistory(BaseModel):
    parameters: dict
    result: dict
    timestamp: str

# Helper Functions 
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get the current UID from the Firebase token
    """
    try:
        decoded_token = firebase_admin.auth.verify_id_token(credentials.credentials)
        return decoded_token['uid']
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
def ml_output_to_command(brew_result: dict) -> str:
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
    if brew_result["temperature"] > 90:
        commands.append(f"D-5")  # 5 second pre-heat
    
    # Set motor speed based on pressure (example: 9 bars = 75% speed)
    # TODO: Use equation Meches calculated to make this conversion
    commands.append(f"R-{int(brew_result['pressure_bars'] * 8.33)}")  # 9 bars -> R-75
    
    # Set pump volume
    commands.append(f"V-{int(brew_result['water_ml'])}")
    
    # Stop motor after completion
    commands.append("R-0")
    
    return " ".join(commands)

@app.post("/brew", response_model=BrewResponse)
async def calculate_brew(
    params: BrewRequest,
    uid: str = Depends(get_current_user)
):

    try:
        # Prepare input features
        input_data = [[
            params.bitterness,
            params.acidity,
            params.sweetness,
            params.strength,
        ]]

        '''
        # Get real prediction
        prediction = model.predict(input_data)[0]
        '''

        # Mock prediction for now 
        prediction = {
            "temperature": 92.5,
            "water_ml": 150,
            "pressure_bars": 9,
            "beans": {"Brazilian": 70, "Ethiopian": 30}
        }

        # Generate command string for ESP32
        command_str = ml_output_to_command(brew_result)

        # Send to ESP32
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                esp_response = await client.post(
                    "http://aicoffee.local/command",  # Or ESP32's IP
                    data={"cmd": command_str}
                    auth=BasicAuth("admin", "brewsecure123")
                )
                esp_response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"ESP32 communication failed: {str(e)}"
                )

        # Append data to DB
        history_ref = db.collection("users").document(uid).collection("history")
        history_entry = {
            "parameters": params.dict(),
            "result": prediction,
            "esp_command": command_str,
            "esp_response": esp_response.text,
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        history_ref.add(history_entry)

        return prediction

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# TODO: Implement history endpoint to get user's brewing history 