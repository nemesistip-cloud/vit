import re

with open('main.py', 'r') as f:
    content = f.read()

# Add missing imports if not already there
needed_imports = [
    'from app.tasks.ticker_sync import start_ticker_sync',
    'from app.tasks.settlement_task import start_settlement_worker',
    'from app.tasks.telegram_digest import start_telegram_digest'
]

for imp in needed_imports:
    if imp not in content:
        content = content.replace('from app.services.firestore_events import setup_firestore_events',
                                  'from app.services.firestore_events import setup_firestore_events\n' + imp)

with open('main.py', 'w') as f:
    f.write(content)
