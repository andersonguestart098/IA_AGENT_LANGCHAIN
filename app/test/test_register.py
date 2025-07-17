import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.generated.client import Prisma


@pytest.mark.asyncio
async def test_register_novo_usuario():
    """
    Deve registrar um novo usuário com sucesso.
    """
    prisma = Prisma()
    await prisma.connect()

    # 🔹 Limpa se já existir (garantia de teste limpo)
    await prisma.usuario.delete_many(where={"email": "teste@exemplo.com"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/register", json={
            "nome": "Usuário Teste",
            "email": "teste@exemplo.com",
            "senha": "senha123"
        })

    assert response.status_code == 200
    data = response.json()
    assert data["mensagem"] == "Usuário registrado com sucesso"
    assert data["email"] == "teste@exemplo.com"
    assert "id" in data

    await prisma.disconnect()


@pytest.mark.asyncio
async def test_register_email_existente():
    """
    Deve retornar erro 400 ao tentar registrar com email já existente.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/register", json={
            "nome": "Outro Nome",
            "email": "teste@exemplo.com",  # Mesmo email do teste anterior
            "senha": "outrasenha"
        })

    assert response.status_code == 400
    assert response.json()["detail"] == "Email já registrado."
