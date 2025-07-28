from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from utils.limiter import limiter
from config.db import db
from routers.chat import router as chat_router
from contextlib import asynccontextmanager
import aiosqlite
from utils.workflow import get_app

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's startup and shutdown events.
    """
    print("Application startup: Initializing resources...")
    conn = await aiosqlite.connect("checkpoint.sqlite")
    chat_app_instance = await get_app(conn)
    
    # Store the resources in the application's state.
    app.state.db_connection = conn
    app.state.chat_app = chat_app_instance
    print("Application startup complete.")
    
    yield # The application is now running
    
    print("Application shutdown: Cleaning up resources...")
    await app.state.db_connection.close()
    print("Database connection closed.")


app = FastAPI(
    title="Aryan Baghel's AI Assistant API",
    description="API for the conversational booking agent.",
    version="1.0.0",
    lifespan=lifespan
)

# middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_credentials=True,
    allow_headers=["*"],
    expose_headers=["Content-Type"],
)

app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])


# Connect on startup
@app.on_event("startup")
async def startup_db():
    db.connect()


# Disconnect on shutdown
@app.on_event("shutdown")
async def shutdown_db():
    db.close()


@app.get("/")
@limiter.limit("1/second")
def health_check(request: Request):
    return {"success": True, "message": "Server is healthy"}
