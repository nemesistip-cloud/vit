import re

with open('main.py', 'r') as f:
    content = f.read()

# Add missing imports for background workers
import_block = """
from app.tasks.ticker_sync import start_ticker_sync
from app.tasks.settlement_task import start_settlement_worker
from app.tasks.telegram_digest import start_telegram_digest
"""

if 'from app.tasks.ticker_sync import start_ticker_sync' not in content:
    content = content.replace('from app.services.firestore_events import setup_firestore_events',
                              'from app.services.firestore_events import setup_firestore_events' + import_block)

# Start workers in lifespan
worker_start_block = """
    start_ticker_sync()
    start_settlement_worker()
    start_telegram_digest()
"""

# Replace the single start_ticker_sync if it exists
if 'start_ticker_sync()' in content:
    content = content.replace('    start_ticker_sync()', worker_start_block)
else:
    # Append to the end of lifespan
    content = content.replace('print_config_status()', 'print_config_status()' + worker_start_block)

with open('main.py', 'w') as f:
    f.write(content)
