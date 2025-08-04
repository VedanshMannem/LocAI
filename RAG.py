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

def build_faiss_index(embeddings, metadata):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, "rag_index.faiss")
    with open("rag_metadata.pkl", "wb") as f:
        pickle.dump(metadata, f)

def retrieve_relevant_chunks(query, embedder, index, metadata, top_k=3):
    query_embedding = embedder.encode([query])
    D, I = index.search(query_embedding, top_k)
    return [metadata[i] for i in I[0]]

def build_prompt(retrieved_chunks, user_question):
    context = "\n\n".join(retrieved_chunks)
    return f"Use the following information to answer the question:\n\n{context}\n\nQuestion: {user_question}"

# testing
# text_data = load_text_files(r"C:\\Users\\manne\\Downloads\\LocAI-Test")
# print("Loaded text files:", text_data)

# for i in range(len(text_data)):
#     file_path, content = text_data[i]
#     print(f"\nProcessing file: {file_path}")
#     chunks = chunk_text(content)
#     embeddings = embed_chunks(chunks)
    # build_faiss_index(embeddings, [(file_path, idx) for idx in range(len(chunks))])


index = faiss.read_index("rag_index.faiss")
with open("rag_metadata.pkl", "rb") as f:
    metadata = pickle.load(f)

question = "What is on to-do list?"
print(ask_ai(build_prompt(retrieve_relevant_chunks(question, embedder, index, metadata), question), tokens=100, n_threads=4))
