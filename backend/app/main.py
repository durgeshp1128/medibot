from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict
# Hardcoded configuration (replaces pydantic Settings)
PROJECT_NAME = "MediBot"
API_V1_STR = "/api/v1"
BACKEND_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
from app.api.endpoints import chat, collections  # Auth router removed

# Initialize the FastAPI Application
app = FastAPI(
    title=PROJECT_NAME,
    openapi_url=f"{API_V1_STR}/openapi.json",
    description="Production‑grade backend orchestration engine for MediBot.",
    version="1.0.0",
)

# Configure CORS Middleware for React 18+ (Vite) development
# Allow the Vite dev server (http://localhost:5173) and any origins defined in settings.
#    *[str(origin).rstrip("/") for origin in BACKEND_CORS_ORIGINS] to your actual domain(s).
allowed_origins = BACKEND_CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health Check"])
def root_health_check():
    """
    Basic service availability verification route.
    Used by internal health checks, Docker, or orchestrators.
    """
    return {
        "status": "healthy",
        "project": PROJECT_NAME,
        "version": "1.0.0"
    }
# ----------------------------------------------------------------------
# Simplified authentication endpoint (hard‑coded demo user)
# ----------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

# _DEMO_USERS = {
#     "admin.sys": {"password": "admin123", "role": "admin"},
# }
_DEMO_USERS: Dict[str, Dict[str, str]] = {
    "dr.mehta": {"password": "doctor123", "role": "doctor"},
    "nurse.priya": {"password": "nurse123", "role": "nurse"},
    "billing.ravi": {"password": "billing123", "role": "billing_executive"},
    "tech.anand": {"password": "tech123", "role": "technician"},
    "admin.sys": {"password": "admin123", "role": "admin"},
}

@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(request: LoginRequest):
    user = _DEMO_USERS.get(request.username)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token="demo-token", role=user["role"])

# Include remaining modular API routers
app.include_router(chat.router, prefix=f"{API_V1_STR}/chat", tags=["Chat Orchestration"])
app.include_router(collections.router, prefix=f"{API_V1_STR}/collections", tags=["Collections"])

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)