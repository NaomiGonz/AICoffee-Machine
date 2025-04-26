from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional
import base64
import os
import json
from datetime import datetime
import re
import logging
import time
import sys
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Set up logging with absolute paths and more visible console output
log_file_path = os.path.join(os.getcwd(), "logs", "coffee_scanner.log")

# Configure root logger for console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Explicitly use stdout
    ]
)

# Create a specific logger for our module
logger = logging.getLogger("coffee-scanner")
logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture everything

# Add file handler to our logger
file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Print startup message to confirm logger is working
startup_message = f"☕ Coffee Scanner API starting up. Logs will be written to {log_file_path}"
print(startup_message)
logger.info(startup_message)

# Create OpenAI client - it will use the API key set in main.py
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger.info("🔑 OpenAI client initialized")

# Create router for these endpoints
router = APIRouter()

class CoffeeBagScanRequest(BaseModel):
    front_image: str  # Base64 encoded image
    back_image: str   # Base64 encoded image
    slot_index: int

class CoffeeBeanInfo(BaseModel):
    name: str
    type: str  # arabica, robusta, blend
    roast: str  # Light, Medium, Dark
    notes: str
    detection_status: str = "success"  # success, failed, or error

def base64_to_image(base64_string, output_path):
    """Helper function to convert base64 to image file"""
    try:
        with open(output_path, "wb") as fh:
            fh.write(base64.b64decode(base64_string))
        logger.info(f"Image saved to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving image: {str(e)}")
        return False

@router.get("/api/coffee-scanner-test")
async def test_endpoint():
    logger.info("🧪 Test endpoint called!")
    print("🧪 TEST ENDPOINT CALLED!")
    return {"status": "success", "message": "Coffee Scanner API is working!"}

@router.post("/api/process-coffee-bag")
async def process_coffee_bag(request: CoffeeBagScanRequest):
    start_time = time.time()
    request_id = f"coffee_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.slot_index}"
    
    # Log initial request reception
    initial_log = f"📣 ENDPOINT CALLED: Processing coffee bag scan for slot {request.slot_index}"
    print(initial_log)  # Direct print for immediate console visibility
    logger.info(f"🔍 Request {request_id}: {initial_log}")
    
    try:
        # Log image data size
        front_image_size_kb = len(request.front_image) / 1024
        back_image_size_kb = len(request.back_image) / 1024
        logger.info(f"📸 Request {request_id}: Front image size: {front_image_size_kb:.2f}KB, Back image size: {back_image_size_kb:.2f}KB")
        
        # Optional: Save images temporarily for debugging
        temp_dir = "logs/coffee_scans"  # Changed to a more accessible location
        os.makedirs(temp_dir, exist_ok=True)
        
        front_image_path = f"{temp_dir}/{request_id}_front.jpg"
        back_image_path = f"{temp_dir}/{request_id}_back.jpg"
        
        # Convert and save base64 to image files
        front_saved = base64_to_image(request.front_image, front_image_path)
        back_saved = base64_to_image(request.back_image, back_image_path)
        
        if not front_saved or not back_saved:
            error_msg = f"❌ Failed to save images to {temp_dir}"
            print(error_msg)
            logger.error(f"Request {request_id}: {error_msg}")
            raise HTTPException(status_code=400, detail="Failed to process images")
        
        # Prepare images for GPT API
        front_image_url = f"data:image/jpeg;base64,{request.front_image}"
        back_image_url = f"data:image/jpeg;base64,{request.back_image}"
        
        # Construct the prompt for coffee bag analysis
        prompt = """
        You are an expert coffee analyst. Analyze these coffee bag images (front and back) and extract the following information:
        
        1. Brand and name of the coffee
        2. Type of beans (arabica, robusta, or blend)
        3. Roast level (light, medium, or dark)
        4. Flavor notes mentioned on the packaging
        
        Format your response as a JSON object with the following keys:
        {
          "name": "Brand and coffee name",
          "type": "bean type (arabica/robusta/blend)",
          "roast": "roast level (Light/Medium/Dark)",
          "notes": "flavor notes",
          "detection_status": "success"
        }
        
        If you cannot clearly identify this as a coffee bag, set "detection_status" to "failed" and provide default values.
        
        Provide only the JSON object with no additional text.
        If you cannot determine a value with confidence, use the most likely value based on what you can see.
        """
        
        api_call_msg = "🧠 Sending images to GPT-4.1-mini"
        print(api_call_msg)
        logger.info(f"Request {request_id}: {api_call_msg}")
        
        # Log API call timing
        gpt_start_time = time.time()
        
        try:
            # Use the exact format from the documentation
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": front_image_url,
                            },
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": back_image_url,
                            },
                        },
                    ],
                }],
            )
            
            gpt_time = time.time() - gpt_start_time
            logger.info(f"⏱️ Request {request_id}: GPT-4.1-mini API response received in {gpt_time:.2f} seconds")
            
            # Extract the response content
            response_text = response.choices[0].message.content
            
            # Save raw response to file for debugging
            with open(f"{temp_dir}/{request_id}_response.txt", "w") as f:
                f.write(response_text)
                
            logger.info(f"📄 Request {request_id}: Raw response saved to {temp_dir}/{request_id}_response.txt")
            
        except Exception as api_error:
            error_msg = f"❌ OpenAI API call failed: {str(api_error)}"
            print(error_msg)
            logger.error(f"Request {request_id}: {error_msg}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"API Error: {str(api_error)}")
        
        # Try to extract a JSON object from the response
        json_match = response_text.strip()
        if json_match.startswith('```json'):
            json_match = json_match[7:]
            logger.debug(f"🧹 Request {request_id}: Removed ```json prefix")
        if json_match.endswith('```'):
            json_match = json_match[:-3]
            logger.debug(f"🧹 Request {request_id}: Removed ``` suffix")
        
        try:
            bean_info = json.loads(json_match)
            logger.info(f"✅ Request {request_id}: Successfully parsed JSON response")
            
            # Save parsed JSON for debugging
            with open(f"{temp_dir}/{request_id}_parsed.json", "w") as f:
                json.dump(bean_info, f, indent=2)
                
        except json.JSONDecodeError as e:
            warning_msg = f"⚠️ Failed to parse JSON directly: {str(e)}"
            print(warning_msg)
            logger.warning(f"Request {request_id}: {warning_msg}")
            
            # Fallback: extract anything that looks like JSON
            json_pattern = r'\{.*\}'
            match = re.search(json_pattern, response_text, re.DOTALL)
            if match:
                try:
                    bean_info = json.loads(match.group(0))
                    logger.info(f"✅ Request {request_id}: Successfully parsed JSON using regex extraction")
                    
                    # Save extracted JSON for debugging
                    with open(f"{temp_dir}/{request_id}_extracted.json", "w") as f:
                        json.dump(bean_info, f, indent=2)
                        
                except Exception as e:
                    error_msg = f"❌ Failed to parse extracted JSON: {str(e)}"
                    print(error_msg)
                    logger.error(f"Request {request_id}: {error_msg}")
                    raise HTTPException(
                        status_code=500, 
                        detail="Failed to parse JSON from GPT response"
                    )
            else:
                error_msg = "❌ No valid JSON found in response"
                print(error_msg)
                logger.error(f"Request {request_id}: {error_msg}")
                raise HTTPException(
                    status_code=500,
                    detail="No valid JSON found in response"
                )
        
        # Get detection status
        detection_status = bean_info.get("detection_status", "success")
        
        # Default values for when a coffee bag is not detected
        if detection_status == "failed":
            warning_msg = "⚠️ Coffee bag not clearly detected in images"
            print(warning_msg)
            logger.warning(f"Request {request_id}: {warning_msg}")
            
            default_bean_info = {
                "name": f"Unknown Coffee {request.slot_index}",
                "type": "arabica",
                "roast": "Medium",
                "notes": "No flavor notes detected",
                "detection_status": "failed"
            }
            total_time = time.time() - start_time
            logger.info(f"⏱️ Request {request_id}: Total processing time: {total_time:.2f} seconds (detection failed)")
            return default_bean_info
            
        # Validate and clean up the extracted data
        cleaned_data = {
            "name": bean_info.get("name", ""),
            "type": bean_info.get("type", "arabica").lower(),
            "roast": bean_info.get("roast", "Medium"),  # Keep capitalized for backend
            "notes": bean_info.get("notes", ""),
            "detection_status": detection_status
        }
        
        # Field validation logging
        if cleaned_data["type"] not in ["arabica", "robusta", "blend"]:
            logger.warning(f"⚠️ Request {request_id}: Invalid bean type '{cleaned_data['type']}', defaulting to 'arabica'")
            cleaned_data["type"] = "arabica"
        
        if cleaned_data["roast"].lower() not in ["light", "medium", "dark"]:
            logger.warning(f"⚠️ Request {request_id}: Invalid roast level '{cleaned_data['roast']}', defaulting to 'Medium'")
            cleaned_data["roast"] = "Medium"
        
        success_msg = f"✅ Successfully processed coffee bag: '{cleaned_data['name']}'"
        print(success_msg)
        logger.info(f"Request {request_id}: {success_msg}")
        logger.info(f"☕ Request {request_id}: Bean type: {cleaned_data['type']}, Roast: {cleaned_data['roast']}")
        logger.info(f"📝 Request {request_id}: Flavor notes: {cleaned_data['notes']}")
        
        # Save final result for debugging
        with open(f"{temp_dir}/{request_id}_result.json", "w") as f:
            json.dump(cleaned_data, f, indent=2)
        
        total_time = time.time() - start_time
        logger.info(f"⏱️ Request {request_id}: Total processing time: {total_time:.2f} seconds")
        
        return cleaned_data
        
    except Exception as e:
        error_msg = f"❌ Error processing coffee bag: {str(e)}"
        print(error_msg)
        logger.error(f"Request {request_id}: {error_msg}", exc_info=True)
        
        # Return default values with error status
        error_response = {
            "name": f"Error - Coffee {request.slot_index}",
            "type": "arabica",
            "roast": "Medium",
            "notes": "Error processing images",
            "detection_status": "error"
        }
        
        total_time = time.time() - start_time
        logger.info(f"⏱️ Request {request_id}: Total processing time: {total_time:.2f} seconds (with error)")
        
        return error_response