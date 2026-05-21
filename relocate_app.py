import sys

with open("main.py", "r") as f:
    lines = f.readlines()

lifespan_start = -1
lifespan_end = -1
app_def_line = -1

for i, line in enumerate(lines):
    if "async def lifespan(app: FastAPI):" in line:
        lifespan_start = i - 5 # include comments
    if lifespan_start != -1 and lifespan_end == -1 and i > lifespan_start and line.strip() == "" and (i+1 < len(lines) and lines[i+1].startswith("#")):
         lifespan_end = i
    if "app = FastAPI(" in line:
        app_def_line = i

# Find the end of lifespan more reliably
for i in range(lifespan_start + 5, len(lines)):
    if lines[i].startswith("# ============================================") or lines[i].startswith("app = FastAPI"):
        lifespan_end = i
        break
    if i > lifespan_start + 50: # safety
        lifespan_end = i
        break

# Extract the blocks
lifespan_block = lines[lifespan_start:lifespan_end]
app_block = lines[app_def_line : app_def_line + 5]

# Clean original lines
new_lines = []
skip_until = -1
for i, line in enumerate(lines):
    if i == lifespan_start:
        skip_until = lifespan_end
    if i == app_def_line:
        skip_until = app_def_line + 5

    if i < skip_until:
        continue
    new_lines.append(line)

# Insert at top (after imports, around line 55)
insert_pos = 55
final_lines = new_lines[:insert_pos] + ["\n"] + lifespan_block + ["\n"] + app_block + ["\n"] + new_lines[insert_pos:]

with open("main.py", "w") as f:
    f.writelines(final_lines)
