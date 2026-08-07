from main import app
import json

openapi = app.openapi()
op = openapi['paths'].get('/api/ai-engine/models/register')
print(json.dumps(op, indent=2))
