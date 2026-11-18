"""
Utility script to fetch Google Stitch screens and assets for Siddhanth Firm Bullion ERP.
Supports:
1. Direct asset URLs (HTML and PNG images)
2. Stitch MCP endpoint using an OAuth 2.0 Bearer token
"""
import os
import sys
import json
import base64
import urllib.request
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = "18152715679196764093"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stitch_screens")

SCREENS = [
    {
        "id": "598c7cf80cab4d5eb7328297eb9cbea4",
        "name": "executive_business_dashboard",
        "title": "Executive Business Dashboard - Siddhanth Firm"
    },
    {
        "id": "d7535747a20041479d5014fdd3531904",
        "name": "gold_testing_management",
        "title": "Gold Testing Management - Siddhanth Firm"
    },
    {
        "id": "e936f82854af4216a2ec8eb818d28fce",
        "name": "login",
        "title": "Login - Siddhanth Firm"
    }
]

def download_url(url, output_path):
    print(f"Downloading from {url} to {output_path}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(output_path, "wb") as f:
        f.write(resp.read())
    print(f"  Saved -> {output_path}")

def fetch_via_mcp(oauth_token):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {oauth_token}"
    }
    
    for screen in SCREENS:
        screen_id = screen["id"]
        slug = screen["name"]
        print(f"\n[Stitch MCP] Fetching screen: {screen['title']} ({screen_id})...")
        
        # 1. get_screen
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_screen",
                "arguments": {
                    "name": f"projects/{PROJECT_ID}/screens/{screen_id}"
                }
            }
        }
        req = urllib.request.Request(
            "https://stitch.googleapis.com/mcp",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"  Error calling get_screen for {slug}: {e}")
            continue

        result = data.get("result", {})
        print(f"  Response: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    token = os.getenv("STITCH_OAUTH_TOKEN")
    if token:
        fetch_via_mcp(token)
    else:
        print("Usage:")
        print("1. Set STITCH_OAUTH_TOKEN in .env or run with an OAuth 2.0 access token")
        print("2. Or pass direct URLs to download_url(url, path)")
