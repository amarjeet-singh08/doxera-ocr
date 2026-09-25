with open('ocr_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
old_models = r"""MODEL_CHAIN = \[.*?\]"""
new_models = """MODEL_CHAIN = [
    {
        "id": "openrouter/free",
        "name": "OpenRouter Auto Free",
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
        "id": "qwen/qwen3.8-27b:free",
        "name": "Qwen 3.8 27B Vision",
        "free": True,
        "max_tokens": 4000,
        "tier": "FALLBACK"
    }
]"""
text = re.sub(old_models, new_models, text, flags=re.DOTALL)

with open('ocr_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("ocr_engine.py models updated to use openrouter/free")
