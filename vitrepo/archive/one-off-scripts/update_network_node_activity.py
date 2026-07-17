import re

with open('app/modules/network/routes.py', 'r') as f:
    content = f.read()

# Make sure NodeActivity is imported or defined
# I'll check models.py for NodeActivity
