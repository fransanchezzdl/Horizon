import re

# Leer archivo
with open('backend/models/train_xgboost_all.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Buscar líneas con caracteres no-ASCII
problematic_lines = []
for line_num, line in enumerate(lines, 1):
    for char in line:
        if ord(char) > 127:
            # Mostrar línea y carácter
            problematic_lines.append((line_num, repr(char), ord(char), line.rstrip()[:100]))
            break

for line_num, char, code, content in problematic_lines:
    print(f"L{line_num}: {char} (U+{code:04X}) - {content}")

print(f"\nTotal líneas con non-ASCII: {len(set(x[0] for x in problematic_lines))}")
