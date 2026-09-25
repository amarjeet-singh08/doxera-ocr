with open('ocr_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
text = re.sub(
    r'return f"OCR Error: All models failed\. The AI servers might be at capacity or rate-limited\. Detailed reasons: \{\' \| \'\.join\(errors\)\}"',
    r'return f"OCR Error: All models failed to process the image. Detailed reasons: {\' | \'.join(errors)}"',
    text
)

with open('ocr_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("ocr_engine.py error message fixed")
