import re
import json

def parse_v1(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    prompts = {}
    parts = re.split(r'## Scenario (\d+) —', content)
    for i in range(1, len(parts), 2):
        num = int(parts[i])
        body = parts[i+1]
        match = re.search(r'### Prompt\n+```(?:markdown)?\n(.*?)```\n+(?:### Expected|---)', body, re.DOTALL)
        if match:
            prompts[num] = match.group(1).strip()
    return prompts

def parse_v2(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    responses = {}
    parts = re.split(r'\[Scenario (\d+)\]', content)
    for i in range(1, len(parts), 2):
        num = int(parts[i])
        body = parts[i+1]
        match = re.search(r'Expected Response:\n(.*?)(?=\[Scenario \d+\]|\Z)', body, re.DOTALL)
        if match:
            responses[num] = match.group(1).strip()
    return responses

prompts = parse_v1("raw_training_prompts.md")
responses = parse_v2("raw_training_prompts_v2.md")

drop_ids = {23, 47, 50}
valid_pairs = []

system_text = "You are Calamity AI, a disaster impact analysis assistant trained on historical disaster data from USGS, NASA EONET, EM-DAT, and HDX/ReliefWeb. Write cold, objective, highly analytical, and strictly factual impact assessments."

for i in range(1, 51):
    if i in drop_ids:
        continue
    p = prompts.get(i)
    r = responses.get(i)
    
    if not p or not r:
        continue
    
    # Strip the redundant system instruction from the V1 prompt
    p = re.sub(r'You are Calamity AI.*?NASA EONET, EM-DAT, and HDX/ReliefWeb\.', '', p, flags=re.DOTALL).strip()
    
    chatml = {
        "messages": [
            {
                "role": "system", 
                "content": system_text
            },
            {
                "role": "user",
                "content": p
            },
            {
                "role": "assistant",
                "content": r
            }
        ]
    }
    valid_pairs.append(chatml)

with open("calamity_training_data.jsonl", "w", encoding="utf-8") as f:
    for pair in valid_pairs:
        f.write(json.dumps(pair) + "\n")

print(f"Generated calamity_training_data.jsonl with {len(valid_pairs)} valid scenarios.")
