from firebase_admin import firestore
from brew.feedback_summary import summarize_feedback

db = firestore.client()

def get_user_feedback_summary(user_id):
    # Fetch brews from Firestore
    docs = db.collection("users").document(user_id).collection("brews").stream()
    feedback_list = []

    for doc in docs:
        brew = doc.to_dict()
        feedback = brew.get("feedback")
        
        # Skip brew if there's no rating
        if not feedback or "rating" not in feedback:
            continue

        # Only store relevant details to avoid unnecessary data
        brew_summary = {
            "beans": [b["name"] for b in brew.get("brew_result", {}).get("beans", [])],
            "rating": feedback["rating"],
            "notes": feedback.get("notes", ""),
            "temperature": brew["brew_result"].get("water_temperature_c"),
            "pressure": brew["brew_result"].get("water_pressure_bar")
        }

        feedback_list.append(brew_summary)

    if not feedback_list:
        return "No feedback available for this user."

    # Optionally summarize user preferences based on feedback here or return raw
    return summarize_feedback(feedback_list)  # Call the summary function for easier processing
