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
    and respecting safety features based on the flowchart.
    """
    bean_descriptions = []
    for bean in available_beans:
        desc = f"- {bean['name']} ({bean['roast']} roast): {bean['notes']}"
        bean_descriptions.append(desc)
    beans_str = "\n".join(bean_descriptions)

    # Extract user preferences based on past brews
    user_pref_summary = extract_preferences_from_feedback(feedback_brews or [])
    preference_hint = f"\n\nBased on the user's past brews, consider the following preferences:\n{user_pref_summary}" if user_pref_summary else ""

    # Extract key brewing parameters
    pressure = 1  # Default pressure for manual methods (adjust based on user preference)
    temperature = 92  # Default medium roast temperature
    brew_strength = 'normal'  # Default brew strength (normal, bold, mild)
    
    if "bold" in user_pref_summary or "strong" in user_pref_summary:
        pressure = 9  # Use higher pressure for espresso-style drinks
        brew_strength = 'strong'
    
    if "cooler" in user_pref_summary:
        temperature = 88  # Cooler brew for light flavors
    elif "hotter" in user_pref_summary:
        temperature = 96  # Hotter brew for rich flavors

    # Adjust bean preferences
    preferred_bean = "Colombian Supremo" if "earthy" not in user_pref_summary else "Brazil Santos"
    
    # Adjust the total amount of beans based on the cup size (1:16 ratio)
    cup_size_oz = 7  # Default cup size is 7 oz
    bean_weight_per_oz = 1 / 16  # 1g of coffee per 16g of water
    water_amount = cup_size_oz * 30  # Approx 30ml of water per ounce
    total_bean_weight = water_amount * bean_weight_per_oz  # Total beans in grams

    # Dynamic calculation of bean percentages based on user preferences
    bean_percentages = {
        "Colombian Supremo": 0.5,
        "Brazil Santos": 0.5
    }

    if "earthy" in user_pref_summary or "chocolate" in user_pref_summary:
        # Adjust bean mix if earthy or chocolate notes are preferred
        bean_percentages = {
            "Colombian Supremo": 0.4,
            "Brazil Santos": 0.6
        }

    # Calculate the amount of each bean dynamically based on the user's preferences
    beans_with_weights = {
        bean: round(total_bean_weight * percent, 2) 
        for bean, percent in bean_percentages.items()
    }

    # Determine grind size based on user strength preference
    grind_size = "G-75"  # Default grind size for normal brew

    if brew_strength == "strong":
        grind_size = "G-100"  # Finer grind for stronger coffee
    
    # Calculate expected water volume and flow rate
    water_volume_ml = water_amount  # Water volume in ml
    flow_rate_mlps = 3.0  # Default flow rate in ml/s
    
    # Adjust flow rate based on brew strength
    if brew_strength == "strong":
        flow_rate_mlps = 2.0  # Slower for stronger extraction
    elif brew_strength == "mild":
        flow_rate_mlps = 4.0  # Faster for lighter extraction
    
    # Calculate expected delays and brew times
    grind_delay_ms = 3000  # Default grinding time
    mixing_time_sec = 30   # Default servo mixing time
    heating_power = int((temperature - 88) * (30/8) + 70)  # Maps 88°C->70%, 96°C->100% 

    # Adjust delays based on cup size
    if cup_size_oz == 3:
        grind_delay_ms = 2000
        mixing_time_sec = 20
    elif cup_size_oz == 10:
        grind_delay_ms = 5000
        mixing_time_sec = 35

    # Generate the system prompt with dynamic values
    return f"""
You are a coffee brewing assistant. You will receive a user's request for a coffee with certain flavor preferences.

Follow these rules:

1. Only select from the following available beans:
{beans_str}{preference_hint}

2. Mix up to 3 of these beans with flexible percentages that sum to 100%.
   - Example: 50% Colombian Supremo + 50% Brazil Santos, or 70% Colombian Supremo + 30% Brazil Santos.

3. Do not mention or use any beans not listed above.

4. Grind size is fixed – do not mention or change it. 
   - For a {brew_strength} brew, use the grind size of {grind_size}.

5. Choose a water temperature in Celsius:
   - Light roasts or fruity flavors → 94–96°C
   - Medium roasts → ~92°C
   - Dark roasts → 88–90°C
   - For this brew, set temperature to {temperature}°C.

6. Use 9 bar pressure for espresso-based drinks 
   (e.g. espresso, cappuccino, macchiato, ristretto, latte).
   Use 1 bar pressure for manual methods 
   (e.g. French press, pour-over, drip, AeroPress).
   - For this brew, set pressure to {pressure} bar.

7. Ask the user to clarify cup size if it's missing. The available cup sizes are:
   - 3 oz (small)
   - 7 oz (medium)
   - 10 oz (large)

8. Do not return a brew configuration until the cup size is known.

When all information is available, output strictly in this JSON format:

{{
  "coffee_type": "latte|espresso|french_press|pour_over|custom",
  "cup_size_oz": 3|7|10,
  "beans": [
    {{
      "name": "{preferred_bean}",
      "roast": "Light|Medium|Dark",
      "notes": "string",
      "amount_g": {beans_with_weights.get("Colombian Supremo", 0)}  # Adjusted bean amount
    }},
    {{
      "name": "Brazil Santos",
      "roast": "Dark",
      "notes": "chocolate, earthy",
      "amount_g": {beans_with_weights.get("Brazil Santos", 0)}  # Adjusted bean amount
    }}
  ],
  "water_temperature_c": {temperature},
  "water_pressure_bar": {pressure},
  "machine_code": {{
    "commands": [
      "G-1.5",  # Grinder motor current (0.0-2.0 Amps)
      "D-{grind_delay_ms}",  # Delay for grinding (milliseconds)
      "S-B-{mixing_time_sec}",  # Servo B for bean mixing (seconds)
      "D-{mixing_time_sec * 1000}",  # Delay for mixing (milliseconds)
      "G-0",  # Turn off grinder
      "R-3600",  # Drum rotation speed (RPM)
      "D-5000",  # Delay for drum to reach speed (milliseconds)
      "H-{heating_power}",  # Heater power (%)
      "P-{water_volume_ml}-{flow_rate_mlps}",  # Water pump (volume-rate)
      "D-20000",  # Brewing delay (milliseconds)
      "R-0"   # Turn off drum
    ]
  }}
}}

The machine_code.commands array must include serial commands in this specific format:

- Grinder current: "G-<amps>" (e.g., G-1.5) - Valid range: 0.0 to 2.0 Amps
- Drum rotation: "R-<rpm>" (e.g., R-3600) - Typical range: 0 to 4000 RPM
- Heater power: "H-<power%>" (e.g., H-85) - Range: 0 to 100%
- Water pump: "P-<volume>-<rate>" (e.g., P-50-3) - Volume in mL, Rate in mL/s
- Servo control: "S-<id>-<time_sec>" (e.g., S-B-30) - ID: A-D, Time in seconds
- Delay: "D-<ms>" (e.g., D-3000) - Time in milliseconds

You can repeat commands and add delays as needed, but follow this general sequence:
1. Start grinding (G command)
2. Delay for grinding (D command)
3. Optional mixing (S command)
4. Delay for mixing (D command)
5. Turn off grinder (G-0)
6. Start drum (R command)
7. Delay for drum speed (D command)
8. Turn on heater (H command)
9. Pump water (P command)
10. Delay for brewing (D command)
11. Turn off heater (H-0) - Note: Not needed if only turning off drum
12. Turn off drum (R-0)

Match water_temperature_c with heater power:  
- 88°C → ~70% power  
- 92°C → ~85% power
- 96°C → ~100% power  

For cup size to water volume mapping:  
- 3 oz → ~88 mL  
- 7 oz → ~207 mL  
- 10 oz → ~296 mL  

Your response should contain only the JSON — no extra explanations, notes, or formatting.
    """.strip()