import re

with open("frontend/src/App.tsx", "r") as f:
    lines = f.readlines()

to_remove = [
    "jules-prompt", "iq-test", "wrapped", "stadium-mode", "oracle-mic",
    "discipline-coach", "quality-feed", "debate-markets", "bet-rooms",
    "node-network", "prophecy-chain"
]

new_lines = []
for line in lines:
    if any(p in line for p in to_remove) and "const " in line and "lazyRetry" in line:
        continue
    new_lines.append(line)

with open("frontend/src/App.tsx", "w") as f:
    f.writelines(new_lines)
