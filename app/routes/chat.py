import json
import time
import mlflow
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
from app.services.rag_chain import setup_rag_chain

router = APIRouter()

class ChatRequest(BaseModel):
    pergunta: str

@router.post("/chat")
async def chat(request: ChatRequest, authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token de sessão ausente.")

    pergunta = request.pergunta.strip()
    inicio_execucao = time.time()

    try:
        chains = await setup_rag_chain(sessao_token=authorization)
        classificacao_chain = chains["classificacao_chain"]
        slot_filling_chain = chains["slot_filling_chain"]
        prisma = chains["prisma"]
        sessao = chains["sessao"]
        eh_primeira_interacao = chains["eh_primeira_interacao"]
        chat_history = chains["chat_history"]

        intencao = classificacao_chain.invoke({"texto": pergunta}).strip()
        print(f"[LOG] Intenção detectada: {intencao}")

        try:
            slots_dict = slot_filling_chain.invoke({"texto": pergunta})
        except Exception as e:
            print(f"[ERRO] Falha ao fazer parse do JSON de slots: {e}")
            slots_dict = {}

        produto = slots_dict.get("produto")
        localidade = slots_dict.get("localidade")
        volume = slots_dict.get("volume_aproximado")
        prazo = slots_dict.get("prazo")

        print(f"[LOG] Slots extraídos: produto={produto}, localidade={localidade}, volume={volume}, prazo={prazo}")

        # 🔹 Mapeamento da intenção para categoria
        mapa_categoria = {
            "PEDIDO_ORCAMENTO": "produtos_servicos",
            "PERGUNTA_PRODUTO": "produtos_servicos",
            "VAGA_EMPREGO": "institucional",
            "FORA_REGIAO": "institucional"
        }
        filtro_categoria = mapa_categoria.get(intencao)
        print(f"[LOG] Categoria usada no filtro RAG: {filtro_categoria}")

        chains = await setup_rag_chain(sessao_token=authorization, filtro_categoria=filtro_categoria)
        rag_chain = chains["rag_chain"]

        resultado = rag_chain.invoke({
            "question": pergunta,
            "chat_history": chat_history
        })

        resposta_base = resultado.get("answer", "").strip()
        fontes = resultado.get("sources", "")

        documentos_utilizados = resultado.get("source_documents", [])
        print(f"[LOG] Documentos encontrados: {len(documentos_utilizados)}")
        for i, doc in enumerate(documentos_utilizados):
            print(f"[LOG] Doc {i+1}: {doc.page_content[:100]}... | Metadata: {doc.metadata}")

        origens_utilizadas = list({
            doc.metadata.get("source", "desconhecido") for doc in documentos_utilizados
        })

        saudacao = "Bom dia, tudo bem? " if eh_primeira_interacao else ""

        if intencao == "PEDIDO_ORCAMENTO" and produto and localidade:
            resposta = "Estou transferindo seu atendimento para o vendedor responsável. Em instantes ele entra em contato para dar continuidade ao seu pedido."
        elif "consultar um especialista" in resposta_base.lower() or len(documentos_utilizados) == 0:
            resposta = "Preciso consultar um especialista sobre isso."
        else:
            encaminhamento = "\nPosso encaminhar seu pedido para nosso setor comercial." if intencao == "PEDIDO_ORCAMENTO" else ""
            resposta = f"{saudacao}{resposta_base}{encaminhamento}".strip()

        if intencao == "CONFIRMACAO" and produto and localidade:
            resposta = f"Ótimo! Já tenho o pedido de {volume or 'volume não informado'} de {produto} para {localidade}. Estou encaminhando ao setor responsável."

        if intencao == "SAUDACAO" and eh_primeira_interacao:
            etapa = "INICIO"
        elif intencao == "PEDIDO_ORCAMENTO" and (produto and localidade):
            etapa = "FINALIZADO"
        elif intencao == "PEDIDO_ORCAMENTO":
            etapa = "COLETA_INFO"
        elif intencao in ("DESPEDIDA", "FORA_REGIAO") or "consultar um especialista" in resposta.lower():
            etapa = "FINALIZADO"
        elif intencao == "CONFIRMACAO":
            etapa = "FINALIZADO"
        else:
            etapa = "MEIO"

        fluxo = await prisma.fluxoconversa.create(data={
            "sessaoId": sessao.id,
            "etapa": etapa,
            "intencao": intencao,
            "pedido": pergunta,
            "resposta": resposta
        })

        for nome, valor in slots_dict.items():
            if valor:
                try:
                    await prisma.slotpreenchido.create(data={
                        "fluxoId": fluxo.id,
                        "nome": nome,
                        "valor": valor
                    })
                    print(f"[LOG] Slot salvo: {nome} = {valor}")
                except Exception as e:
                    print(f"[ERRO] Falha ao salvar slot '{nome}': {e}")

        tempo_total = time.time() - inicio_execucao

        # 🔹 Log com MLflow
        mlflow.set_experiment("chat")
        with mlflow.start_run():
            mlflow.set_tag("sessao_id", sessao.id)
            mlflow.set_tag("etapa", etapa)
            mlflow.set_tag("sucesso", True)
            mlflow.log_param("intencao", intencao)
            mlflow.log_param("pergunta", pergunta)
            mlflow.log_param("resposta", resposta[:300])

            docs_usados = [doc.page_content for doc in resultado.get("source_documents", [])]
            mlflow.log_dict({"documentos": docs_usados}, "rag_contexto.json")
            mlflow.log_metric("tempo_execucao", tempo_total)

            mlflow.log_dict({
                "pergunta": pergunta,
                "resposta": resposta,
                "documentos": [doc.page_content for doc in documentos_utilizados],
                "origens": origens_utilizadas,
                "slots": slots_dict,
                "intencao": intencao
            }, artifact_file="interacao.json")

            mlflow.log_dict({
                "origens_utilizadas": origens_utilizadas,
                "contexto": "rag"
            }, "input_metadata.json")

        return {
            "intencao": intencao,
            "etapa": etapa,
            "resposta": resposta,
            "fonte": fontes,
            "slots": {
                "produto": produto,
                "localidade": localidade,
                "volume_aproximado": volume,
                "prazo": prazo
            }
        }

    except Exception as e:
        print(f"[FATAL] Erro inesperado: {e}")
        mlflow.set_experiment("chat")
        with mlflow.start_run():
            mlflow.set_tag("sessao_id", authorization)
            mlflow.set_tag("erro", str(e))
            mlflow.set_tag("sucesso", False)

        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")

    finally:
        await prisma.disconnect()
