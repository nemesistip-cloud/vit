import re

with open("frontend/src/App.tsx", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if skip:
        if '</Layout></Route>' in line or '</Route>' in line:
            skip = False
        continue

    # Identify routes to delete
    if any(p in line for p in [
        'path="/stadium"', 'path="/jules-prompt"', 'path="/iq-test"',
        'path="/oracle-mic"', 'path="/wrapped"', 'path="/discipline-coach"',
        'path="/quality-feed"', 'path="/debates"', 'path="/rooms"',
        'path="/node-network"', 'path="/prophecy"'
    ]):
        skip = True
        continue

    new_lines.append(line)

with open("frontend/src/App.tsx", "w") as f:
    f.writelines(new_lines)
