import os

PATH = "app/modules/ai/orchestrator.py"
with open(PATH, "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'sport: str = "soccer",' in line:
        new_lines.append('    sport: str,\n') # or just move it. Let's make it required or move it.
    else:
        new_lines.append(line)

# Actually let's just swap them
content = "".join(new_lines)
content = content.replace('    sport: str,', '    orchestrator: Any,')
content = content.replace('    orchestrator: Any,', '    sport: str = "soccer",', 1)

with open(PATH, "w") as f:
    f.write(content)
