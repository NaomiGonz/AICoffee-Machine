# ml_refinement.py
from models import BrewingParameters
from typing import Dict, List, Any
import logging
from typing import Optional # <--- ADD THIS LINE


logger = logging.getLogger(__name__)

# This is a placeholder for actual user feedback storage (in-memory for demo)
# Production: Use a database (SQL, NoSQL)
user_feedback_history: Dict[str, List[Dict[str, Any]]] = {}

def store_feedback(user_id: str, session_id: str, feedback_data: Dict):
    """Stores user feedback."""
    if user_id not in user_feedback_history:
        user_feedback_history[user_id] = []
    feedback_data['session_id'] = session_id # Ensure session_id is stored
    user_feedback_history[user_id].append(feedback_data)
    logger.info(f"Stored feedback for user {user_id}, session {session_id}")

def get_user_feedback_summary(user_id: str) -> Optional[str]:
    """
    Generates a simple summary of user feedback to potentially add to the LLM prompt.
    This is a basic example.
    """
    if user_id not in user_feedback_history or not user_feedback_history[user_id]:
        return None

    summary_parts = []
    # Look at the last few feedback entries
    recent_feedback = user_feedback_history[user_id][-3:] # Look at last 3
    for fb in recent_feedback:
        comment = fb.get('comment', '').lower()
        rating = fb.get('rating')
        temp = fb.get('parameters_used', {}).get('water_temperature_c')

        if rating is not None and rating <= 4:
            if "bitter" in comment:
                summary_parts.append(f"Prefers less bitterness (rated {rating}/10 on brew at {temp}°C).")
            elif "sour" in comment or "acidic" in comment:
                 summary_parts.append(f"May prefer less acidity/sourness (rated {rating}/10 on brew at {temp}°C).")
            elif "weak" in comment:
                 summary_parts.append(f"May prefer stronger coffee (rated {rating}/10).")
        elif rating is not None and rating >= 8:
             summary_parts.append(f"Enjoyed brew rated {rating}/10 (at {temp}°C).")
        elif "fruity" in comment:
             summary_parts.append("Seems to like fruity notes.")
        elif "chocolate" in comment or "nutty" in comment:
             summary_parts.append("Seems to like chocolate/nutty notes.")

    # Remove duplicates and join
    unique_summary = sorted(list(set(summary_parts)))
    if not unique_summary:
        return None

    return " ".join(unique_summary)


def refine_parameters_ml(
    parameters: BrewingParameters,
    user_id: str
) -> BrewingParameters:
    """
    Placeholder for the ML refinement layer.
    This function would adjust the LLM's proposed parameters based on
    historical user feedback.

    For now, it just returns the parameters unchanged or applies a very simple rule.
    """
    logger.info(f"Applying ML refinement for user {user_id} (currently basic)...")
    feedback = user_feedback_history.get(user_id, [])
    refined_params = parameters.copy(deep=True)

    if not feedback:
        logger.info("No feedback history for user, returning original parameters.")
        return refined_params

    # --- Example Simple Adjustment Logic ---
    # Look at the last feedback item
    last_feedback = feedback[-1]
    last_comment = last_feedback.get('comment', '').lower()
    last_rating = last_feedback.get('rating')
    last_temp = last_feedback.get('parameters_used', {}).get('water_temperature_c')

    adjustment_applied = False
    if last_rating is not None and last_rating <= 4:
        if "bitter" in last_comment and refined_params.water_temperature_c > 88:
            refined_params.water_temperature_c = max(88.0, refined_params.water_temperature_c - 1.0) # Lower temp
            logger.info(f"Feedback indicated bitterness; lowering temp to {refined_params.water_temperature_c}°C")
            adjustment_applied = True
        elif ("sour" in last_comment or "weak" in last_comment) and refined_params.water_temperature_c < 96:
             refined_params.water_temperature_c = min(96.0, refined_params.water_temperature_c + 1.0) # Higher temp
             logger.info(f"Feedback indicated sour/weak; raising temp to {refined_params.water_temperature_c}°C")
             adjustment_applied = True
             # Could also adjust dose slightly higher here if beans allow

    if not adjustment_applied:
        logger.info("No specific ML adjustments applied based on last feedback.")
    # --- End Example Logic ---

    # A real ML model would take more history and features into account.
    # It could adjust bean ratios, temperature, maybe even pressure slightly.

    return refined_params