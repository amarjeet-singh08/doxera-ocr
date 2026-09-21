import re
with open(r'E:\Docket Dimension OCR\templates\dashboard.html', 'r') as f:
    text = f.read()
    hrefs = re.findall(r'href="[^"]+"', text)
    for h in set(hrefs):
        print(h)
