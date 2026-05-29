import sys

file_path = 'app/api/routes/admin_ai_sources.py'
with open(file_path, 'r') as f:
    content = f.read()

content = content.replace(
    'result = await generate_ai_prediction(\n            features, str(fixture_id), orchestrator, db=db\n        )',
    'result = await generate_ai_prediction(\n            features, str(fixture_id), "soccer", orchestrator, db=db\n        )'
)

with open(file_path, 'w') as f:
    f.write(content)
print("Successfully updated app/api/routes/admin_ai_sources.py")
