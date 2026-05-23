import re

with open("main.py", "r") as f:
    content = f.read()

# Remove the messy block
pattern = r'\n\n\s+if col not in user_col_names:.*?await conn\.execute\(text\(f"ALTER TABLE users ADD COLUMN {col} {ddl}"\)\)'
content = re.sub(pattern, '', content, flags=re.DOTALL)

with open("main.py", "w") as f:
    f.write(content)
