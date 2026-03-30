import os
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

def get_rag_chain():
    # Load embeddings and vector store
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    retriever = db.as_retriever(search_kwargs={"k": 3})

    # Initialize LLM
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set. Please add it to your .env file.")
        
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)

    # Define Prompt
    system_prompt = (
        "You are an IT Helpdesk AI Assistant. Use the following pieces of retrieved technical documentation "
        "to answer the user's question. If you don't know the answer or the context doesn't contain the answer, "
        "just say that you don't know, don't try to make up an answer."
        "\n\n"
        "Context:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    # Construct the LCEL chain
    setup_and_retrieval = RunnablePassthrough.assign(
        context=(lambda x: x["input"]) | retriever
    )
    
    def format_input_for_prompt(x):
        return {
            "context": format_docs(x["context"]),
            "input": x["input"]
        }
        
    answer_chain = format_input_for_prompt | prompt | llm | StrOutputParser()
    
    rag_chain = setup_and_retrieval | RunnablePassthrough.assign(
        answer=answer_chain
    )
    
    return rag_chain

