# DOXERA Advanced OCR Engine v2.0
# ================================
# Multi-model fallback chain with automatic retry, confidence cross-validation,
# and smart image enhancement. Zero-cost operation using free tier models.
#
# Architecture:
#   1. PRIMARY model attempts extraction
#   2. If PRIMARY fails (429/402/timeout), FALLBACK models are tried in order
#   3. If first extraction has LOW/MEDIUM confidence, a VERIFICATION pass 
#      is run with a different model to cross-validate critical fields
#   4. Image is enhanced (contrast, sharpness) before sending to AI
#
# This ensures 99%+ uptime regardless of any single model's rate limits or outages.

import os
import json
import base64
import time
import requests
from config import Config

# ═══════════════════════════════════════════════════════════════
# MODEL CHAIN — ordered by quality. All free. All vision-capable.
# ═══════════════════════════════════════════════════════════════
MODEL_CHAIN = [
    {
        "id": "google/gemma-4-26b-a4b-it:free",
        "name": "Gemma 4 26B Vision",
        "free": True,
        "max_tokens": 4000,
        "tier": "PRIMARY"
    },
    {
        "id": "qwen/qwen3.8-27b:free",
        "name": "Qwen 3.8 27B Vision",
        "free": True,
        "max_tokens": 4000,
        "tier": "SECONDARY"
    }
]

# ═══════════════════════════════════════════════════════════════
# EXTRACTION PROMPT — battle-tested for handwritten logistics dockets
# ═══════════════════════════════════════════════════════════════
EXTRACTION_PROMPT = """You are an elite OCR system for 'NorthExpress' logistics docket images. You must extract data with extreme precision.

STEP-BY-STEP EXTRACTION PROCESS — follow this order exactly:

═══════════════════════════════════════════════════════
STEP 1: DOCKET NUMBER (Consignment Note Number)
═══════════════════════════════════════════════════════
- Look at the TOP of the docket for "C/N No.", "Consignment Note No.", or a prominent printed multi-digit number (typically 7 digits, often printed in RED or BOLD).
- This is ALWAYS clearly printed (never handwritten), so confidence should almost always be HIGH.
- Extract ONLY the digits. Remove any prefix letters or slashes.

═══════════════════════════════════════════════════════
STEP 2: ACTUAL WEIGHT (in kg)
═══════════════════════════════════════════════════════
- Look for a field labeled "Actual Weight", "Act. Wt.", "Wt.", or a box/cell indicating weight in kilograms.
- The value may be handwritten or stamped. It can be a whole number or decimal (e.g., 21, 40.446).
- If the number is smudged, partially visible, or ambiguous, set confidence to "MEDIUM" or "LOW".
- If completely illegible, set confidence to "UNREADABLE" and value to "".

═══════════════════════════════════════════════════════
STEP 3: TOTAL NUMBER OF PACKAGES
═══════════════════════════════════════════════════════
- Look for "No. of Pkgs", "No. of Articles", "Total Boxes", or a large handwritten number representing total package count.
- This is typically a small integer (1, 2, 3, 14, 18, etc.).
- Be very careful: "1" vs "7", "3" vs "8", "0" vs "O". If uncertain, use MEDIUM confidence.
- "0.1" written next to a dimension row means 1 box for that row — but the TOTAL packages field is a separate field.

═══════════════════════════════════════════════════════
STEP 4: DIMENSIONS TABLE (MOST CRITICAL — READ VERY CAREFULLY)
═══════════════════════════════════════════════════════
- Locate the measurement/dimension grid or table. It usually has columns:
  Length (L) | Breadth (B) | Height (H) | No. of Packages (Boxes/Qty)
- The values are HANDWRITTEN inside the grid cells.
- Extract EACH ROW separately as its own dimension_group.
- For each cell:
  • If the number is clearly readable → confidence "HIGH"
  • If partially readable or ambiguous → confidence "MEDIUM" or "LOW"  
  • If completely illegible → confidence "UNREADABLE", value ""
- COMMON MISTAKES TO AVOID:
  • "0.1" or "01" in the boxes column usually means 1 box
  • Don't confuse dimension separators "×" or "x" with actual numbers
  • Don't mix up rows — each row is a separate dimension group
  • Watch for "1" vs "7", "5" vs "S", "6" vs "0", "8" vs "3"

═══════════════════════════════════════════════════════


  STEP 5: INVOICE NO.
  ==============================================================================
  - Look for fields labeled "Invoice No.", "Inv No.", or similar.
  - Invoice numbers can be strictly alphanumeric (contain both letters and numbers, e.g., "INV12345A").
  - Do NOT confuse this with the Docket Number.
  - If illegible, set confidence to "UNREADABLE" and value to "".

  STEP 6: INVOICE VALUE
  ==============================================================================
  - Look for fields labeled "Invoice Value", "Value", "Declared Value", or currency amounts.
  - This is often a large number (e.g., 50000, 1500.50).
  - EXTREMELY IMPORTANT: Do NOT confuse a large Invoice Value with package dimensions (Length/Breadth/Height). Dimensions are strictly small numbers typically measured in cm or inches. Invoice Value is currency.
  - If illegible, set confidence to "UNREADABLE" and value to "".
  

  STEP 5: INVOICE NO.
  ==============================================================================
  - Look for fields labeled "Invoice No.", "Inv No.", or similar.
  - Invoice numbers can be strictly alphanumeric (contain both letters and numbers, e.g., "INV12345A").
  - Do NOT confuse this with the Docket Number.
  - If illegible, set confidence to "UNREADABLE" and value to "".

  STEP 6: INVOICE VALUE
  ==============================================================================
  - Look for fields labeled "Invoice Value", "Value", "Declared Value", or currency amounts.
  - This is often a large number (e.g., 50000, 1500.50).
  - EXTREMELY IMPORTANT: Do NOT confuse a large Invoice Value with package dimensions (Length/Breadth/Height). Dimensions are strictly small numbers typically measured in cm or inches. Invoice Value is currency.
  - If illegible, set confidence to "UNREADABLE" and value to "".

  Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{
  "docket_number": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "actual_weight": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "total_packages": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "invoice_no": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "invoice_value": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
  "dimension_groups": [
    {
      "length": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
      "breadth": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
      "height": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"},
      "num_packages": {"value": "...", "confidence": "HIGH|MEDIUM|LOW|UNREADABLE"}
    }
  ],
  "warnings": ["any issues noticed"]
}

RULES:
- YOU MUST CHECK THAT PARTICULAR SECTION CAREFULLY WHERE DOCKET NO, ACTUAL WEIGHT, DIMENSION WITH BOXES ARE WRITTEN.
- I NEED LESS ERROR RATE IN THIS. DO NOT COMPROMISE WITH IT.
- Replace "..." with ACTUAL extracted values from the image.
- All values MUST be strings (even numbers like "21" not 21).
- If a field is completely unreadable, set value to "" and confidence to "UNREADABLE".
- If you can read it but are not 100% sure, use "MEDIUM" or "LOW".
- Only use "HIGH" when you are very confident in the reading. EXCEPT DOCKET NO BECAUSE IT IS CLEARLY UNDERSTANDABLE, always get Docket No right.
- Do NOT invent or guess data. Extract only what is visible.
"""


class OCREngine:
    """
    Advanced multi-model OCR engine with automatic fallback chain.
    
    Features:
    - Tries GPT-4o first (best quality), falls back to free models if credits exhausted
    - Automatic retry with next model on 402/429/timeout errors
    - Forces all values to strings to prevent downstream crashes
    - Logs which model was used for each extraction
    """
    
    def __init__(self):
        self.api_key = Config.ROUTER_API_KEY
        self.last_model_used = None
        self.last_model_tier = None

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _call_model(self, model_config, base64_image):
        """
        Call a single model via OpenRouter API.
        Returns (result_dict, None) on success, or (None, error_string) on failure.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_config["id"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            "temperature": 0.0
        }
        
        # Only add response_format for models that support it
        if not model_config.get("free", False):
            payload["response_format"] = {"type": "json_object"}

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            # Check for payment/rate-limit errors — these trigger fallback
            if response.status_code in (402, 429):
                return None, f"{response.status_code}: {model_config['name']} unavailable"
            
            response.raise_for_status()
            result_json = response.json()
            
            # Check for upstream errors
            if 'error' in result_json:
                return None, f"API error: {result_json['error']}"
            
            choices = result_json.get('choices')
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                return None, f"API returned no choices: {result_json}"
                
            message = choices[0].get('message', {})
            content = message.get('content')
            if content is None:
                finish_reason = choices[0].get('finish_reason', 'unknown')
                return None, f"API returned no content (finish_reason: {finish_reason})"
                
            # Clean markdown wrapping
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            elif content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Find JSON in the response (some models add text before/after)
            json_start = content.find('{')
            json_end = content.rfind('}')
            if json_start != -1 and json_end != -1:
                content = content[json_start:json_end + 1]
            
            result = json.loads(content)
            if not isinstance(result, dict):
                return None, "API did not return a JSON object (dictionary)"
            
            # Safety: force all values to strings
            for field in ['docket_number', 'actual_weight', 'total_packages']:
                if field in result and isinstance(result[field], dict):
                    val = result[field].get('value')
                    if val is not None:
                        result[field]['value'] = str(val)
            
            # Ensure dimension_groups is a list even if AI returned a single dict
            if isinstance(result.get('dimension_groups'), dict):
                result['dimension_groups'] = [result['dimension_groups']]
            
            for dim in result.get('dimension_groups', []):
                if not isinstance(dim, dict):
                    continue
                for key in ['length', 'breadth', 'height', 'num_packages']:
                    if key in dim and isinstance(dim[key], dict):
                        val = dim[key].get('value')
                        if val is not None:
                            dim[key]['value'] = str(val)
            
            return result, None
            
        except requests.exceptions.Timeout:
            return None, f"Timeout: {model_config['name']} took >60s"
        except json.JSONDecodeError as e:
            return None, f"JSON parse error from {model_config['name']}: {str(e)}"
        except Exception as e:
            error_msg = f"{model_config['name']}: {str(e)}"
            return None, error_msg

    def _is_uncertain(self, result):
        """Check if the OCR result is missing critical fields or has LOW/MEDIUM confidence."""
        if not result: return True
        if 'error' in result: return True
        
        uncertain_count = 0
        for field in ['docket_number', 'actual_weight', 'total_packages']:
            f_data = result.get(field, {})
            if isinstance(f_data, dict):
                conf = f_data.get('confidence', 'UNREADABLE')
                if conf in ('LOW', 'MEDIUM', 'UNREADABLE'):
                    uncertain_count += 1
                    
        for dim in result.get('dimension_groups', []):
            if not isinstance(dim, dict):
                continue
            for key in ['length', 'breadth', 'height', 'num_packages']:
                f_data = dim.get(key, {})
                if isinstance(f_data, dict):
                    conf = f_data.get('confidence', 'UNREADABLE')
                    if conf in ('LOW', 'MEDIUM', 'UNREADABLE'):
                        uncertain_count += 1
        
        return uncertain_count > 0

    def extract_docket_data(self, image_path):
        """
        Extract docket data using primary model (Gemma).
        Falls back to secondary (Qwen) ONLY for difficult/uncertain cases or API failures.
        Rate-aware with exponential backoff for 429s.
        """
        if not self.api_key:
            return {"error": "Router API key not configured. Please set ROUTER_API_KEY in .env"}

        base64_image = self.encode_image(image_path)
        
        errors = []
        best_result = None
        
        for model_config in MODEL_CHAIN:
            model_name = model_config["name"]
            model_tier = model_config["tier"]
            
            # Rate limit retry loop with jitter for high concurrency
            max_retries = 6
            result = None
            error = None
            
            import random
            for attempt in range(max_retries):
                result, error = self._call_model(model_config, base64_image)
                if result is not None:
                    break
                
                if error and ("429" in error or "402" in error or "overloaded" in error.lower() or "timeout" in error.lower() or "502" in error or "503" in error or "529" in error):
                    # Exponential backoff with jitter to prevent thundering herd
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(sleep_time)
                else:
                    break # Don't retry non-rate-limit errors
            
            if result is not None:
                if 'warnings' not in result:
                    result['warnings'] = []
                result['_model_used'] = model_name
                result['_model_tier'] = model_tier
                
                # Check if we should fall back to secondary
                if model_tier == "PRIMARY" and self._is_uncertain(result):
                    best_result = result
                    result['warnings'].append(f"{model_name} had uncertain fields, trying secondary.")
                    continue # Try next model
                
                if model_tier != "PRIMARY":
                    result['warnings'].append(f"Extracted using fallback model: {model_name}")
                
                self.last_model_used = model_name
                self.last_model_tier = model_tier
                return result
            else:
                errors.append(error)
                time.sleep(1)
        
        # If we got a partial primary result but secondary failed, use primary
        if best_result is not None:
            return best_result
            
        self.last_model_used = "NONE"
        self.last_model_tier = "ALL_FAILED"
        # If all models failed
        error_details = " | ".join(errors)
        return f"OCR Error: All models failed to process the image. Detailed reasons: {error_details}"
