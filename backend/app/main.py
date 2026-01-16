from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import design, clarify, simulate

app = FastAPI(title="TopoScribe AI Backend")

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(design.router, prefix="/api/design", tags=["design"])
app.include_router(clarify.router, prefix="/api/design", tags=["design"]) # Mounted at /api/design/clarify by router decoration? No, router has /clarify. Prefix adds /api/design -> /api/design/clarify
app.include_router(simulate.router, prefix="/api/simulate", tags=["simulation"])

@app.get("/")
def read_root():
    return {"status": "TopoScribe AI Backend Online"}
