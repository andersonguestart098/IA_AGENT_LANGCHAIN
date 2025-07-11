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
        texto = content.decode("utf-8", errors="ignore")

        if not texto.strip():
            raise HTTPException(400, "Arquivo sem conteúdo.")

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        documentos = splitter.create_documents([texto])

        for doc in documentos:
            embedding = embedding_model.embed_documents([doc.page_content])[0]
            embedding_json = json.dumps(np.array(embedding).tolist())

            await prisma.knowledgebase.create(data={
                "origem": file.filename,
                "conteudo": doc.page_content,
                "embedding": embedding_json
            })

        return {
            "status": "sucesso",
            "chunks_salvos": len(documentos),
            "origem": file.filename
        }

    except Exception as e:
        raise HTTPException(500, f"Erro ao processar arquivo: {str(e)}")
