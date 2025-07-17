import pytest
from app.services.rag_chain import setup_rag_chain

# Token de sessão de teste válido (garanta que existe no banco)
VALID_TOKEN = "06fc2665-925d-4950-9595-b7d171019d6c"

@pytest.mark.asyncio
async def test_setup_rag_chain_components():
    """
    Deve montar corretamente todos os componentes do pipeline RAG,
    incluindo LLM, classificadores, embeddings e histórico.
    """
    resultado = await setup_rag_chain(sessao_token=VALID_TOKEN)

    # ✅ Conexão com banco
    assert resultado["prisma"] is not None, "Prisma não inicializado"

    # ✅ Sessão da conversa
    assert resultado["sessao"] is not None, "Sessão não encontrada"

    # ✅ Modelo LLM carregado
    assert resultado["llm"] is not None, "LLM não carregado"

    # ✅ Cadeias auxiliares
    assert resultado["classificacao_chain"] is not None, "Classificador não carregado"
    assert resultado["slot_filling_chain"] is not None, "Slot filler não carregado"
    assert resultado["rag_chain"] is not None, "RAG chain não carregada"

    # ✅ Histórico de conversa (pode ser vazio)
    assert isinstance(resultado["chat_history"], list), "Histórico de chat inválido"
