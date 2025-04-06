import csv
import requests
import time
import random

# Define your FastAPI endpoint
API_URL = "http://127.0.0.1:8000/brew"

# Prompt categories and base prompts
categories = {
    "bold_espresso": [
        "Make me a bold espresso",
        "I need a strong espresso shot",
        "Brew a dark, rich espresso",
        "I want something bold and intense",
        "Give me the strongest espresso you've got"
    ],
    "fruity_light": [
        "I'd like something fruity and light",
        "Make me a bright coffee with citrus notes",
        "I want a floral and fruity cup",
        "Brew something with berry flavors and light body",
        "Give me a light roast with fruitiness"
    ],
    "chocolate_nutty": [
        "Brew a chocolatey and nutty coffee",
        "I want a smooth cup with chocolate notes",
        "Give me coffee with hazelnut and cocoa flavors",
        "Make a nutty medium roast",
        "Prepare a rich, chocolate-inspired brew"
    ],
    "smooth_creamy": [
        "I need a creamy and smooth coffee",
        "Make me a mellow brew with a soft finish",
        "Give me something smooth and not too acidic",
        "Brew a balanced and gentle coffee",
        "I want a velvety coffee with low bitterness"
    ],
    "iced_sweet": [
        "Make an iced sweet latte",
        "Give me a cold brew with vanilla and caramel notes",
        "I want a sweet iced coffee",
        "Brew a refreshing and sugary iced latte",
        "Prepare a chilled sweet coffee drink"
    ]
}

# Flatten and expand to 100+ prompts with modifiers
all_prompts = []
modifiers = ["", " please", " now", " this morning", " for a hot day", " that helps me relax", " with a kick"]

for category, prompts in categories.items():
    for prompt in prompts:
        all_prompts.append((category, prompt))

for _ in range(80):
    cat = random.choice(list(categories.keys()))
    base = random.choice(categories[cat])
    modified = base + random.choice(modifiers)
    all_prompts.append((cat, modified))

# CSV output
output_file = "coffee_brew_results.csv"
headers = [
    "prompt_id", "category", "prompt", 
    "coffee_type", "flavor_profile", "recommended_temp", 
    "grind_size", "pressure_bar", "esp_command"
]

with open(output_file, mode="w", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=headers)
    writer.writeheader()

    for i, (category, prompt) in enumerate(all_prompts, 1):
        try:
            res = requests.post(API_URL, json={"query": prompt, "serving_size": 7.0})
            data = res.json()

            brew = data.get("brewing_parameters", {})
            writer.writerow({
                "prompt_id": i,
                "category": category,
                "prompt": prompt,
                "coffee_type": data.get("coffee_type"),
                "flavor_profile": data.get("flavor_profile"),
                "recommended_temp": brew.get("recommended_temp_c"),
                "grind_size": brew.get("ideal_grind_size"),
                "pressure_bar": brew.get("pressure_bar"),
                "esp_command": data.get("esp_command")
            })
            print(f"[{i}] ✅ Processed: {prompt}")
            time.sleep(1)  # Be nice to the server
        except Exception as e:
            print(f"[{i}] ❌ Failed: {prompt} | Error: {e}")
