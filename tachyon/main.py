import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from tachyon.api import router as api_router

app = FastAPI(title="Storage System Coordination Service", version="1.0.0")

@app.get("/")
async def root():
    return RedirectResponse(url="/health")

@app.get("/health")
async def health():
    return {"status": "quantum_stable", "plane": "coordination"}

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
