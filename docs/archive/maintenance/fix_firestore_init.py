import sys

with open("main.py", "r") as f:
    content = f.read()

# Add import
import_line = "from app.services.firestore_events import setup_firestore_events"
if import_line not in content:
    content = content.replace("from app.auth.routes import router as auth_router",
                              f"{import_line}\nfrom app.auth.routes import router as auth_router")

# Add call in lifespan
setup_call = "    setup_firestore_events()"
if setup_call not in content:
    content = content.replace("    configure_logging(level=get_env(\"LOG_LEVEL\", \"INFO\"))",
                              f"    configure_logging(level=get_env(\"LOG_LEVEL\", \"INFO\"))\n{setup_call}")

with open("main.py", "w") as f:
    f.write(content)
