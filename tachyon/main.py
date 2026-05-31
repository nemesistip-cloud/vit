from fastapi import FastAPI
from tachyon.api import router as api_router

app = FastAPI(title="Tachyon Fabric Coordination Service", version="1.0.0")

@app.get("/health")
async def health():
    return {"status": "quantum_stable", "plane": "coordination"}

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
