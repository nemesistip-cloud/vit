import sys

with open("main.py", "r") as f:
    content = f.read()

# Add import
import_line = "from app.tasks.ticker_sync import start_ticker_sync"
if import_line not in content:
    content = content.replace("from app.services.firestore_events import setup_firestore_events",
                              f"from app.services.firestore_events import setup_firestore_events\n{import_line}")

# Add call in lifespan
setup_call = "    start_ticker_sync()"
if setup_call not in content:
    content = content.replace("setup_firestore_events()",
                              f"setup_firestore_events()\n{setup_call}")

with open("main.py", "w") as f:
    f.write(content)
