import csv
import requests
import time
import random

API_URL = "http://127.0.0.1:8000/brew"

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

modifiers = ["", " please", " now", " this morning", " for a hot day", " that helps me relax", " with a kick"]
serving_sizes = [3.0, 7.0, 10.0]

all_prompts = [(cat, prompt) for cat, prompts in categories.items() for prompt in prompts]

for _ in range(80):
    cat = random.choice(list(categories.keys()))
    base = random.choice(categories[cat])
    modified = base + random.choice(modifiers)
    all_prompts.append((cat, modified))

output_file = "coffee_brew_results.csv"
headers = [
    "prompt_id", "category", "prompt", "serving_size",
    "coffee_type", "flavor_profile", "recommended_temp", 
    "grind_size", "pressure_bar", "esp_command"
]

with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=headers)
    writer.writeheader()

    for i, (category, prompt) in enumerate(all_prompts, 1):
        serving_size = random.choice(serving_sizes)
        try:
            res = requests.post(API_URL, json={"query": prompt, "serving_size": serving_size})
            res.raise_for_status()
            data = res.json()

            brew = data.get("brewing_parameters", {})
            writer.writerow({
                "prompt_id": i,
                "category": category,
                "prompt": prompt,
                "serving_size": serving_size,
                "coffee_type": data.get("coffee_type", "N/A"),
                "flavor_profile": data.get("flavor_profile", "N/A"),
                "recommended_temp": brew.get("recommended_temp_c", "N/A"),
                "grind_size": brew.get("ideal_grind_size", "N/A"),
                "pressure_bar": brew.get("pressure_bar", "N/A"),
                "esp_command": data.get("esp_command", "N/A")
            })
            print(f"[{i}] ✅ Processed ({serving_size} oz): {prompt}")
            time.sleep(1)
        except Exception as e:
            print(f"[{i}] ❌ Failed ({serving_size} oz): {prompt} | Error: {e}")
