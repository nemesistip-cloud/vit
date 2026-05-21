with open("main.py", "r") as f:
    lines = f.readlines()

# Positions (0-indexed)
lifespan_range = range(593, 633)
app_range = range(1949, 1954)

lifespan_block = [lines[i] for i in lifespan_range]
app_block = [lines[i] for i in app_range]

new_lines = []
for i, line in enumerate(lines):
    if i in lifespan_range or i in app_range:
        continue
    new_lines.append(line)
    if i == 23: # Insertion point
        new_lines.append("\n")
        new_lines.extend(lifespan_block)
        new_lines.append("\n")
        new_lines.extend(app_block)
        new_lines.append("\n")

with open("main.py", "w") as f:
    f.writelines(new_lines)
