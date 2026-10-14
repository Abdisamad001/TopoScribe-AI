import os

from dotenv import load_dotenv

load_dotenv()


def _setup_langwatch() -> None:
   
    api_key = os.getenv("LANGWATCH_API_KEY")
    if not api_key:
        return
    try:
        import langwatch
        from openinference.instrumentation.groq import GroqInstrumentor
        from openinference.instrumentation.openai import OpenAIInstrumentor

        langwatch.setup(
            api_key=api_key,
            instrumentors=[OpenAIInstrumentor(), GroqInstrumentor()],
        )
    except Exception as e:
        print(f"LangWatch setup skipped: {e}")



_setup_langwatch()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import (
    chats,
    clarify,
    design,
    projects,
    reports,
    saved_designs,
    simulate,
    topology,
)
from app.db import Base, engine

app = FastAPI(title="TopoScribe AI Backend")


@app.on_event("startup")
def create_tables():
   
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        print(f"Designs table setup skipped (database unreachable): {e}")

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
app.include_router(clarify.router, prefix="/api/design", tags=["design"]) 
app.include_router(simulate.router, prefix="/api/simulate", tags=["simulation"])
app.include_router(saved_designs.router, prefix="/api/designs", tags=["designs"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(chats.router, prefix="/api/chats", tags=["chats"])
app.include_router(topology.router, prefix="/api/topology", tags=["topology"])

@app.get("/")
def read_root():
    return {"status": "TopoScribe AI Backend Online"}
