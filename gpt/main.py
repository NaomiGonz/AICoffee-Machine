from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional
from llm.prompt_template import build_system_prompt
from llm.gpt_handler import call_gpt_4o
from brew.personalize import personalize_brew_parameters
from brew.feedback_summary import summarize_feedback
import json
import requests
import datetime
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore
import pytz

# ----------------------
# Firebase Setup
# ----------------------
if not firebase_admin._apps:
    cred = credentials.Certificate("ai-coffee-20cd0-firebase-adminsdk-fbsvc-08c2fd525a.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ----------------------
# Machine Control Functions
# ----------------------
def format_command_string(commands):
    """
    Convert an array of commands to a space-separated string for the machine
    """
    return " ".join(commands)

def send_commands_to_machine(commands, machine_ip="172.20.10.9"):
    """
    Send the commands to the coffee machine
    """
    command_string = format_command_string(commands)
    
    # Log the command being sent
    print(f"📤 Sending to machine {machine_ip}: {command_string}")
    
    try:
        # Submit the command to the machine
        response = requests.post(
            f"http://{machine_ip}/command",
            data={"cmd": command_string}
        )
        
        # Return the response
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response": response.text if response.status_code == 200 else f"Error: {response.status_code}"
        }
    except Exception as e:
        print(f"❌ Machine communication error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# ----------------------
# FastAPI App
# ----------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------
# Models
# ----------------------
class BeanInput(BaseModel):
    name: str
    roast: Literal["Light", "Medium", "Dark"]
    notes: str

class BrewRequest(BaseModel):
    query: str = Field(..., example="Fruity espresso")
    serving_size: Literal[3, 7, 10] = Field(..., example=7)
    user_id: str = Field(..., example="firebaseUID123")

class FeedbackRequest(BaseModel):
    user_id: str
    brew_id: str
    rating: int = Field(..., ge=1, le=5)  # Ensure rating is between 1 and 5
    notes: Optional[str] = None

class BrewExecuteRequest(BaseModel):
    brew_id: str
    user_id: str
    machine_ip: str = "172.20.10.9"  # Default machine IP

# ----------------------
# Brew Route with Auto-Execution
# ----------------------
@app.post("/brew")
async def generate_brew(request: BrewRequest, machine_ip: str = "172.20.10.9"):
    try:
        # Default beans
        available_beans = [
            {"name": "Ethiopian Yirgacheffe", "roast": "Light", "notes": "floral, citrus"},
            {"name": "Colombian Supremo", "roast": "Medium", "notes": "chocolate, nutty"},
            {"name": "Brazil Santos", "roast": "Dark", "notes": "chocolate, earthy"}
        ]
        
        # Pull feedback brews
        feedback_brews = []
        feedback_query = db.collection("users").document(request.user_id).collection("brews").stream()
        for doc in feedback_query:
            data = doc.to_dict()
            if "feedback" in data:
                feedback_brews.append(data)

        # Summarize feedback into user preferences
        user_preferences = summarize_feedback(feedback_brews)

        # Prompt setup
        system_prompt = build_system_prompt(available_beans, feedback_brews=feedback_brews)
        user_prompt = f"{request.query.strip()} (Cup size: {request.serving_size} oz)"

        print("📥 User query:", request.query)
        print("📦 Serving size:", request.serving_size)
        print("🧠 Final user prompt:", user_prompt)

        llm_response = call_gpt_4o(system_prompt, user_prompt)
        if not llm_response:
            raise HTTPException(status_code=500, detail="LLM did not return a response.")

        # Clean up the response to handle markdown code blocks
        cleaned_response = llm_response.strip()
        
        # Remove markdown code block markers if present
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        
        # Attempt to parse as JSON
        try:
            brew_json = json.loads(cleaned_response)
            personalized = personalize_brew_parameters(brew_json)
            
            # Generate optimized commands matching the logged output
            def generate_optimized_commands(brew_data, cup_size_oz):
                """
                Generates an optimized command sequence with scaled parameters
                """
                # Precise timing calculations scaled proportionally
                if cup_size_oz == 3:
                    initial_grind_time_ms = 3000
                    servo_mixing_time_sec = 15
                    delay_after_mixing_ms = 30000
                    water_volume_ml = 89
                    flow_rate_mlps = 2.0
                    pump_time_ms = int((water_volume_ml / flow_rate_mlps) * 1000)
                    final_delay_ms = max(45000, pump_time_ms + 15000)
                    drum_rpm = 3600
                elif cup_size_oz == 7:
                    initial_grind_time_ms = 6000
                    servo_mixing_time_sec = 25
                    delay_after_mixing_ms = 30000
                    water_volume_ml = 207
                    flow_rate_mlps = 3.0
                    pump_time_ms = int((water_volume_ml / flow_rate_mlps) * 1000)
                    final_delay_ms = max(60000, pump_time_ms + 15000)
                    drum_rpm = 3300
                else:  # 10 oz
                    initial_grind_time_ms = 9000
                    servo_mixing_time_sec = 35
                    delay_after_mixing_ms = 30000
                    water_volume_ml = 296
                    flow_rate_mlps = 4.0
                    pump_time_ms = int((water_volume_ml / flow_rate_mlps) * 1000)
                    final_delay_ms = max(75000, pump_time_ms + 15000)
                    drum_rpm = 3000

                # Temperature-based heat power calculation
                temperature_c = brew_data.get('water_temperature_c', 96)
                heat_power = min(max(int((temperature_c - 88) * (30/8) + 70), 0), 100)

                # Bean-specific servo assignments
                servo_commands = []
                bean_servo_map = {
                    "Ethiopian Yirgacheffe": "C",
                    "Colombian Supremo": "B", 
                    "Brazil Santos": "A"
                }
                used_servos = set()

                for bean in brew_data.get('beans', []):
                    servo = bean_servo_map.get(bean['name'], 'B')
                    if servo not in used_servos:
                        servo_commands.append(f"S-{servo}-{servo_mixing_time_sec}")
                        used_servos.add(servo)

                # Command sequence construction
                commands = [
                    "G-1.5",
                    f"D-{initial_grind_time_ms}",
                    *servo_commands,
                    f"D-{delay_after_mixing_ms}",
                    f"R-{drum_rpm}",
                    "D-3000",  # Drum spin-up delay
                    f"H-{heat_power}",
                    "D-100",  # Heater warmup delay
                    f"P-{water_volume_ml}-{flow_rate_mlps}",
                    "R-20000",  # Keep drum running
                    "D-84000",  # Post-pump delay
                    "H-0",
                    "R-0"
                ]

                return commands
            
            # Generate the optimized command sequence
            optimized_commands = generate_optimized_commands(brew_json, request.serving_size)
            
            # Replace the LLM-generated commands with our optimized sequence
            brew_json['machine_code']['commands'] = optimized_commands
            personalized['machine_code']['commands'] = optimized_commands

            # Save result to Firestore
            brew_doc = {
                "query": request.query,
                "serving_size": request.serving_size,
                "timestamp": datetime.utcnow().isoformat(),
                "brew_result": personalized
            }
            doc_ref = db.collection("users").document(request.user_id).collection("brews").document()
            brew_id = doc_ref.id
            personalized["brew_id"] = brew_id
            
            # Save the brew data first
            doc_ref.set(brew_doc)
            print(f"✅ Brew saved for user {request.user_id} with ID {brew_id}")
            
            # Send commands to the machine
            execution_result = send_commands_to_machine(optimized_commands, machine_ip)
            
            # Update the document with execution information
            doc_ref.update({
                "execution": {
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "success": execution_result.get("success", False),
                    "machine_ip": machine_ip,
                    "command_string": format_command_string(optimized_commands),
                    "response": execution_result
                }
            })
            
            # Add execution result to the response
            personalized["execution_result"] = execution_result
            personalized["command_string"] = format_command_string(optimized_commands)
            
            print(f"🤖 Machine execution result: {execution_result}")
            return personalized
            
        except json.JSONDecodeError:
            return {"clarification": llm_response.strip()}

    except Exception as e:
        print("❌ Exception:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
# ----------------------
# Feedback Route
# ----------------------
@app.post("/feedback")
async def save_feedback(feedback: FeedbackRequest):
    try:
        feedback_ref = db.collection("users").document(feedback.user_id).collection("brews").document(feedback.brew_id)
        
        # Validate rating
        if not 1 <= feedback.rating <= 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        
        # Prepare feedback data with a timezone-aware timestamp
        feedback_data = {
            "feedback": {
                "rating": feedback.rating,
                "notes": feedback.notes or "",  # Use empty string if notes is None
                "timestamp": datetime.now(pytz.utc)  # Use current UTC time
            }
        }
        
        # Update the document
        feedback_ref.update(feedback_data)
        
        print(f"✅ Feedback saved for brew {feedback.brew_id}")
        return {"status": "success", "message": "Feedback saved successfully"}
    
    except Exception as e:
        print("❌ Feedback save error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
# ----------------------
# History Route
# ----------------------
@app.get("/history/{user_id}")
async def get_brew_history(user_id: str):
    try:
        brews_ref = db.collection("users").document(user_id).collection("brews")
        docs = brews_ref.stream()
        history = []

        for doc in docs:
            brew = doc.to_dict()
            
            # Ensure timestamp is converted to a consistent format
            if 'timestamp' in brew:
                timestamp = brew['timestamp']
                
                # Convert to datetime if it's a Firestore Timestamp
                if hasattr(timestamp, 'isoformat'):
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                elif isinstance(timestamp, str):
                    # Parse string timestamp and make it timezone-aware
                    try:
                        timestamp = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
                    except ValueError:
                        # Fallback parsing if ISO format fails
                        timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)
                
                # Convert to ISO format string
                brew['timestamp'] = timestamp.isoformat()
                brew["brew_id"] = doc.id
                history.append(brew)

        # Sort by timestamp
        history.sort(
            key=lambda b: datetime.fromisoformat(b["timestamp"]), 
            reverse=True
        )

        return {"history": history}
    except Exception as e:
        print("❌ History fetch error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
# ----------------------
# Execute Brew Route (Direct execution of a saved brew)
# ----------------------
@app.post("/execute-brew")
async def execute_brew(request: BrewExecuteRequest):
    try:
        # Retrieve the brew from Firestore
        brew_ref = db.collection("users").document(request.user_id).collection("brews").document(request.brew_id)
        brew_doc = brew_ref.get()
        
        if not brew_doc.exists:
            raise HTTPException(status_code=404, detail=f"Brew ID {request.brew_id} not found")
        
        # Get the brew data
        brew_data = brew_doc.to_dict()
        
        # Ensure brew_result and machine_code exist
        if not brew_data.get("brew_result") or not brew_data["brew_result"].get("machine_code"):
            raise HTTPException(status_code=400, detail="Brew data is missing machine code")
        
        # Get the commands
        commands = brew_data["brew_result"]["machine_code"]["commands"]
        
        # Send commands to the machine
        result = send_commands_to_machine(commands, request.machine_ip)
        
        # Log execution
        brew_ref.update({
            "execution": {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "success": result.get("success", False),
                "machine_ip": request.machine_ip,
                "command_string": format_command_string(commands),
                "response": result
            }
        })
        
        # Return the result
        return {
            "brew_id": request.brew_id,
            "execution_result": result,
            "commands": commands,
            "command_string": format_command_string(commands)
        }
    
    except Exception as e:
        print(f"❌ Execute brew error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Direct execution endpoint that accepts a brew_id in the URL
@app.get("/execute-brew/{user_id}/{brew_id}")
async def execute_brew_direct(
    user_id: str,
    brew_id: str,
    machine_ip: str = "172.20.10.9"
):
    # Create a request object and call the main execution function
    request = BrewExecuteRequest(
        user_id=user_id,
        brew_id=brew_id,
        machine_ip=machine_ip
    )
    return await execute_brew(request)