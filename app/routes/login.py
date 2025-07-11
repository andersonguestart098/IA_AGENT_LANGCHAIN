from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.generated.client import Prisma
import uuid

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    nome: str = "Usuário"

class LoginResponse(BaseModel):
    token: str
    usuario_id: int
    nome: str
    email: str

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    prisma = Prisma()
    await prisma.connect()

    # 🔹 Verifica se o usuário já existe
    usuario = await prisma.usuario.find_unique(where={"email": request.email})

    # 🔹 Se não existir, cria
    if not usuario:
        usuario = await prisma.usuario.create(data={
            "email": request.email,
            "nome": request.nome
        })

    # 🔹 Cria nova sessão
    token = str(uuid.uuid4())
    await prisma.sessao.create(data={
        "token": token,
        "usuarioId": usuario.id
    })

    await prisma.disconnect()

    return LoginResponse(
        token=token,
        usuario_id=usuario.id,
        nome=usuario.nome or "",
        email=usuario.email or ""
    )
