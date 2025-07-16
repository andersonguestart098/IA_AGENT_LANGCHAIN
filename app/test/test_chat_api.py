import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

# Simula um token de sessão válido
VALID_TOKEN = "f5f15217-f2c7-4547-95af-f4fdb2573057"

@pytest.mark.asyncio
async def test_chat_quero_orcamento_piso_vinilico():
    """
    Deve classificar corretamente como PEDIDO_ORCAMENTO,
    preencher os slots relevantes e retornar uma resposta coerente.
    """
    pergunta = "Quero orçamento de piso vinílico para Canoas"

    transport = ASGITransport(app=app)  # ✅ chave aqui
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/chat",
            headers={"Authorization": VALID_TOKEN},
            json={"pergunta": pergunta}
        )

    # ✅ Valida retorno HTTP
    assert response.status_code == 200, f"Status inesperado: {response.status_code}"
    data = response.json()

    # ✅ Valida intenção
    assert data["intencao"] == "PEDIDO_ORCAMENTO", f"Intenção Errada: {data['intencao']}"

    # ✅ Valida slots extraídos
    assert data["slots"]["produto"] == "piso vinílico", f"Produto slot falhou: {data['slots']['produto']}"
    assert data["slots"]["localidade"] == "Canoas", f"Localidade slot falhou: {data['slots']['localidade']}"
    assert data["slots"]["volume_aproximado"] is None
    assert data["slots"]["prazo"] is None

    # ✅ Valida resposta final
    assert any(term in data["resposta"].lower() for term in ["vendedor", "transferindo", "setor comercial"]), \
        f"Resposta incoerente: {data['resposta']}"

    # ✅ Valida etapa do fluxo
    assert data["etapa"] == "FINALIZADO", f"Etapa incorreta: {data['etapa']}"
