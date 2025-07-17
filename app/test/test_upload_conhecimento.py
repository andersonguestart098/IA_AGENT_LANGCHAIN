import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status
from app.main import app


@pytest.mark.asyncio
async def test_upload_conhecimento_txt(tmp_path):
    """
    Deve aceitar upload de arquivo .txt, dividir em chunks,
    salvar embeddings e retornar resposta de sucesso.
    """
    # 🔹 Cria arquivo temporário com conteúdo de teste
    test_text = "Linha 1\nLinha 2\nLinha 3\n" * 50
    file_path = tmp_path / "teste.txt"
    file_path.write_text(test_text, encoding="utf-8")

    # 🔹 Realiza chamada para o endpoint com transporte local
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with open(file_path, "rb") as f:
            response = await ac.post(
                "/upload-conhecimento",
                files={"file": ("teste.txt", f, "text/plain")}
            )

    # 🔹 Valida resposta HTTP
    assert response.status_code == status.HTTP_200_OK, f"Status inesperado: {response.status_code}"
    data = response.json()

    # 🔹 Valida resposta esperada
    assert data["status"] == "sucesso"
    assert data["chunks_salvos"] > 0
    assert data["origem"] == "teste.txt"
