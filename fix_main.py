import sys
import re

with open("main.py", "r") as f:
    content = f.read()

# Remove the incorrectly inserted blocks
# (Searching for the pattern of the messy insert)
content = re.sub(r'\n\n# ============================================\n# LIFECYCLE\n# ============================================\n\n@asynccontextmanager.*?\n\napp = FastAPI\(.*?\)\n\n', '', content, flags=re.DOTALL)

# Also remove them if they exist anywhere else
content = re.sub(r'@asynccontextmanager\s+async def lifespan\(app: FastAPI\):.*?# Shutdown complete', '', content, flags=re.DOTALL)
content = re.sub(r'app = FastAPI\(.*?\)', '', content, flags=re.DOTALL)

lines = content.splitlines()
new_lines = []
inserted = False

for line in lines:
    new_lines.append(line)
    if "from app.config import get_env, APP_VERSION, print_config_status" in line and not inserted:
        new_lines.append("\n@asynccontextmanager")
        new_lines.append("async def lifespan(app: FastAPI):")
        new_lines.append("    from app.core.logging_config import configure_logging")
        new_lines.append("    configure_logging(level=get_env('LOG_LEVEL', 'INFO'))")
        new_lines.append("    print_config_status()")
        new_lines.append("    print(f'🚀 VIT Network v{APP_VERSION} starting...')")
        new_lines.append("    from app.agents.coordinator import get_coordinator")
        new_lines.append("    coordinator = get_coordinator()")
        new_lines.append("    tasks = coordinator.start()")
        new_lines.append("    yield")
        new_lines.append("    print('🛑 VIT Network shutting down...')")
        new_lines.append("    await coordinator.stop()")
        new_lines.append("    for task in tasks:")
        new_lines.append("        task.cancel()")
        new_lines.append("    await asyncio.gather(*tasks, return_exceptions=True)")
        new_lines.append("    print('🛑 Shutdown complete')\n")
        new_lines.append("app = FastAPI(")
        new_lines.append("    title='VIT Sports Intelligence Network',")
        new_lines.append("    version=APP_VERSION,")
        new_lines.append("    lifespan=lifespan,")
        new_lines.append(")\n")
        inserted = True

with open("main.py", "w") as f:
    f.write("\n".join(new_lines))
