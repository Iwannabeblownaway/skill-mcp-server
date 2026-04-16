"""FastAPI application entry point with MCP Streamable HTTP support."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import DatabasePool
from app.utils.redis_client import redis_client
from app.utils.logger import setup_logging, get_logger
from app.api.v1 import users, skills, auth, logs
from app.mcp.server import get_session_manager


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting application...")

    try:
        pool = await DatabasePool.get_pool()
        logger.info("Database pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")

    try:
        await redis_client.connect()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed (non-fatal): {e}")

    # Start the MCP session manager
    session_manager = get_session_manager()
    async with session_manager.run():
        logger.info("MCP session manager started")
        yield

    logger.info("Shutting down application...")
    await DatabasePool.close_pool()
    await redis_client.disconnect()


# Create FastAPI application
app = FastAPI(
    title="SKILL MCP Server",
    description="MCP protocol server for managing team skills",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create ASGI app for MCP that uses the session manager
from app.mcp.server import get_mcp_asgi_handler

mcp_asgi_handler = get_mcp_asgi_handler()

# Mount MCP at /mcp using FastAPI's mount
app.mount("/mcp", mcp_asgi_handler)


# Mount REST API routers
app.include_router(users.router, prefix="/api/v1")
app.include_router(skills.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "SKILL MCP Server",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    setup_logging()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
    )
