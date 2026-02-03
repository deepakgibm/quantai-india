import os
import json

RESULTS_DIR = r"c:\Users\Deepak Kumar\Downloads\quantai-india\tests\api_results"
OUTPUT_FILE = r"c:\Users\Deepak Kumar\Downloads\quantai-india\docs\api_performance_diagnosis.md"

diagnosis = []

for filename in os.listdir(RESULTS_DIR):
    if filename.endswith(".json"):
        with open(os.path.join(RESULTS_DIR, filename), 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            if data["response_time_ms"] <= 200:
                continue
            
            api_name = data["api_name"]
            time = data["response_time_ms"]
            
            obs = "High computation or blocking IO detected."
            if "ai_get" in api_name or "scanner" in api_name:
                obs = "Sequential technical analysis computation for multiple symbols in request loop."
            elif "agentic" in api_name:
                obs = "LLM/Agentic reasoning delay."
            
            diagnosis.append(f"| {api_name} | {data['method']} | {time} | {obs} |")

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write("# API Performance Diagnosis\n\n| API Name | Method | Time (ms) | Observations |\n|---|---|---|---|\n")
    f.write("\n".join(diagnosis))

print(f"Generated performance diagnosis for {len(diagnosis)} APIs")
