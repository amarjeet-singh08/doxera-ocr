with open('ocr_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# 1. Update Models
old_models = r"""MODEL_CHAIN = \[.*?\]"""
new_models = """MODEL_CHAIN = [
    {
        "id": "nex-agi/nex-n2.5-pro:free",
        "name": "Nex N2.5 Pro Vision",
        "free": True,
        "max_tokens": 4000,
        "tier": "PRIMARY"
    },
    {
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "name": "Nemotron Nano Omni",
        "free": True,
        "max_tokens": 4000,
        "tier": "SECONDARY"
    },
    {
        "id": "google/gemma-4-26b-a4b-it:free",
        "name": "Gemma 4 26B Vision",
        "free": True,
        "max_tokens": 4000,
        "tier": "FALLBACK"
    }
]"""
text = re.sub(old_models, new_models, text, flags=re.DOTALL)

# 2. Extract better error
old_429 = """            # Check for payment/rate-limit errors — these trigger fallback
            if response.status_code in (402, 429):
                return None, f"{response.status_code}: {model_config['name']} unavailable\""""
new_429 = """            # Check for payment/rate-limit errors — these trigger fallback
            if response.status_code in (402, 429):
                try:
                    err_json = response.json()
                    if 'error' in err_json and 'metadata' in err_json['error'] and err_json['error']['metadata'].get('limit_source') == 'upstream_provider_shared_pool':
                        return None, f"UPSTREAM_OVERLOADED: {model_config['name']} pool exhausted"
                except:
                    pass
                return None, f"{response.status_code}: {model_config['name']} unavailable\""""
text = text.replace(old_429, new_429)

# 3. Reduce retries and handle UPSTREAM_OVERLOADED
old_retry = """            # Rate limit retry loop with jitter for high concurrency
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
                    break # Don't retry non-rate-limit errors"""

new_retry = """            # Fast failover retry loop
            max_retries = 2
            result = None
            error = None
            
            import random
            for attempt in range(max_retries):
                result, error = self._call_model(model_config, base64_image)
                if result is not None:
                    break
                
                # If upstream pool is exhausted, DO NOT wait, instantly failover to next model
                if error and "UPSTREAM_OVERLOADED" in error:
                    break
                    
                if error and ("429" in error or "402" in error or "overloaded" in error.lower() or "timeout" in error.lower() or "502" in error or "503" in error or "529" in error):
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(sleep_time)
                else:
                    break"""
text = text.replace(old_retry, new_retry)

with open('ocr_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("ocr_engine.py fully patched for fast failover!")
