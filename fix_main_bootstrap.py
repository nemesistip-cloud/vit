import os

PATH = "main.py"
with open(PATH, "r") as f:
    content = f.read()

# Add AIInsight and PlatformConfig creation to bootstrap
search_text = 'await conn.run_sync(Base.metadata.create_all)'
replacement_text = """await conn.run_sync(Base.metadata.create_all)
            # Ensure AIInsight and PlatformConfig are explicitly created
            from app.modules.ai.models import AIInsight
            from app.modules.wallet.models import PlatformConfig
            await conn.run_sync(AIInsight.__table__.create, checkfirst=True)
            await conn.run_sync(PlatformConfig.__table__.create, checkfirst=True)"""

if search_text in content and replacement_text not in content:
    content = content.replace(search_text, replacement_text)

with open(PATH, "w") as f:
    f.write(content)
