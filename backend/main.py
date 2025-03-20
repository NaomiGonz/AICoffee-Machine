from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import joblib  # For loading ML model later

app = FastAPI()

# Enable CORS 
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load ML model
# model = joblib.load("model.pkl")

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

@app.post("/brew", response_model=BrewResponse)
async def calculate_brew(params: BrewRequest):

    # Temporary response until connect with ML
    return {
        "temperature": 92.5,
        "water_ml": 150,
        "pressure_bars": 9,
        "beans": {"Brazilian": 70, "Ethiopian": 30}
    }


# Possible layout for endpoint connected with ML model
'''
@app.post("/brew", response_model=BrewResponse)
async def calculate_brew(params: BrewRequest):

    # Append data to DB

    try:
        # Prepare input features
        input_data = [[
            params.bitterness,
            params.acidity,
            params.sweetness,
            params.strength,
            5,  # Placeholder for balance
            0.12,  # Average moisture
            1500  # Average altitude
        ]]
        
        # Get prediction
        prediction = model.predict(input_data)[0]
        
        # Return send instructions to ESP32 

        # Return response to web-appication
        return {
            "temperature": prediction[0],
            "water_ml": prediction[1],
            "pressure_bars": prediction[2],
            "beans": {
                "Brazilian": prediction[3],
                "Ethiopian": prediction[4]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''