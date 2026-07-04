import re

with open('app/api/routes/predict.py', 'r') as f:
    content = f.read()

# Fix potential division by zero in ensemble weight aggregation
# I'll look for where weights are aggregated.
# In ModelOrchestrator.predict, usually there's a sum of weights.

# I'll check for any division in predict.py first
