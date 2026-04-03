from fastapi import FastAPI
from Opr.router import router

app = FastAPI(title="C Service")
app.include_router(router)