import asyncio
import subprocess
import sys
import os

# Runtime dependency check for Render environments
# We check and install multiple critical dependencies before any other imports
def install_dependencies():
    required = ["python-multipart", "sqlalchemy", "reedsolo", "aiofiles"]
    for pkg in required:
        try:
            if pkg == "python-multipart":
                import multipart
            elif pkg == "sqlalchemy":
                import sqlalchemy
            elif pkg == "reedsolo":
                import reedsolo
            elif pkg == "aiofiles":
                import aiofiles
        except ImportError:
            print(f"[tachyon] Installing missing dependency: {pkg}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

install_dependencies()

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from tachyon.api import router as api_router
from tachyon.core.worker import TachyonVerificationWorker

app = FastAPI(title="Storage System Coordination Service", version="1.0.0")

@app.get("/")
async def root():
    return RedirectResponse(url="/health")


@app.on_event("startup")
async def startup_event():
    worker = TachyonVerificationWorker(interval_seconds=3600)
    asyncio.create_task(worker.start())

@app.get("/health")
async def health():
    return {"status": "quantum_stable", "plane": "coordination"}

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
