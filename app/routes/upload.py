from fastapi import APIRouter, UploadFile, File, HTTPException
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.services.embeddings import embedding_model
import numpy as np
import json
from app.generated.client import Prisma

router = APIRouter()

@router.post("/upload-conhecimento")
async def upload_conhecimento(file: UploadFile = File(...)):
    try:
        prisma = Prisma()
        await prisma.connect()

        content = await file.read()
        try:
            dados = json.loads(content.decode("utf-8"))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erro ao ler JSON: {e}")

        if not isinstance(dados, list):
            raise HTTPException(status_code=400, detail="JSON deve ser uma lista de objetos.")

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        total_chunks = 0

        for item in dados:
            conteudo = item.get("conteudo")
            if not conteudo:
                continue

            metadados = item.copy()
            metadados.pop("Conteudo", None)  # Remover o conteúdo do metadado para não duplicar

            documentos = splitter.create_documents([conteudo], metadatas=[metadados])
            total_chunks += len(documentos)

            for doc in documentos:
                embedding = embedding_model.embed_documents([doc.page_content])[0]
                embedding_json = json.dumps(np.array(embedding).tolist())

                await prisma.knowledgebase.create(data={
                    "origem": json.dumps(doc.metadata, ensure_ascii=False),
                    "conteudo": doc.page_content,
                    "embedding": embedding_json
                })

        return {
            "status": "sucesso",
            "chunks_salvos": total_chunks,
            "origem": file.filename
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")
