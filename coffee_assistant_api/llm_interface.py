# llm_interface.py
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
import torch
import logging
import json
from typing import Optional # <--- ADD THIS LINE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Choose your model. Smaller models are faster but less capable.
# Examples: 'EleutherAI/gpt-neo-1.3B', 'gpt2', 'EleutherAI/gpt-j-6b' (requires more RAM/VRAM)
MODEL_NAME = "EleutherAI/gpt-neo-1.3B"
MAX_NEW_TOKENS = 150 # Max tokens for the LLM to generate in response
# --- End Configuration ---


# Global variables to hold the loaded model and tokenizer
llm_pipeline = None

def load_llm():
    """Loads the LLM model and tokenizer."""
    global llm_pipeline
    if llm_pipeline is None:
        try:
            logger.info(f"Loading LLM model: {MODEL_NAME}...")
            # Check if GPU is available and use it
            device = 0 if torch.cuda.is_available() else -1 # 0 for first GPU, -1 for CPU
            logger.info(f"Using device: {'GPU' if device == 0 else 'CPU'}")

            # Using pipeline for easier text generation handling
            llm_pipeline = pipeline(
                "text-generation",
                model=MODEL_NAME,
                tokenizer=MODEL_NAME,
                device=device,
                torch_dtype=torch.float16 if device == 0 else torch.float32 # Use float16 on GPU for speed/memory
            )
            logger.info("LLM model loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading LLM model: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load LLM model: {MODEL_NAME}") from e
    return llm_pipeline

def format_prompt(user_request: str, user_profile_summary: Optional[str] = None) -> str:
    """Formats the prompt using the template and user request."""

    # Base prompt structure (incorporating your design)
    prompt_template = f"""System/Instruction:
You are a coffee brewing assistant. You will receive a user’s request for a coffee (espresso, Americano, etc.) with certain flavor preferences. Follow these steps:
1. Identify the coffee type and any specific flavor notes or preferences from the user’s request.
2. Determine if any essential details are missing (e.g. shot size for espresso, drink size for Americano) and ask the user for clarification **before** giving a recipe. Ask only one clear question if needed.
3. Based on the coffee type and flavor notes, choose up to 4 coffee beans that match the desired profile. Use your knowledge of coffee:
   - Match flavor notes to bean origins/roasts (e.g. fruity notes → Ethiopian or Kenyan beans; chocolate/nutty → Brazilian/Colombian).
   - You may blend beans to achieve a balance (e.g. mix a light roast with fruity notes and a dark roast for body). Assume access to common single-origin beans and roasts unless specified otherwise.
4. Decide the amount (grams) of each selected bean to total about 18-20g for a double espresso shot (default), or about 8-10g for a single shot if specified.
5. Set the water temperature (in °C) appropriate for the beans and brew method:
   - Use ~94–96°C for light roasts or to emphasize bright, fruity flavors.
   - Use ~88–91°C for dark roasts or to avoid bitterness.
   - For medium or mixed roasts, ~92-93°C is a good middle ground.
6. Set the water pressure (in bar) appropriate for the brew:
   - Espresso-based drinks use ~9 bar (standard espresso pressure).
   - If the request is for a non-espresso method (e.g. a pour-over, French Press), pressure is 1 bar (no extra pressure).
7. Format the final answer *only* as a valid JSON object with keys: `"beans"`, `"water_temperature_c"`, `"water_pressure_bar"`. The "beans" key should be a list of objects, each with "name", "roast", "flavor_notes" (list of strings), and "amount_grams". Do not add explanations or extra text outside the JSON.
8. If clarification is needed, ask the question clearly and concisely as plain text, and *do not* output JSON.

"""
    # Add user profile summary if available (from feedback)
    if user_profile_summary:
        prompt_template += f"User Profile Notes: {user_profile_summary}\n\n"

    # Add the user's actual request
    prompt_template += f"User: {user_request}\nAssistant:"

    return prompt_template


def get_llm_response(prompt: str) -> str:
    """Gets a response from the loaded LLM pipeline."""
    pipeline_instance = load_llm() # Ensure model is loaded
    if not pipeline_instance:
        raise RuntimeError("LLM Pipeline not available.")

    try:
        logger.info("Generating LLM response...")
        # Using do_sample=True and temperature can lead to more creative/varied responses
        # You might adjust top_k, top_p, temperature for desired output style
        sequences = pipeline_instance(
            prompt,
            max_new_tokens=MAX_NEW_TOKENS,
            num_return_sequences=1,
            do_sample=True,
            temperature=0.7, # Lower temp = more deterministic, Higher = more random
            top_k=50,
            top_p=0.95,
            pad_token_id=pipeline_instance.tokenizer.eos_token_id # Important to stop generation
        )
        # The pipeline returns the full text (prompt + completion), extract just the completion
        generated_text = sequences[0]['generated_text']
        # Remove the input prompt part to get only the assistant's response
        response_text = generated_text[len(prompt):].strip()

        logger.info(f"LLM raw response: {response_text}")
        return response_text

    except Exception as e:
        logger.error(f"Error during LLM generation: {e}", exc_info=True)
        return f"Error: Could not generate response from LLM. {e}"


def parse_llm_output(response_text: str) -> tuple[Optional[dict], Optional[str], Optional[str]]:
    """
    Parses the LLM raw output.
    Returns: (parsed_json, clarification_question, error_message)
    Only one of these should typically be non-None.
    """
    response_text = response_text.strip()

    # Attempt to parse as JSON first (most common success case)
    try:
        # Find the start and end of a potential JSON object
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            potential_json = response_text[json_start:json_end]
            parsed_data = json.loads(potential_json)
            # Basic check for required keys
            if "beans" in parsed_data and "water_temperature_c" in parsed_data and "water_pressure_bar" in parsed_data:
                 logger.info("Successfully parsed JSON output.")
                 return parsed_data, None, None
            else:
                 logger.warning("Parsed JSON missing required keys.")
                 # Fall through to treat as clarification/error

        # If no JSON found or parsing failed, check if it looks like a question
        if '?' in response_text and len(response_text) < 150: # Simple heuristic
            logger.info("Detected clarification question.")
            return None, response_text, None

        # If it's neither valid JSON nor a question, treat as an error or unexpected output
        logger.warning(f"LLM output is not valid JSON or a clear question: {response_text}")
        return None, None, f"Unexpected LLM output: {response_text}"

    except json.JSONDecodeError as e:
        logger.warning(f"JSON decoding failed: {e}. Checking if it's a question.")
        # If JSON parsing fails, it might be a clarification question
        if '?' in response_text and len(response_text) < 150:
            logger.info("Detected clarification question after JSON parse failure.")
            return None, response_text, None
        else:
            logger.error(f"LLM output failed JSON parsing and doesn't look like a question: {response_text}")
            return None, None, f"LLM output could not be parsed as JSON or question: {response_text}"
    except Exception as e:
        logger.error(f"Unexpected error parsing LLM output: {e}", exc_info=True)
        return None, None, f"Internal error parsing LLM response: {e}"