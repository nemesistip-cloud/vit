import asyncio
import subprocess
import sys
import os

# Runtime dependency check for Render environments
def install_dependencies():
    required = ["python-multipart", "sqlalchemy", "reedsolo", "aiofiles", "python-dotenv"]
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
            elif pkg == "python-dotenv":
                import dotenv
        except ImportError:
            print(f"[tachyon] Installing missing dependency: {pkg}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

install_dependencies()

# Load environment variables if dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from tachyon.api import router as api_router
from tachyon.core.worker import TachyonVerificationWorker
from app.db.database import AsyncSessionLocal

app = FastAPI(title="Storage System Coordination Service", version="1.0.0")

@app.get("/")
async def root():
    return RedirectResponse(url="/health")


@app.on_event("startup")
async def startup_event():
    # Load persistent providers from DB
    from tachyon.api.router import initialize_providers
    async with AsyncSessionLocal() as db:
        await initialize_providers(db)

    worker = TachyonVerificationWorker(interval_seconds=3600)
    asyncio.create_task(worker.start())

@app.get("/health")
async def health():
    return {"status": "quantum_stable", "plane": "coordination"}

@app.get("/metrics")
async def metrics():
    from tachyon.api.router import get_status
    async with AsyncSessionLocal() as db:
        status_data = await get_status(db=db)
    return {
        "status": "healthy",
        "bandwidth": status_data.get("network_bandwidth", "3.2 Tbps"),
        "active_nodes": status_data.get("active_nodes", 0),
        "manifest_count": status_data.get("manifest_count", 0),
        "disk": status_data.get("disk", {}),
    }

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    print(f"[tachyon] Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
