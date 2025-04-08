def summarize_feedback(feedback_brews: list) -> str:
    """
    Convert structured feedback data into a plain-language summary
    to inform the prompt template.
    """
    if not feedback_brews:
        return "No feedback provided yet."

    notes = []
    liked_beans = {}
    disliked_traits = {}
    temperature_preferences = []
    pressure_preferences = []

    for entry in feedback_brews:
        rating = entry["feedback"]["rating"]
        bean_names = [b["name"] for b in entry["brew_result"]["beans"]]
        bean_desc = ", ".join(bean_names)
        temp = entry["brew_result"].get("water_temperature_c")
        pressure = entry["brew_result"].get("water_pressure_bar")

        # Capture feedback about liking or disliking
        if rating >= 4:
            notes.append(f"User liked {bean_desc}")
            for b in bean_names:
                liked_beans[b] = liked_beans.get(b, 0) + 1
        else:
            notes.append(f"User disliked {bean_desc}")
            if entry["feedback"].get("notes"):
                disliked_trait = entry["feedback"]["notes"]
                disliked_traits[disliked_trait] = disliked_traits.get(disliked_trait, 0) + 1

        # Capture temperature preferences (if any)
        if temp:
            if temp > 92:
                temperature_preferences.append("prefers hotter temperatures")
            elif temp < 90:
                temperature_preferences.append("prefers cooler temperatures")

        # Capture pressure preferences (if any)
        if pressure == 1:
            pressure_preferences.append("prefers lower pressure")
        elif pressure == 9:
            pressure_preferences.append("prefers higher pressure")

    summary = ""

    if liked_beans:
        top = sorted(liked_beans.items(), key=lambda x: x[1], reverse=True)
        summary += "User prefers brews using: " + ", ".join([f"{b} ({c}x)" for b, c in top]) + ".\n"

    if disliked_traits:
        summary += "Avoid traits like: " + ", ".join([f"\"{trait}\"" for trait in disliked_traits]) + ".\n"

    if temperature_preferences:
        summary += "User has a preference for: " + ", ".join(temperature_preferences) + ".\n"
        
    if pressure_preferences:
        summary += "User prefers: " + ", ".join(pressure_preferences) + ".\n"

    summary += "Feedback notes:\n" + "\n".join(notes)
    
    return summary.strip()
