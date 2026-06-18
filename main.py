from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Future endpoints (login, chat, collections) will be added here.
