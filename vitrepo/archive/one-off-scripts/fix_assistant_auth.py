import re

with open('app/api/routes/ai_assistant.py', 'r') as f:
    content = f.read()

# Replace verify_api_key with get_current_user to allow standard logged-in users to use the assistant
content = content.replace('from app.api.middleware.auth import verify_api_key', 'from app.auth.dependencies import get_current_user')
content = content.replace('_user=Depends(verify_api_key)', '_user=Depends(get_current_user)')

with open('app/api/routes/ai_assistant.py', 'w') as f:
    f.write(content)
