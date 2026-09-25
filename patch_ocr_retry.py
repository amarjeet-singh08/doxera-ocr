with open('ocr_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
old_retry = """            # Rate limit retry loop
            max_retries = 3
            result = None
            error = None
            
            for attempt in range(max_retries):
                result, error = self._call_model(model_config, base64_image)
                if result is not None:
                    break
                
                if "429" in error or "402" in error:
                    time.sleep(2 ** attempt) # Exponential backoff (1s, 2s, 4s)
                else:
                    break # Don't retry non-rate-limit errors"""

new_retry = """            # Rate limit retry loop with jitter for high concurrency
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

if old_retry in text:
    text = text.replace(old_retry, new_retry)
else:
    print("Retry block not found!")

with open('ocr_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("ocr_engine.py retry logic enhanced")
