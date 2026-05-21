import re

with open("main.py", "r") as f:
    lines = f.readlines()

with open("main.py", "w") as f:
    for i, line in enumerate(lines):
        if 615 <= i + 1 <= 650:
             # Remove 16 leading spaces and add 4
             line = re.sub(r'^ {16}', '    ', line)
        f.write(line)
