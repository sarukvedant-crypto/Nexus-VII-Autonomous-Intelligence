import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()
NEMOTRON_API_KEY = os.getenv("NEMOTRON_API_KEY")

def analyze_document(image_path, query="Please extract all text and analyze the document."):
    """
    Uses NVIDIA Nemotron API to perform advanced OCR and Document Intelligence on an image.
    """
    if not NEMOTRON_API_KEY:
        return "NEMOTRON_API_KEY not configured in .env"

    if not os.path.exists(image_path):
        return f"File not found: {image_path}"

    try:
        with open(image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
        
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/png")
        image_url = f"data:{mime_type};base64,{b64_data}"
        
        invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {NEMOTRON_API_KEY}",
            "Accept": "application/json",
        }
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        },
                        {
                            "type": "text",
                            "text": query
                        }
                    ]
                }
            ],
            "model": "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
            "temperature": 0.1,
            "top_p": 1.0,
            "max_tokens": 2048,
            "stream": False
        }
        
        response = requests.post(invoke_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"Nemotron API Failed: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Failed to analyze document: {e}"
