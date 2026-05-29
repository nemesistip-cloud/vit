import os

PATH = "app/api/routes/admin.py"
with open(PATH, "r") as f:
    content = f.read()

# Add necessary imports if missing
imports = [
    "from sqlalchemy import select",
    "from app.db.database import AsyncSessionLocal",
    "from app.db.models import Match",
]

for imp in imports:
    if imp not in content:
        content = "from sqlalchemy import select\n" + content if "from sqlalchemy" not in content else content
        if "from app.db.database import AsyncSessionLocal" not in content:
            content = "from app.db.database import AsyncSessionLocal\n" + content
        if "from app.db.models import Match" not in content:
            content = "from app.db.models import Match\n" + content

with open(PATH, "w") as f:
    f.write(content)
