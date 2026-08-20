from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import employees, projects, seats, dashboard, ai, auth

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Ethara Seat Allocation & Project Mapping System",
    description="API for managing employee seating, project mapping, and floor allocation at Ethara.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(projects.router)
app.include_router(seats.router)
app.include_router(dashboard.router)
app.include_router(ai.router)


@app.get("/")
def root():
    return {
        "message": "Ethara Seat Allocation & Project Mapping System API",
        "docs": "/docs",
        "health": "ok",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
