from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import os

def load_text_files(folder_path):
    text_data = []
    for file_path in Path(folder_path).rglob("*"):
        if file_path.suffix.lower() in ['.txt', '.pdf']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text_data.append((str(file_path), f.read()))
    return text_data

def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i+chunk_size])
        if chunk.strip():  # Only add non-empty chunks
            chunks.append(chunk)
    return chunks

embedder = SentenceTransformer("./models/all-MiniLM-L6-v2")

def embed_chunks(chunks):
    return embedder.encode(chunks, convert_to_numpy=True)

def build_faiss_index(embeddings, metadata):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, "rag_index.faiss")
    
    with open("rag_metadata.pkl", "wb") as f:
        pickle.dump({'metadata': metadata}, f)
    print("Saved metadata to rag_metadata.pkl")

def build_embeddings(folder_path):
    text_data = load_text_files(folder_path)
    if not text_data:
        print("No text files found!")
        return False
    
    all_chunks = []
    all_metadata = []
    
    for file_path, content in text_data:
        print(f"Processing: {os.path.basename(file_path)}")
        chunks = chunk_text(content)
        
        for idx, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadata.append((file_path, idx))
    
    if not all_chunks:
        print("No chunks created from files!")
        return False
    
    embeddings = embed_chunks(all_chunks)
    
    build_faiss_index(embeddings, all_metadata)
    
    return True

if __name__ == "__main__":
    DOCUMENT_FOLDER = r"C:\Users\manne\LocAI-test"
    
    success = build_embeddings(DOCUMENT_FOLDER)