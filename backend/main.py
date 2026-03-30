from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_pipeline import get_rag_chain

app = FastAPI(title="IT Helpdesk RAG API")

# Setup CORS for the Next.js frontend (usually port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]

try:
    rag_chain = get_rag_chain()
except Exception as e:
    rag_chain = None
    print(f"Warning: RAG chain failed to initialize: {e}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not rag_chain:
        raise HTTPException(status_code=500, detail="RAG chain not initialized. Is GOOGLE_API_KEY set?")
        
    try:
        response = rag_chain.invoke({"input": request.message})
        answer = response.get("answer", "I could not generate an answer.")
        
        # Extract source documents
        source_docs = response.get("context", [])
        sources = []
        for doc in source_docs:
            source = doc.metadata.get("source", "Unknown source")
            if source not in sources:
                sources.append(source)
                
        return ChatResponse(answer=answer, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
