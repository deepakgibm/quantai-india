import os
import json

RESULTS_DIR = r"c:\Users\Deepak Kumar\Downloads\quantai-india\tests\api_results_after_fix"
OUTPUT_FILE = r"c:\Users\Deepak Kumar\Downloads\quantai-india\docs\api_failure_matrix_post_fix.md"

matrix = []

for filename in os.listdir(RESULTS_DIR):
    if filename.endswith(".json"):
        with open(os.path.join(RESULTS_DIR, filename), 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            if 200 <= data["status_code"] < 300:
                continue
            
            error_msg = str(data["response_payload"].get("detail", data["response_payload"].get("message", "Unknown Error")))
            
            category = "Unhandled exception"
            if data["status_code"] == 404:
                category = "Incorrect path / Router not mounted"
            elif "not authenticated" in error_msg.lower() or "token" in error_msg.lower():
                category = "Authentication / authorization issue"
            elif "syntax error" in error_msg.lower() or "column" in error_msg.lower() or "table" in error_msg.lower():
                category = "Database error"
            elif "import name" in error_msg.lower() or "not defined" in error_msg.lower():
                category = "External dependency failure"
            elif "validation" in error_msg.lower() or "missing" in error_msg.lower():
                category = "Missing or invalid request validation"
            
            matrix.append(f"| {data['api_name']} | {data['status_code']} | {category} | `{error_msg[:100]}` |")

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write("# Post-Fix API Failure Matrix\n\n| API Name | Status | Category | Error Evidence |\n|---|---|---|---|\n")
    f.write("\n".join(matrix))

print(f"Generated failure matrix for {len(matrix)} APIs")
