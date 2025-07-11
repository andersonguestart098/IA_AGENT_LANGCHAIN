import os
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS
from app.services.embeddings import embedding_model
from langchain.chains import RetrievalQAWithSourcesChain
from langchain_core.documents import Document
from app.generated.client import Prisma

async def setup_rag_chain():
    prisma = Prisma()
    await prisma.connect()

    # 🔹 LLM - Mistral via LangChain
    llm = ChatOpenAI(
        model="mistral-large-latest",
        openai_api_key=os.getenv("MISTRAL_API_KEY"),
        base_url="https://api.mistral.ai/v1",
        temperature=0.3
    )

    # 🔹 Prompt para classificar intenção
    intencao_prompt = PromptTemplate.from_template("""
    Você é um classificador de intenção para uma assistente virtual da Cemear (pisos, divisórias e soluções acústicas).
    Classifique a frase do cliente em UMA das seguintes categorias:
    - SAUDACAO
    - PEDIDO_ORCAMENTO
    - PERGUNTA_PRODUTO
    - VAGA_EMPREGO
    - FORA_REGIAO
    - OUTRO

    Frase: {texto}
    Categoria:
    """)
    classificacao_chain = intencao_prompt | llm | StrOutputParser()

    # 🔹 Recupera documentos com embedding
    docs_db = await prisma.knowledgebase.find_many(
    where={"embedding": {"not": ""}})
    docs = [Document(page_content=doc.conteudo, metadata={"id": doc.id, "source": doc.origem}) for doc in docs_db]

    # 🔹 Cria vetores e retriever
    vectorstore = FAISS.from_documents(docs, embedding_model)
    retriever = vectorstore.as_retriever(search_type="similarity", k=1)

    # 🔹 Prompt para RAG
    resposta_prompt = PromptTemplate.from_template("""
    Você é o atendente virtual da Cemear, especializada em pisos, divisórias, brise e soluções acústicas.
    Regras:
    - Responda APENAS com base no documento abaixo.
    - Seja cordial e breve (máximo 3 frases).
    - Não invente. Se não souber, diga: "Preciso consultar um especialista sobre isso."

    DOCUMENTO:
    {context}

    PERGUNTA:
    {question}
    """)

    rag_chain = RetrievalQAWithSourcesChain.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True,
    chain_type="stuff",
    chain_type_kwargs={
        "prompt": resposta_prompt,
        "document_variable_name": "context" 
    }
)


    return {
        "prisma": prisma,
        "llm": llm,
        "classificacao_chain": classificacao_chain,
        "rag_chain": rag_chain
    }
