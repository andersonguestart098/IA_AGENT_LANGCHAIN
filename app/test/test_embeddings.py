import pytest
from app.services.embeddings import embedding_model

def test_embedding_generation():
    texto = "Teste de embedding simples"
    embedding = embedding_model.embed_documents([texto])[0]

    # ✅ Verifica que é uma lista de floats
    assert isinstance(embedding, list), "O embedding deve ser uma lista"
    assert all(isinstance(v, float) for v in embedding), "Todos os elementos devem ser floats"

    # ✅ Verifica o tamanho esperado (modelo all-MiniLM-L6-v2 = 384)
    assert len(embedding) == 384, f"Tamanho incorreto do embedding: {len(embedding)}"
