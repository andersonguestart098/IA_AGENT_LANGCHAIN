from fastapi import APIRouter, UploadFile, File, HTTPException
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.services.embeddings import embedding_model
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from langchain_community.vectorstores.qdrant import Qdrant as LangchainQdrant

import json
import os

router = APIRouter()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = "cemear_knowledge_base"

@router.post("/upload-conhecimento")
async def upload_conhecimento(file: UploadFile = File(...)):
    try:
        content = await file.read()

        try:
            dados = json.loads(content.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erro ao ler JSON: {e}")

        if not isinstance(dados, list):
            raise HTTPException(status_code=400, detail="JSON deve ser uma lista de objetos.")

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        total_chunks = 0
        documentos = []

        for item in dados:
            conteudo = item.get("conteudo")
            if not conteudo:
                continue

            # 🔹 Filtra apenas metadados simples (str, int, float, bool)
            metadados = {
                k: v for k, v in item.items()
                if k != "conteudo" and isinstance(v, (str, int, float, bool))
            }

            # 🔸 Garante que 'categoria' esteja presente e normalizada
            categoria = metadados.get("categoria", "geral")
            if isinstance(categoria, str):
                categoria = categoria.strip().lower()
            else:
                categoria = "geral"
            metadados["categoria"] = categoria

            # 🔹 Divide o conteúdo em chunks e aplica os metadados no nível raiz
            chunks = splitter.create_documents([conteudo], metadatas=[metadados])
            documentos.extend(chunks)
            total_chunks += len(chunks)

        # 🔹 Cria cliente Qdrant
        qdrant_client = QdrantClient(url=QDRANT_URL)

        # 🔹 Descobre tamanho do vetor dinamicamente
        sample_vector = embedding_model.embed_query("exemplo de texto")
        embedding_size = len(sample_vector)

        # 🔹 Recria coleção com dimensão correta
        qdrant_client.recreate_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=embedding_size,
                distance=Distance.COSINE
            )
        )

        # 🔹 Instância da vectorstore Langchain
        vectorstore = LangchainQdrant(
            client=qdrant_client,
            collection_name=QDRANT_COLLECTION,
            embeddings=embedding_model,
        )

        # 🔹 Adiciona documentos
        vectorstore.add_documents(documentos)

        return {
            "status": "sucesso",
            "chunks_salvos": total_chunks,
            "origem": file.filename
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")
