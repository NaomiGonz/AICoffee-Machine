# main.py
from fastapi import FastAPI, HTTPException, Depends
from models import UserRequest, AssistantResponse, BrewingParameters, FeedbackRequest
from llm_interface import load_llm, format_prompt, get_llm_response, parse_llm_output
from ml_refinement import refine_parameters_ml, store_feedback, get_user_feedback_summary
from data_loader import get_coffee_dataframe # To potentially use later
import logging
import uuid # For session IDs
from pydantic import ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLM Coffee Brewing Assistant API",
    description="API to get coffee brewing parameters based on natural language requests.",
    version="0.1.0",
)

@app.on_event("startup")
async def startup_event():
    """Load models and data on startup."""
    logger.info("Application startup...")
    try:
        load_llm() # Load the LLM
        get_coffee_dataframe() # Load the coffee data
        logger.info("Startup complete. LLM and data loaded.")
    except Exception as e:
        logger.error(f"Fatal error during startup: {e}", exc_info=True)
        # Depending on severity, you might want the app to fail startup
        # For now, we log and continue, endpoints might fail if LLM didn't load.

@app.post("/brew", response_model=AssistantResponse)
async def handle_brew_request(request: UserRequest):
    """
    Receives a user's coffee request, processes it with the LLM,
    and returns either brewing parameters or a clarification question.
    """
    session_id = str(uuid.uuid4()) # Generate a unique ID for this interaction
    logger.info(f"Received brew request for user {request.user_id} (Session: {session_id}): '{request.text}'")

    try:
        # 1. Get user profile summary (optional enhancement)
        user_summary = get_user_feedback_summary(request.user_id)
        logger.info(f"User profile summary for LLM: {user_summary}")

        # 2. Format Prompt
        prompt = format_prompt(request.text, user_summary)

        # 3. Get LLM Response
        llm_raw_output = get_llm_response(prompt)

        # 4. Parse LLM Output
        parsed_json, clarification, error_msg = parse_llm_output(llm_raw_output)

        if error_msg:
            logger.error(f"Error processing LLM output: {error_msg}")
            # Include session_id in error response for easier debugging
            return AssistantResponse(error=f"Session {session_id}: {error_msg}")

        if clarification:
            logger.info(f"Assistant needs clarification: {clarification}")
            return AssistantResponse(clarification=clarification)

        if parsed_json:
            try:
                # 5. Validate JSON Structure with Pydantic
                llm_params = BrewingParameters(**parsed_json)
                logger.info("LLM parameters validated successfully.")

                # 6. Apply ML Refinement (Placeholder)
                final_params = refine_parameters_ml(llm_params, request.user_id)
                logger.info(f"Final parameters after refinement: {final_params.dict()}")

                # Store the parameters used for this session before returning
                # This allows linking feedback later
                # (Could store in a temporary cache or DB if needed)
                # For simplicity, we won't store parameters *before* feedback here,
                # but the feedback request requires them.

                return AssistantResponse(parameters=final_params)

            except ValidationError as e:
                logger.error(f"LLM output failed Pydantic validation: {e}")
                return AssistantResponse(error=f"Session {session_id}: LLM generated invalid parameter structure. Details: {e}")
            except Exception as e:
                logger.error(f"Error during parameter refinement or validation: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Session {session_id}: Internal server error during parameter processing.")

        # Should not be reached if parse_llm_output logic is correct
        logger.error("Reached unexpected state after parsing LLM output.")
        raise HTTPException(status_code=500, detail=f"Session {session_id}: Unexpected internal server error.")

    except Exception as e:
        logger.error(f"Unhandled error in /brew endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Session {session_id}: Internal server error: {e}")


@app.post("/feedback", status_code=201)
async def handle_feedback(feedback: FeedbackRequest):
    """
    Receives user feedback on a previously brewed coffee.
    """
    logger.info(f"Received feedback for user {feedback.user_id}, session {feedback.session_id}")
    try:
        # Store the feedback (using the placeholder storage)
        store_feedback(
            user_id=feedback.user_id,
            session_id=feedback.session_id,
            feedback_data=feedback.dict() # Store the whole feedback object
        )
        return {"message": "Feedback received successfully."}
    except Exception as e:
        logger.error(f"Error storing feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while storing feedback.")


# Optional: Add a root endpoint for basic checks
@app.get("/")
async def root():
    return {"message": "Welcome to the Coffee Brewing Assistant API!"}