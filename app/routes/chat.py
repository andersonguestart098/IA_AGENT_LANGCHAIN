from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag_chain import setup_rag_chain

router = APIRouter()

class ChatRequest(BaseModel):
    pergunta: str

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        chains = await setup_rag_chain()
        classificacao_chain = chains["classificacao_chain"]
        rag_chain = chains["rag_chain"]

        pergunta = request.pergunta

        # Classificação de intenção
        intencao = classificacao_chain.invoke({"texto": pergunta})

        # Busca com contexto (RAG)
        resultado = rag_chain({"question": pergunta})
        resposta = resultado["answer"]
        fontes = resultado.get("sources", "")

        return {
            "intencao": intencao,
            "resposta": resposta,
            "fonte": fontes
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")