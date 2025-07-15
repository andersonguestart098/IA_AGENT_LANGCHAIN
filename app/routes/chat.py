import json
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

    try:
        # 🔹 Carrega os componentes do RAG
        chains = await setup_rag_chain(sessao_token=authorization)
        classificacao_chain = chains["classificacao_chain"]
        slot_filling_chain = chains["slot_filling_chain"]
        rag_chain = chains["rag_chain"]
        prisma = chains["prisma"]
        sessao = chains["sessao"]
        eh_primeira_interacao = chains["eh_primeira_interacao"]
        chat_history = chains["chat_history"]

        # 🔹 Intenção do usuário
        intencao = classificacao_chain.invoke({"texto": pergunta}).strip()
        print(f"[LOG] Intenção detectada: {intencao}")

        # 🔹 Slot Filling
        print("[LOG] Executando slot filling...")
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

        # 🔹 Geração da resposta via RAG
        resultado = rag_chain.invoke({
            "question": pergunta,
            "chat_history": chat_history
        })
        resposta_base = resultado.get("answer", "").strip()
        fontes = resultado.get("sources", "")


        # 🔹 Regras de saudação
        saudacao = "Bom dia, tudo bem? " if eh_primeira_interacao else ""

        # 🔹 Formação da resposta com lógica refinada
        if intencao == "PEDIDO_ORCAMENTO" and produto and localidade:
            resposta = "Estou transferindo seu atendimento para o vendedor responsável. Em instantes ele entra em contato para dar continuidade ao seu pedido."
        elif "consultar um especialista" in resposta_base.lower():
            resposta = "Preciso consultar um especialista sobre isso."
        else:
            encaminhamento = "\nPosso encaminhar seu pedido para nosso setor comercial." if intencao == "PEDIDO_ORCAMENTO" else ""
            resposta = f"{saudacao}{resposta_base}{encaminhamento}".strip()

        # 🔹 Ajusta resposta em caso de confirmação explícita
        if intencao == "CONFIRMACAO" and produto and localidade:
            resposta = f"Ótimo! Já tenho o pedido de {volume or 'volume não informado'} de {produto} para {localidade}. Estou encaminhando ao setor responsável."

        # 🔹 Define a etapa do fluxo
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

        # 🔹 Registra o fluxo da conversa
        fluxo = await prisma.fluxoconversa.create(data={
            "sessaoId": sessao.id,
            "etapa": etapa,
            "intencao": intencao,
            "pedido": pergunta,
            "resposta": resposta
        })

        # 🔹 Registra os slots extraídos (se houver)
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
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")

    finally:
        await prisma.disconnect()
