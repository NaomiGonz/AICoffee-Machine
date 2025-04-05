# models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Union

class BeanInfo(BaseModel):
    name: str = Field(..., description="Name or origin of the coffee bean")
    roast: Optional[str] = Field(None, description="Roast level (e.g., light, medium, dark)")
    flavor_notes: Optional[List[str]] = Field(None, description="Keywords describing flavor (e.g., fruity, chocolatey)")
    amount_grams: float = Field(..., description="Amount of this bean in grams")

class BrewingParameters(BaseModel):
    beans: List[BeanInfo] = Field(..., max_items=4, description="List of beans to use (up to 4)")
    water_temperature_c: float = Field(..., description="Water temperature in Celsius")
    water_pressure_bar: float = Field(..., description="Water pressure in bars (e.g., 9 for espresso, 1 for drip)")
    # Add other potential parameters if needed: grind_size, brew_time_seconds, etc.

class UserRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user")
    text: str = Field(..., description="User's natural language request for coffee")

class AssistantResponse(BaseModel):
    parameters: Optional[BrewingParameters] = Field(None, description="The final brewing parameters in JSON format")
    clarification: Optional[str] = Field(None, description="A question asked by the assistant if more info is needed")
    error: Optional[str] = Field(None, description="An error message if something went wrong")

class FeedbackRequest(BaseModel):
    user_id: str
    session_id: str # To link feedback to a specific brew request
    parameters_used: BrewingParameters
    rating: Optional[int] = Field(None, ge=1, le=10, description="User rating 1-10")
    comment: Optional[str] = Field(None, description="User qualitative feedback")