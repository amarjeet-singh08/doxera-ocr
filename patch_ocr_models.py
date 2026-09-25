with open('ocr_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
old_models = """MODEL_CHAIN = [
    {
        "id": "inclusionai/ling-3.0-flash-vl:free",
        "name": "Ling 3.0 Flash Vision",
        "free": True,
        "max_tokens": 4000,
        "tier": "PRIMARY"
    }
]"""

new_models = """MODEL_CHAIN = [
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
]"""

if old_models in text:
    text = text.replace(old_models, new_models)
else:
    print("WARNING: MODEL_CHAIN not found in ocr_engine.py")

with open('ocr_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("ocr_engine.py models updated")
