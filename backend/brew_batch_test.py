import requests
import csv
import time
import random
import json

# ----------------------------------
# Config
# ----------------------------------

URL = "http://localhost:8000/brew"
USER_ID = "test-user-123"
SERVING_SIZE = 7
CSV_PATH = "brew_test_results.csv"
ERROR_LOG_PATH = "brew_test_errors.log"

# ----------------------------------
# Prompt Categories & Variations
# ----------------------------------

prompt_categories = {
    "Fruity Espresso": [
        "I'd love a fruity espresso",
        "Fruity and bright espresso shot",
        "Make me a citrusy espresso",
        "Espresso with a tangy flavor",
        "Bright light roast espresso"
    ],
    "Nutty Pour-Over": [
        "Give me a nutty pour-over",
        "Pour-over with nutty and smooth tones",
        "I want something smooth and nutty",
        "Can I have a pour-over with chocolate and nuts?",
        "Nut-forward light coffee"
    ],
    "Bold Dark Roast": [
        "Strong and bold coffee",
        "Dark roast with intensity",
        "Give me the darkest brew you’ve got",
        "I want intense and bitter flavor",
        "Heavy-bodied black coffee"
    ],
    "Smooth Medium": [
        "Balanced and smooth coffee",
        "Medium roast with mellow flavor",
        "Make a smooth medium roast cup",
        "Nutty medium coffee please",
        "Smooth Colombian cup"
    ],
    "Chocolatey Latte": [
        "Make me a chocolatey latte",
        "Latte with rich chocolate notes",
        "I want a creamy, chocolate-flavored coffee",
        "Milk coffee with chocolate undertone",
        "Sweet and chocolatey latte"
    ]
}

# Flatten and shuffle prompts
prompt_list = [(cat, prompt) for cat, prompts in prompt_categories.items() for prompt in prompts]
random.shuffle(prompt_list)

# ----------------------------------
# Run Requests
# ----------------------------------

results = []
errors = []

for category, prompt in prompt_list:
    payload = {
        "query": prompt,
        "serving_size": SERVING_SIZE,
        "user_id": USER_ID
    }

    try:
        response = requests.post(URL, json=payload)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict) or "coffee_type" not in data:
            raise ValueError("Invalid response structure")

        results.append({
            "category": category,
            "prompt": prompt,
            "coffee_type": data.get("coffee_type"),
            "temperature": data.get("water_temperature_c"),
            "pressure": data.get("water_pressure_bar"),
            "beans": "; ".join(
                [f"{b['name']} ({b['roast']}) {b['amount_g']}g" for b in data.get("beans", [])]
            ),
            "commands": "; ".join(data.get("machine_code", {}).get("commands", []))
        })
        print(f"✅ {prompt} → {data.get('coffee_type')}")
    except Exception as e:
        print(f"❌ {prompt} → {str(e)}")
        errors.append({"prompt": prompt, "error": str(e), "raw": response.text if 'response' in locals() else "No response"})
        results.append({
            "category": category,
            "prompt": prompt,
            "coffee_type": "ERROR",
            "temperature": "",
            "pressure": "",
            "beans": "",
            "commands": ""
        })

    time.sleep(0.5)  # Avoid spamming

# ----------------------------------
# Save CSV Results
# ----------------------------------

fieldnames = ["category", "prompt", "coffee_type", "temperature", "pressure", "beans", "commands"]
with open(CSV_PATH, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

# ----------------------------------
# Save Error Log
# ----------------------------------

if errors:
    with open(ERROR_LOG_PATH, "w") as f:
        for e in errors:
            f.write(json.dumps(e, indent=2) + "\n\n")
    print(f"⚠️ Saved {len(errors)} errors to {ERROR_LOG_PATH}")

print(f"\n📄 Saved {len(results)} rows to {CSV_PATH}")
