import json
import os

def parse_openapi():
    file_path = "openapi.json"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"OpenAPI Title: {data.get('info', {}).get('title')}")
    print(f"OpenAPI Version: {data.get('info', {}).get('version')}")
    
    paths = data.get("paths", {})
    print(f"Total paths discovered: {len(paths)}")
    
    endpoints = []
    for path, methods in paths.items():
        for method, details in methods.items():
            # Check auth
            security = details.get("security", [])
            auth_req = "Yes (Bearer)" if security else "No"
            
            # Request schema
            req_schema = "None"
            if "requestBody" in details:
                content = details["requestBody"].get("content", {})
                if "application/json" in content:
                    schema_ref = content["application/json"].get("schema", {}).get("$ref", "")
                    req_schema = schema_ref.split("/")[-1] if schema_ref else "JSON Object"
            
            # Response schema
            resp_schema = "None"
            responses = details.get("responses", {})
            if "200" in responses:
                content = responses["200"].get("content", {})
                if "application/json" in content:
                    schema_ref = content["application/json"].get("schema", {}).get("$ref", "")
                    resp_schema = schema_ref.split("/")[-1] if schema_ref else "JSON Object"
            
            summary = details.get("summary", "")
            
            endpoints.append({
                "path": path,
                "method": method.upper(),
                "req_schema": req_schema,
                "resp_schema": resp_schema,
                "auth": auth_req,
                "summary": summary
            })
            
    # Print the first 20 endpoints as a preview
    for ep in endpoints[:20]:
        print(f"{ep['method']} {ep['path']} (Auth: {ep['auth']})")
        print(f"  Req: {ep['req_schema']} | Resp: {ep['resp_schema']}")
        
    # Write to a JSON file for easy loading in other scripts
    with open("backend/scratch/parsed_endpoints.json", "w", encoding="utf-8") as f:
        json.dump(endpoints, f, indent=2)
    print("Parsed endpoints saved to backend/scratch/parsed_endpoints.json")

if __name__ == "__main__":
    parse_openapi()
