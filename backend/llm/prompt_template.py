def extract_preferences_from_feedback(brew_history):
    """
    Generates a short preference summary from all brews with feedback.
    """
    if not brew_history:
        return "No feedback provided yet."

    lines = []
    liked_beans = {}
    disliked_traits = {}
    temperature_preferences = []
    pressure_preferences = []

    for entry in brew_history:
        feedback = entry.get("feedback")
        brew = entry.get("brew_result", {})
        if not feedback or not brew:
            continue

        rating = feedback.get("rating")
        notes = feedback.get("notes", "No additional comments.")
        bean_names = [b["name"] for b in brew.get("beans", [])]
        bean_desc = ", ".join(bean_names)
        temp = brew.get("water_temperature_c")
        pressure = brew.get("water_pressure_bar")

        # Capture feedback about liking or disliking
        if rating >= 4:
            lines.append(f"User liked {bean_desc}")
            for b in bean_names:
                liked_beans[b] = liked_beans.get(b, 0) + 1
        else:
            lines.append(f"User disliked {bean_desc}")
            if notes:
                disliked_traits[notes] = disliked_traits.get(notes, 0) + 1

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

    summary += "Feedback notes:\n" + "\n".join(lines)
    
    return summary.strip()

def build_system_prompt(available_beans, feedback_brews=None):
    """
    Builds the system prompt for the LLM, dynamically including brewing parameters 
    and respecting grinder max RPM (capped at 3600) and slow grinder ramp-down sequence.
    """
    bean_descriptions = []
    for bean in available_beans:
        desc = f"- {bean['name']} ({bean['roast']} roast): {bean['notes']}"
        bean_descriptions.append(desc)
    beans_str = "\n".join(bean_descriptions)

    user_pref_summary = extract_preferences_from_feedback(feedback_brews or [])
    preference_hint = f"\n\nBased on the user's past brews, consider the following preferences:\n{user_pref_summary}" if user_pref_summary else ""

    pressure = 1
    temperature = 92
    brew_strength = 'normal'

    if "bold" in user_pref_summary or "strong" in user_pref_summary:
        pressure = 9
        brew_strength = 'strong'
    if "cooler" in user_pref_summary:
        temperature = 88
    elif "hotter" in user_pref_summary:
        temperature = 96

    preferred_bean = "Colombian Supremo" if "earthy" not in user_pref_summary else "Brazil Santos"

    cup_size_oz = 7
    bean_weight_per_oz = 1 / 16
    water_amount = cup_size_oz * 30
    total_bean_weight = water_amount * bean_weight_per_oz

    colombian_weight = round(total_bean_weight * 0.5, 2)
    brazil_weight = round(total_bean_weight * 0.5, 2)

    if "earthy" in user_pref_summary or "chocolate" in user_pref_summary:
        colombian_weight = round(total_bean_weight * 0.4, 2)
        brazil_weight = round(total_bean_weight * 0.6, 2)

    grind_size = "G-75"
    if brew_strength == "strong":
        grind_size = "G-100"

    water_volume_ml = water_amount
    flow_rate_mlps = max(2.5, 5.0)  # Ensure minimum 2.5 mL/s

    if brew_strength == "strong":
        flow_rate_mlps = 2.5
    elif brew_strength == "mild":
        flow_rate_mlps = 8.0

    # --- Dynamic Grinder RPM based on brew type ---
    grinder_rpm = 5000  # default
    if "espresso" in user_pref_summary or "latte" in user_pref_summary:
        grinder_rpm = 8000
    elif "french_press" in user_pref_summary:
        grinder_rpm = 3000
    # Cap grinder RPM at 3600
    grinder_rpm = min(grinder_rpm, 3600)

    colombian_dispense_time = round(colombian_weight / 0.61, 1)
    brazil_dispense_time = round(brazil_weight / 0.61, 1)

    heating_power = int((temperature - 88) * (30/8) + 70)
    heating_power = min(100, max(70, heating_power))  # Clamp to 70%-100%

    return f"""
You are a coffee brewing assistant. Your job is to generate JSON brew configurations following these rules:

1. Only use these available beans:
{beans_str}{preference_hint}

2. Mix up to 3 beans specifying grams.

3. Grind size is {grind_size}.

4. Set water temperature to {temperature}°C.

5. Set brew pressure to {pressure} bar.

6. Flow rate must be at least 2.5 mL/s.

When generating the machine_code.commands array, after dispensing beans, slow the grinder down by:

- Set grinder RPM to 3600 → wait 5 sec
- Set grinder RPM to 3000 → wait 5 sec
- Set grinder RPM to 2500 → wait 5 sec
- Set grinder RPM to 2000 → wait 5 sec
- Set grinder RPM to 1250 → wait 30 sec
- Turn grinder off (G-0)

Then continue with drum spin, heating, and brewing.

Output strictly in JSON format.
Example (core template):

{{
  "coffee_type": "latte|espresso|french_press|pour_over|custom",
  "cup_size_oz": 3|7|10,
  "beans": [
    {{
      "name": "{preferred_bean}",
      "roast": "Light|Medium|Dark",
      "notes": "string",
      "amount_g": {colombian_weight}
    }},
    {{
      "name": "Brazil Santos",
      "roast": "Dark",
      "notes": "chocolate, earthy",
      "amount_g": {brazil_weight}
    }}
  ],
  "water_temperature_c": {temperature},
  "water_pressure_bar": {pressure},
  "machine_code": {{
    "commands": [
      "G-{grinder_rpm}",
      "D-5000",
      "S-A-{colombian_dispense_time}",
      "D-{int(colombian_dispense_time * 1000)}",
      "S-B-{brazil_dispense_time}",
      "D-{int(brazil_dispense_time * 1000)}",

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

      "R-3300",
      "D-3000",
      "H-{heating_power}",
      "D-100",
      "P-{water_volume_ml}-{flow_rate_mlps}",
      "R-20000",
      "D-84000",
      "H-0",
      "R-0"
    ]
  }}
}}
""".strip()