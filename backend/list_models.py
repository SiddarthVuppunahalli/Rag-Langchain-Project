import os
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv(".env")
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("GOOGLE_API_KEY not found.")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

print("Available generative models:")
try:
    with urllib.request.urlopen(url) as req:
        data = json.loads(req.read().decode())
        for model in data.get('models', []):
            if 'generateContent' in model.get('supportedGenerationMethods', []):
                print(f" - {model['name']}")
except Exception as e:
    print(f"Error calling list_models: {e}")
