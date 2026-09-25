with open('routes_ops.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("with ThreadPoolExecutor(max_workers=2) as executor:", "with ThreadPoolExecutor(max_workers=4) as executor:")

with open('routes_ops.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("max_workers updated to 4")
