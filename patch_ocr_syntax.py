with open('ocr_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
text = text.replace(
    r'return f"OCR Error: All models failed to process the image. Detailed reasons: {\' | \'.join(errors)}"',
    'error_details = " | ".join(errors)\n        return f"OCR Error: All models failed to process the image. Detailed reasons: {error_details}"'
)

with open('ocr_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("ocr_engine.py syntax error fixed")
