import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.generated.client import Prisma

@pytest.mark.asyncio
async def test_login_cria_usuario_e_sessao():
    """
    Deve criar um novo usuário e gerar um token de sessão.
    """
    prisma = Prisma()
    await prisma.connect()

    # 🔹 Garante que o usuário não exista
    await prisma.usuario.delete_many(where={"email": "novoteste@exemplo.com"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/login", json={
            "email": "novoteste@exemplo.com",
            "nome": "Novo Teste"
        })

    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["email"] == "novoteste@exemplo.com"
    assert data["nome"] == "Novo Teste"
    assert isinstance(data["usuario_id"], int)

    await prisma.disconnect()


@pytest.mark.asyncio
async def test_login_usuario_existente():
    """
    Deve reutilizar usuário existente e criar nova sessão.
    """
    prisma = Prisma()
    await prisma.connect()

    # 🔹 Cria usuário previamente
    email = "existe@exemplo.com"
    usuario = await prisma.usuario.find_unique(where={"email": email})
    if usuario:
        await prisma.usuario.update(
            where={"email": email},
            data={"nome": "Já Existe"}
        )
    else:
        await prisma.usuario.create(
            data={"email": email, "nome": "Já Existe"}
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/login", json={
            "email": email,
            "nome": "Ignorado"
        })

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["nome"] == "Já Existe"
    assert "token" in data
    assert isinstance(data["usuario_id"], int)

    await prisma.disconnect()
