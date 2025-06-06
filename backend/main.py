from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any
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
import openai
import os
import asyncio
from process_coffee_bag import router as coffee_bag_router
from dotenv import load_dotenv
import time

load_dotenv()

# ----------------------
# Firebase Setup
# ----------------------
if not firebase_admin._apps:
    cred = credentials.Certificate("ai-coffee-20cd0-firebase-adminsdk-fbsvc-c77f5b1cd6.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

openai.api_key = os.getenv("OPENAI_API_KEY")

# ----------------------
# Machine Control Functions
# ----------------------
def format_command_string(commands):
    """
    Convert an array of commands to a space-separated string for the machine
    """
    return " ".join(commands)

def send_commands_to_machine(commands, machine_ip="128.197.180.251"):
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
# Bean Configuration Functions
# ----------------------
def get_user_bean_configuration(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetch the user's bean configuration from Firebase
    """
    # Default beans if no configuration is found
    default_beans = [
        {"name": "Ethiopian Yirgacheffe", "roast": "Light", "notes": "floral, citrus"},
        {"name": "Colombian Supremo", "roast": "Medium", "notes": "chocolate, nutty"},
        {"name": "Brazil Santos", "roast": "Dark", "notes": "chocolate, earthy"}
    ]
    
    try:
        # Get the user's bean configuration
        beans_ref = db.collection("users").document(user_id).collection("beans").document("configuration")
        beans_doc = beans_ref.get()
        
        if beans_doc.exists:
            beans_data = beans_doc.to_dict()
            if beans_data and "slots" in beans_data and len(beans_data["slots"]) > 0:
                # Convert bean configuration to match expected format
                beans = []
                for bean in beans_data["slots"]:
                    # Map the frontend roast format (lowercase) to backend format (capitalized)
                    roast_map = {
                        "light": "Light",
                        "medium": "Medium", 
                        "dark": "Dark"
                    }
                    
                    # Only include beans that have a name
                    if bean.get("name"):
                        beans.append({
                            "name": bean.get("name", ""),
                            "roast": roast_map.get(bean.get("roast", "medium"), "Medium"),
                            "notes": bean.get("notes", "")
                        })
                
                # If we have beans with names, return them
                if len(beans) > 0:
                    print(f"✅ Found {len(beans)} beans in user configuration")
                    return beans
        
        # If we get here, no valid configuration was found
        print("⚠️ No valid bean configuration found, using defaults")
        return default_beans
        
    except Exception as e:
        print(f"❌ Error fetching bean configuration: {str(e)}")
        return default_beans

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

app.include_router(coffee_bag_router)

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
    machine_ip: str = "128.197.180.251"  # Default machine IP

class GrinderCleanRequest(BaseModel):
    machine_ip: str = Field(default="128.197.180.251", example="128.197.180.251")

class DrumCleanRequest(BaseModel):
    machine_ip: str = Field(default="128.197.180.251", example="128.197.180.251")

# ----------------------
# Brew Route with Auto-Execution
# ----------------------
@app.post("/brew")
async def generate_brew(request: BrewRequest, machine_ip: str = "128.197.180.251"):
    try:
        # Get user's bean configuration from Firebase
        available_beans = get_user_bean_configuration(request.user_id)
        
        print(f"🫘 Using beans for user {request.user_id}:")
        for i, bean in enumerate(available_beans):
            print(f"  Bean {i+1}: {bean['name']} ({bean['roast']})")
        
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
                Generates an optimized command sequence with dynamic grinder RPM capped at 3600
                and slow grinder ramp-down before brewing.
                """
                if cup_size_oz == 3:
                    water_volume_ml = 89
                    flow_rate_mlps = max(2.5, 3.0)
                    drum_rpm = 3600
                elif cup_size_oz == 7:
                    water_volume_ml = 207
                    flow_rate_mlps = 5.0
                    drum_rpm = 3300
                else:  # 10 oz
                    water_volume_ml = 296
                    flow_rate_mlps = min(7.0, 8.0)
                    drum_rpm = 3000

                brew_type = brew_data.get('coffee_type', 'pour_over').lower()

                # Dynamic grinder RPM based on brew type (but capped)
                if 'espresso' in brew_type or 'latte' in brew_type:
                    grinder_rpm = 8000
                elif 'french_press' in brew_type:
                    grinder_rpm = 3000
                else:
                    grinder_rpm = 5000

                grinder_rpm = min(grinder_rpm, 3600)  # Always cap at 3600

                temperature_c = brew_data.get('water_temperature_c', 92)
                if temperature_c >= 94:
                    heat_power = 100
                    flow_rate_mlps = min(flow_rate_mlps, 3.5)
                elif temperature_c <= 90:
                    heat_power = 90
                    flow_rate_mlps = max(flow_rate_mlps, 6.5)
                else:
                    heat_power = 95

                flow_rate_mlps = max(2.5, min(flow_rate_mlps, 8.0))  # Ensure flow is between 2.5 and 8.0

                servo_commands = []
                bean_servo_map = {}
                servo_letters = ["A", "B", "C"]
                for i, bean in enumerate(available_beans):
                    if i < len(servo_letters):
                        bean_servo_map[bean["name"]] = servo_letters[i]

                for bean in brew_data.get('beans', []):
                    servo = bean_servo_map.get(bean['name'], 'B')
                    amount_g = bean.get('amount_g', 10)
                    dispense_time_sec = round(amount_g / 0.61, 1)
                    servo_commands.append((servo, dispense_time_sec))

                commands = [
                    f"G-{grinder_rpm}",
                    "D-5000",
                ]

                for servo, time_sec in servo_commands:
                    commands.append(f"S-{servo}-{time_sec}")
                    delay_sec = 4 * (time_sec * 0.61)
                    commands.append(f"D-{int(delay_sec * 1000)}")

                # Grinder slow ramp-down sequence
                commands.extend([
                    "G-3600",
                    "D-5000",
                    "G-3000",
                    "D-5000",
                    "G-2500",
                    "D-5000",
                    "G-2000",
                    "D-5000",
                    "G-1250",
                    "D-30000",
                    "G-0",
                ])

                # Brewing process
                commands.extend([
                    f"R-{drum_rpm}",
                    "D-3000",
                    f"H-{heat_power}",
                    "D-100",
                    f"P-{water_volume_ml}-{flow_rate_mlps}",
                    "R-20000",
                    "D-84000",
                    "H-0",
                    "R-0",
                ])

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
                "brew_result": personalized,
                "used_beans": available_beans  # Save the actual beans used for this brew
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
                    "timestamp": datetime.utcnow().isoformat(),
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
# Get Available Beans Route
# ----------------------
@app.get("/beans/{user_id}")
async def get_available_beans(user_id: str):
    """
    Get the user's configured beans
    """
    try:
        beans = get_user_bean_configuration(user_id)
        return {"beans": beans}
    except Exception as e:
        print(f"❌ Error getting available beans: {str(e)}")
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
                "timestamp": datetime.utcnow().isoformat(),
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
    machine_ip: str = "128.197.180.251"
):
    # Create a request object and call the main execution function
    request = BrewExecuteRequest(
        user_id=user_id,
        brew_id=brew_id,
        machine_ip=machine_ip
    )
    return await execute_brew(request)

# ----------------------
# Brew Progress Streaming
# ----------------------

@app.get("/brew-progress/{brew_id}")
async def stream_brew_progress(brew_id: str):
    async def event_generator():
        progress = 0
        while progress <= 100:
            await asyncio.sleep(2)  # simulate brewing step
            yield f"data: {json.dumps({'progress': progress})}\n\n"
            progress += 10
        # After 100%, close the stream
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ----------------------
# Grinder Clean with Auto-Execution
# ----------------------
@app.post("/grinder-clean")
async def clean_grinder(request: GrinderCleanRequest):
    try:
        print("🧹 Starting grinder cleaning process with progressive speed increase")
        
        # Generate optimized commands for grinder cleaning
        def generate_grinder_cleaning_commands():
            """
            Generates a command sequence for cleaning the grinder.
            Incrementally increases speed from 1250 to 8000 RPM in steps of 250 RPM,
            with a 10-second delay between each increase.
            """
            commands = []
            
            # Progressive speed increase from 1250 to 8000 RPM
            for rpm in range(1250, 8250, 250):
                commands.append(f"G-{rpm}")
                time.sleep(10)  # 10-second delay

            # Progressive speed decrease from 8000 to 1250 RPM
            for rpm in range(8000, 1000, -250):
                commands.append(f"G-{rpm}")
                time.sleep(10)  # 10-second delay
            
            # Stop the grinder
            commands.append("G-0")
            
            return commands
        
        # Generate the optimized command sequence
        cleaning_commands = generate_grinder_cleaning_commands()
        
        # Send commands to the machine
        execution_result = send_commands_to_machine(cleaning_commands, request.machine_ip)
        
        # Prepare response
        cleaning_response = {
            "timestamp": datetime.utcnow().isoformat(),
            "machine_code": {
                "commands": cleaning_commands
            },
            "execution_result": execution_result,
            "command_string": format_command_string(cleaning_commands)
        }
        
        print(f"🤖 Machine execution result for grinder cleaning: {execution_result}")
        return cleaning_response
            
    except Exception as e:
        print("❌ Exception during grinder cleaning:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    
# ----------------------
# Drum Clean with Auto-Execution
# ----------------------
@app.post("/drum-clean")
async def clean_drum(request: DrumCleanRequest):
    try:
        print("🧹 Starting drum cleaning process")
        
        # Generate commands for drum cleaning
        def generate_drum_cleaning_commands():
            """
            Generates a command sequence for cleaning the drum.
            Uses specific preset commands for drum cleaning.
            """
            commands = [
                "P-400-5",
                "R-15000",
                "D-60000",
                "R-0"
            ]
            
            return commands
        
        # Generate the command sequence
        cleaning_commands = generate_drum_cleaning_commands()
        
        # Send commands to the machine
        execution_result = send_commands_to_machine(cleaning_commands, request.machine_ip)
        
        # Prepare response
        cleaning_response = {
            "timestamp": datetime.utcnow().isoformat(),
            "machine_code": {
                "commands": cleaning_commands
            },
            "execution_result": execution_result,
            "command_string": format_command_string(cleaning_commands)
        }
        
        print(f"🤖 Machine execution result for drum cleaning: {execution_result}")
        return cleaning_response
            
    except Exception as e:
        print("❌ Exception during drum cleaning:", str(e))
        raise HTTPException(status_code=500, detail=str(e))