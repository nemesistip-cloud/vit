import re

with open('main.py', 'r') as f:
    content = f.read()

# Add import
content = content.replace('from app.tasks.settlement_task import start_settlement_worker',
                          'from app.tasks.settlement_task import start_settlement_worker\nfrom app.tasks.telegram_digest import start_telegram_digest')

# Start worker
content = content.replace('start_settlement_worker()', 'start_settlement_worker()\n    start_telegram_digest()')

with open('main.py', 'w') as f:
    f.write(content)
