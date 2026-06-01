import sys

with open('main.py', 'r') as f:
    lines = f.readlines()

# Clean up any duplicate registration for basketball/tennis if it exists
filtered_lines = []
skip_manual = False
for line in lines:
    if '# Manual registration for missed sports routers' in line:
        skip_manual = True
        continue
    if skip_manual and ('basketball' in line or 'tennis' in line or 'app.include_router' in line):
        if 'app.include_router' in line and 'basketball_route' not in line and 'tennis_route' not in line:
             skip_manual = False # End of manual block
        else:
             continue
    if not skip_manual:
        filtered_lines.append(line)

lines = filtered_lines

# Find insertion point for imports
import_idx = -1
for i, line in enumerate(lines):
    if 'from app.api.routes import (' in line:
        # Found the core routes import block
        for j in range(i+1, len(lines)):
            if ')' in lines[j]:
                import_idx = j
                break
        break

if import_idx != -1:
    # Check if they are already there
    has_basketball = any('basketball' in line for line in lines[:import_idx+1])
    if not has_basketball:
        # Insert basketball and tennis into the multi-line import
        lines.insert(import_idx, "    basketball, tennis,\n")

# Find insertion point for routers
router_idx = -1
for i, line in enumerate(lines):
    if 'app.include_router(ai_assistant_route.router' in line:
        router_idx = i + 1
        break

if router_idx != -1:
    # Check if already included
    if not any('basketball.router' in line for line in lines):
        lines.insert(router_idx, 'app.include_router(basketball.router, prefix="/api")\n')
        lines.insert(router_idx + 1, 'app.include_router(tennis.router, prefix="/api")\n')

with open('main.py', 'w') as f:
    f.writelines(lines)
