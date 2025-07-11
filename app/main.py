from fastapi import FastAPI
from app.routes.chat import router as chat_router
from app.routes.upload import router as upload_router
from app.routes.login import router as login_router
from app.routes.register import router as register_router

app = FastAPI()

app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(login_router)
app.include_router(register_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
