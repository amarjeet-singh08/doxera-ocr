with open('ocr_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# 1. Reduce timeout from 60 to 25
text = re.sub(r"timeout=60", "timeout=25", text)

# 2. Refactor the retry loop
old_retry = """            # Fast failover retry loop
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

new_retry = """            # Advanced fast failover
            result = None
            error = None
            
            import random
            # Attempt 1
            result, error = self._call_model(model_config, base64_image)
            
            # If we get a LOCAL rate limit (429 but not UPSTREAM), do ONE quick retry with jitter
            if result is None and error and "429" in error and "UPSTREAM_OVERLOADED" not in error:
                time.sleep(1.5 + random.uniform(0, 1))
                result, error = self._call_model(model_config, base64_image)
            
            # For all other errors (Timeout, 502, 503, UPSTREAM_OVERLOADED), we instantly failover to the next model in the chain!
            # No pointless retries on dead/overloaded endpoints!"""

text = text.replace(old_retry, new_retry)

with open('ocr_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("ocr_engine.py fast failover logic modernized")
