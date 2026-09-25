with open('excel_exporter.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix KeyError in export_all
text = text.replace("dim['width']", "dim['breadth']")
text = text.replace("dim['boxes_count']", "dim['num_packages']")

with open('excel_exporter.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("excel_exporter patched for width -> breadth")
