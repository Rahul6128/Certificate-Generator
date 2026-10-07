from fastapi import FastAPI

from app.database import Base, engine
from app.routers import jobs, certificates

# create tables on startup - fine for sqlite/assignment scope, would use
# Alembic migrations for a real production app
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bulk Certificate Generator",
    description="Accepts a batch of recipients and generates certificates against a fixed template.",
    version="1.0.0",
)

app.include_router(jobs.router)
app.include_router(certificates.router)


@app.get("/health")
def health():
    return {"status": "ok"}
