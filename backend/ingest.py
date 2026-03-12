import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import MarkdownTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Paths
DOCS_DIR = os.path.join(os.path.dirname(__file__), "data", "docs")
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

def main():
    print(f"Loading markdown documents from {DOCS_DIR}")
    # Load all markdown files in the directory
    loader = DirectoryLoader(DOCS_DIR, glob="*.md", loader_cls=TextLoader, loader_kwargs={'autodetect_encoding': True})
    documents = loader.load()
    
    if not documents:
        print("No documents found. Please ensure real data is downloaded.")
        return
        
    print(f"Loaded {len(documents)} documents.")

    # Split documents into chunks
    text_splitter = MarkdownTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)
    print(f"Split documents into {len(chunks)} chunks.")

    # Initialize HuggingFace embeddings (runs locally, free, no API key required)
    print("Initializing local HuggingFace embedding model (all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # Store chunks in Chroma
    print(f"Saving chunks into ChromaDB at {CHROMA_PATH}...")
    db = Chroma.from_documents(
        chunks, 
        embeddings, 
        persist_directory=CHROMA_PATH
    )
    print("Ingestion complete!")

if __name__ == "__main__":
    main()
