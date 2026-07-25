import sys
import os
import glob
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

load_dotenv()

def build_vector_store(bot_id):
    source_dir = os.path.join("data", "brands", bot_id)
    dest_path = os.path.join("vector_stores", bot_id)
    
    if not os.path.exists(source_dir):
        print(f"[ERROR] Source documents directory not found: {source_dir}")
        return False
        
    print(f"[INFO] Compiling vector store for chatbot: {bot_id} ...")
    embeddings = FastEmbedEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    all_docs = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    
    md_files = glob.glob(os.path.join(source_dir, "*.md"))
    if not md_files:
        print(f"[WARN] No markdown files found in {source_dir}")
        return False
        
    for file_path in md_files:
        try:
            loader = TextLoader(file_path, encoding="utf-8")
            documents = loader.load()
            docs = text_splitter.split_documents(documents)
            all_docs.extend(docs)
            print(f"[OK] Loaded {len(docs)} chunks from {os.path.basename(file_path)}")
        except Exception as e:
            print(f"[ERROR] Failed to load {file_path}: {e}")
            
    if all_docs:
        vectorstore = FAISS.from_documents(all_docs, embeddings)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        vectorstore.save_local(dest_path)
        print(f"[OK] Vector store compiled successfully for '{bot_id}' with {len(all_docs)} total chunks")
        return True
    else:
        print(f"[ERROR] No documents loaded for '{bot_id}'")
        return False

def build_all():
    brands_dir = os.path.join("data", "brands")
    if not os.path.exists(brands_dir):
        print("[ERROR] No data/brands directory found.")
        return
        
    brand_subdirs = [d for d in os.listdir(brands_dir) if os.path.isdir(os.path.join(brands_dir, d))]
    if not brand_subdirs:
        print("[WARN] No brand subdirectories found under data/brands/")
        return
        
    for bot_id in brand_subdirs:
        try:
            build_vector_store(bot_id)
        except Exception as e:
            print(f"[ERROR] Failed to compile for {bot_id}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Build specific bot_id passed as argument
        build_vector_store(sys.argv[1])
    else:
        # Build all bots in the brands directory
        build_all()
