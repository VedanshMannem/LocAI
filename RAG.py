from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import pickle
from response import ask_ai

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
        chunks.append(chunk)
    return chunks

embedder = SentenceTransformer("./models/all-MiniLM-L6-v2")

def embed_chunks(chunks):
    return embedder.encode(chunks, convert_to_numpy=True)

def build_faiss_index(embeddings, chunks, metadata):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, "rag_index.faiss")
    # Only save metadata with file positions, not full chunks
    with open("rag_metadata.pkl", "wb") as f:
        pickle.dump({'metadata': metadata}, f)

def retrieve_relevant_chunks(query, embedder, index, data, top_k=3):
    query_embedding = embedder.encode([query])
    D, I = index.search(query_embedding, top_k)
    
    # Dynamically load chunks from original files
    chunks = []
    metadata = data['metadata']
    
    for i in I[0]:
        file_path, chunk_idx = metadata[i]
        # Re-read and re-chunk the file to get the specific chunk
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                file_chunks = chunk_text(content)
                if chunk_idx < len(file_chunks):
                    chunks.append(file_chunks[chunk_idx])
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return chunks

def build_prompt(retrieved_chunks, user_question):
    context = "\n\n".join(retrieved_chunks)
    return f"Use the following information to answer the question:\n\n{context}\n\nQuestion: {user_question}"

def load_faiss_index_and_metadata():
    index = faiss.read_index("rag_index.faiss")
    with open("rag_metadata.pkl", "rb") as f:
        metadata = pickle.load(f)
    return index, metadata

# testing
# use this for 1st time loading in data
# text_data = load_text_files(r"C:\Users\manne\Downloads\LocAI-Test")
# print("Loaded text files:", len(text_data))

# all_chunks = []
# all_metadata = []

# for file_path, content in text_data:
#     print(f"Processing file: {file_path}")
#     chunks = chunk_text(content)
#     for idx, chunk in enumerate(chunks):
#         all_chunks.append(chunk)
#         all_metadata.append((file_path, idx))
#         print(f"Chunk {idx+1}/{len(chunks)}: {chunk[:30]}...")  
#         print(f"Metadata: {file_path}, Chunk Index: {idx}")

# if all_chunks:
#     embeddings = embed_chunks(all_chunks)
#     build_faiss_index(embeddings, all_chunks, all_metadata)  
#     print(f"Built index with {len(all_chunks)} chunks")


index, metadata = load_faiss_index_and_metadata()
print("Loaded index and metadata")

question = "write me a draft of an email for a meeting request to discuss my top to-do list tasks"
print(ask_ai(build_prompt(retrieve_relevant_chunks(question, embedder, index, metadata), question), 256))
