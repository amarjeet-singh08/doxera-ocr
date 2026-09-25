with open('templates/exports.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
text = re.sub(r'<form class="space-y-4 mt-auto" action="(.*?)" method="GET" class="space-y-4">', r'<form class="space-y-4 mt-auto" action="\1" method="GET">', text)

with open('templates/exports.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("exports.html class double definition fixed")
