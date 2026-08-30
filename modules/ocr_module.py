import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

def analyze_document(image_path, query="Please extract all text and analyze the document."):
    """
    Uses an available Vision API (NVIDIA Nemotron or Google Gemini) to perform OCR and Document Intelligence.
    """
    nemotron_key = os.getenv("NEMOTRON_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("AI_API_KEY")
    
    if not nemotron_key and not gemini_key:
        return "No vision API key found. Please set NEMOTRON_API_KEY or GEMINI_API_KEY in .env"

    if not os.path.exists(image_path):
        return f"File not found: {image_path}"

    try:
        with open(image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
        
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/png")
        image_url = f"data:{mime_type};base64,{b64_data}"
        
        # Determine which API to use based on available keys
        if nemotron_key:
            invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
            token = nemotron_key
            model = "nvidia/llama-3.1-nemotron-nano-vl-8b-v1"
        else:
            invoke_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            token = gemini_key
            model = os.getenv("AI_MODEL", "gemini-2.5-flash")
            
        headers = {
            "Authorization": f"Bearer {token}",
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
            "model": model,
            "temperature": 0.1,
            "top_p": 1.0,
            "max_tokens": 2048,
            "stream": False
        }
        
        response = requests.post(invoke_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"Vision API Failed: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Failed to analyze document: {e}"
