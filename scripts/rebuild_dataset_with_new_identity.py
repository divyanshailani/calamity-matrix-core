import json
import os

# 1. Read existing JSONL
input_path = "calamity_training_data.jsonl"
valid_scenarios = []
with open(input_path, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        # Filter out the old identity rows we injected earlier
        # We know they are the ones without a "Location:" in the user prompt
        user_content = data["messages"][1]["content"]
        if "Location:" in user_content:
            valid_scenarios.append(data)

# 2. Append new identity data by importing the updated script module
import sys
sys.path.insert(0, os.path.abspath("scripts"))
from inject_identity import identity_data

valid_scenarios.extend(identity_data)

# 3. Overwrite the file
with open(input_path, "w", encoding="utf-8") as f:
    for entry in valid_scenarios:
        f.write(json.dumps(entry) + "\n")

print(f"Successfully rebuilt JSONL with 47 scenarios + {len(identity_data)} updated identity rows. Total: {len(valid_scenarios)}")
