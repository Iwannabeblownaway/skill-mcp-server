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
from app.admin.router import router as admin_router


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

# CORS middleware - development configuration
# For production, replace with specific origins like ["https://your-domain.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ],
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

# Mount admin panel
app.include_router(admin_router)


@app.get("/health")
async def health_check():
    """Health check endpoint with database and Redis connectivity checks."""
    health_status = {"status": "healthy", "checks": {}}

    # Check database
    try:
        pool = await DatabasePool.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"

    # Check Redis
    try:
        redis_ok = await redis_client.ping()
        health_status["checks"]["redis"] = "ok" if redis_ok else "error: ping failed"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = f"error: {str(e)}"

    return health_status


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
