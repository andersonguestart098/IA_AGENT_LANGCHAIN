from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.generated.client import Prisma
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class RegisterRequest(BaseModel):
    nome: str
    email: EmailStr
    senha: str

@router.post("/register")
async def register(request: RegisterRequest):
    prisma = Prisma()
    await prisma.connect()

    # Verifica se já existe usuário com esse email
    existing = await prisma.usuario.find_unique(where={"email": request.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email já registrado.")

    # Criptografa a senha
    hashed = pwd_context.hash(request.senha)

    # Cria o usuário
    user = await prisma.usuario.create(data={
        "nome": request.nome,
        "email": request.email,
        "senha_hash": hashed
    })

    await prisma.disconnect()
    return {
        "id": user.id,
        "email": user.email,
        "nome": user.nome,
        "mensagem": "Usuário registrado com sucesso"
    }
