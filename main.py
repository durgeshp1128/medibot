
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel



# Duplicate login endpoint removed
from datetime import datetime, timedelta
from typing import Optional
import os
import json
from jose import JWTError, jwt
from chat_flow import process_chat

# Simple in‑memory user store for demo purposes
_USERS = {
    "alice": {"username": "alice", "password": "@Secret123", "role": "admin"},
    "bob": {"username": "bob", "password": "@Password123", "role": "billing_executive"},
    "dr.mehta": {"username": "dr.mehta", "password": "@doctor123", "role": "doctor"},
    "nurse.priya": {"username": "nurse.priya", "password": "@Nurse123", "role": "nurse"},
    "billing.ravi": {"username": "billing.ravi", "password": "@Billing123", "role": "billing_executive"},
    "tech.anand": {"username": "tech.anand", "password": "@Tech123", "role": "technician"},
    "admin.sys": {"username": "admin.sys", "password": "@Admin123", "role": "admin"}
}

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = _USERS.get(username)
    if user is None:
        raise credentials_exception
    return user

@app.get("/health")
async def health_check():
    return {"status": "ok"}

class LoginRequest(BaseModel):
    username: str
    password: str

class QuestionRequest(BaseModel):
    question: str

@app.post("/login")
async def login(data: LoginRequest):
    # Normalize username to lowercase for case‑insensitive lookup
    print('Login attempt:', data.username, data.password)
    lookup_name = data.username.split("@")[0].lower() if "@" in data.username else data.username.lower()
    user = _USERS.get(lookup_name)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    return {"access_token": access_token, "token_type": "bearer"}



@app.post("/chat")

async def chat_endpoint(question: QuestionRequest, current_user: dict = Depends(get_current_user)):
    # Prepare payload for process_chat
    payload = {"question": question.question}
    result = process_chat(payload, current_user)
    return result

@app.post("/sql_rag")
async def sql_rag_endpoint(question: QuestionRequest, current_user: dict = Depends(get_current_user)):
    from sql_rag import sql_rag_chain
    answer = sql_rag_chain(question.question, current_user.get("role"))
    return {"answer": answer}
