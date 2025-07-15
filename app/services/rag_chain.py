import os
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain_core.documents import Document
from app.services.embeddings import embedding_model
from app.generated.client import Prisma
from langchain.output_parsers import OutputFixingParser


async def setup_rag_chain(sessao_token: str):
    prisma = Prisma()
    await prisma.connect()

    # 🔹 Recupera a sessão e histórico recente da conversa
    sessao = await prisma.sessao.find_unique(where={"token": sessao_token})
    historico = await prisma.fluxoconversa.find_many(
        where={"sessaoId": sessao.id},
        order={"id": "asc"},
        take=5
    )
    eh_primeira_interacao = len(historico) == 0
    chat_history = [(h.pedido, h.resposta) for h in historico if h.resposta]

    # 🔹 Instancia LLM (Mistral via OpenAI compatível)
    llm = ChatOpenAI(
        model="mistral-large-latest",
        openai_api_key=os.getenv("MISTRAL_API_KEY"),
        base_url="https://api.mistral.ai/v1",
        temperature=0.3
    )

    # 🔹 Cadeia de classificação de intenção
    intencao_prompt = PromptTemplate.from_template("""
Você é um classificador de intenção para uma assistente virtual da Cemear (pisos, divisórias e soluções acústicas).
Classifique a frase do cliente em UMA das seguintes categorias:
- SAUDACAO
- PEDIDO_ORCAMENTO
- PERGUNTA_PRODUTO
- VAGA_EMPREGO
- FORA_REGIAO
- CONTINUIDADE_FLUXO
- DESPEDIDA
- CONFIRMACAO
- OUTRO

Frase: {texto}
Categoria:
""")
    classificacao_chain = intencao_prompt | llm | StrOutputParser()

    # 🔹 Prompt de Slot Filling estruturado
    slot_prompt = PromptTemplate.from_template("""
Dada a frase de um cliente, extraia as seguintes informações de forma estruturada:

- produto
- volume_aproximado
- localidade
- prazo

Se alguma informação não estiver presente, use `null`.

Responda APENAS com um JSON válido, exatamente neste formato:
{{
  "produto": string | null,
  "volume_aproximado": string | null,
  "localidade": string | null,
  "prazo": string | null
}}

Frase: {texto}
JSON:
""")

    # 🔹 Cria parser com fallback para corrigir formatos
    slot_filling_chain = slot_prompt | llm | OutputFixingParser.from_llm(
        parser=JsonOutputParser(), llm=llm
    )

    # 🔹 Carrega documentos com embeddings
    docs_db = await prisma.knowledgebase.find_many(where={"embedding": {"not": ""}})
    docs = [
        Document(
            page_content=doc.conteudo,
            metadata={"id": doc.id, "source": doc.origem}
        )
        for doc in docs_db
    ]
    vectorstore = FAISS.from_documents(docs, embedding_model)
    retriever = vectorstore.as_retriever(search_type="similarity", k=3)

    # 🔹 Prompt do RAG com regras contextuais
    resposta_prompt = PromptTemplate.from_template("""
Você é o atendente virtual da Cemear, especializada em pisos, divisórias, brises e soluções acústicas.

Regras:
- Responda SOMENTE com base no DOCUMENTO abaixo.
- Seja direto, educado e evite frases genéricas como "como posso ajudar?" ou "entre em contato conosco".
- NÃO mencione horários comerciais, exceto se o cliente pedir.
- Apenas diga que vai encaminhar o pedido se a intenção for PEDIDO_ORCAMENTO.
- Evite repetir saudações se não for a primeira interação.
- Considere o HISTÓRICO da conversa para responder com contexto.
- Se a resposta não estiver clara no documento, diga: "Preciso consultar um especialista sobre isso."

HISTÓRICO DE CONVERSA:
{chat_history}

DOCUMENTO:
{context}

PERGUNTA ATUAL:
{question}
""")

    # 🔹 Cadeia principal de resposta com histórico e documentos
    rag_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
        combine_docs_chain_kwargs={
            "prompt": resposta_prompt
        }
    )

    # 🔹 Retorna todos os componentes para uso no fluxo principal
    return {
        "prisma": prisma,
        "llm": llm,
        "classificacao_chain": classificacao_chain,
        "slot_filling_chain": slot_filling_chain,
        "rag_chain": rag_chain,
        "sessao": sessao,
        "eh_primeira_interacao": eh_primeira_interacao,
        "chat_history": chat_history
    }
