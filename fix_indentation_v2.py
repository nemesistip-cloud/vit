import re

with open("main.py", "r") as f:
    lines = f.readlines()

with open("main.py", "w") as f:
    for i, line in enumerate(lines):
        # Fix lines 615 to 700
        if 615 <= i + 1 <= 700:
             # If line starts with 16 spaces, replace them with 8
             line = re.sub(r'^ {16}', '        ', line)
             # If it starts with 4, maybe it was a top level try I moved
             # This is tricky.
        f.write(line)
