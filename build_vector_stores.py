import sys
import os
import glob
from dotenv import load_dotenv
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from pymongo import MongoClient

load_dotenv()

# ---------------------------------------------------------------------------
# MongoDB connection (writes chunks into Atlas for Vector Search)
# ---------------------------------------------------------------------------
MONGO_URI = os.environ["MONGO_URI"]
mongo_client = MongoClient(MONGO_URI)
chunks_col = mongo_client.get_default_database().chunks


def store_chunks_to_mongo(bot_id, texts, vectors, source="build"):
    """
    Upserts knowledge-base chunks for a given bot_id into the Atlas 'chunks'
    collection.  Clears the previous version first so re-runs stay clean.
    """
    chunks_col.delete_many({"bot_id": bot_id})
    if not texts:
        return
    docs = [
        {
            "bot_id": bot_id,
            "text": text,
            "embedding": embedding,   # list[float] — 384 dims
            "source": source,
        }
        for text, embedding in zip(texts, vectors)
    ]
    chunks_col.insert_many(docs)
    print(f"[OK] Stored {len(docs)} chunks in MongoDB for '{bot_id}'")


def build_vector_store(bot_id):
    source_dir = os.path.join("data", "brands", bot_id)

    if not os.path.exists(source_dir):
        print(f"[ERROR] Source documents directory not found: {source_dir}")
        return False

    print(f"[INFO] Compiling vector store for chatbot: {bot_id} ...")
    embed_model = FastEmbedEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    all_texts = []
    all_sources = []

    md_files = glob.glob(os.path.join(source_dir, "*.md"))
    if not md_files:
        print(f"[WARN] No markdown files found in {source_dir}")
        return False

    for file_path in md_files:
        try:
            loader = TextLoader(file_path, encoding="utf-8")
            documents = loader.load()
            docs = text_splitter.split_documents(documents)
            texts = [d.page_content for d in docs]
            all_texts.extend(texts)
            all_sources.extend([os.path.basename(file_path)] * len(texts))
            print(f"[OK] Loaded {len(texts)} chunks from {os.path.basename(file_path)}")
        except Exception as e:
            print(f"[ERROR] Failed to load {file_path}: {e}")

    if not all_texts:
        print(f"[ERROR] No documents loaded for '{bot_id}'")
        return False

    # Embed all chunks locally using FastEmbed
    print(f"[INFO] Embedding {len(all_texts)} chunks...")
    vectors = embed_model.embed_documents(all_texts)

    # Persist to MongoDB Atlas instead of local files
    chunks_col.delete_many({"bot_id": bot_id})
    docs_to_insert = [
        {
            "bot_id": bot_id,
            "text": text,
            "embedding": vector,
            "source": source,
        }
        for text, vector, source in zip(all_texts, vectors, all_sources)
    ]
    chunks_col.insert_many(docs_to_insert)
    print(
        f"[OK] {len(docs_to_insert)} chunks stored in MongoDB Atlas for '{bot_id}'"
    )
    return True


def build_all():
    brands_dir = os.path.join("data", "brands")
    if not os.path.exists(brands_dir):
        print("[ERROR] No data/brands directory found.")
        return

    brand_subdirs = [
        d
        for d in os.listdir(brands_dir)
        if os.path.isdir(os.path.join(brands_dir, d))
    ]
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
        build_vector_store(sys.argv[1])
    else:
        build_all()
