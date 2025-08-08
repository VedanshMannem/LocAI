from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import fitz  # PyMuPDF
import os

def load_text_files(folder_path):
    text_data = []
    for file_path in Path(folder_path).rglob("*"):
        if file_path.suffix.lower() == '.txt' or file_path.suffix.lower() == '.md':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text_data.append((str(file_path), f.read()))
        elif file_path.suffix.lower() == '.pdf':
            with fitz.open(file_path) as doc:
                content = ""
                for page in doc:
                    content += page.get_text()
                text_data.append((str(file_path), content))
        # elif file_path.suffix.lower() == '.png': # for png files of text (receipts, etc.)
            #     # FIXME & ADD @ ~ line 90
            #     with open(file_path, 'rb') as f:
            #         content = f.read()
            #         text_data.append((str(file_path), content))

    return text_data

def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i+chunk_size])
        chunks.append(chunk)
    return chunks

model_path = "./models/all-MiniLM-L6-v2" # . for source and .. for build
embedder = SentenceTransformer(model_path)

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

def build_embeddings(folder_path):
    text_data = load_text_files(folder_path)
    if not text_data:
        print("No text files found!")
        return False
    
    all_chunks = []
    all_metadata = []
    
    for file_path, content in text_data:
        chunks = chunk_text(content)
        
        for idx, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadata.append((file_path, idx))
    
    if not all_chunks:
        print("No chunks created from files!")
        return False

    embeddings = embed_chunks(all_chunks)
    build_faiss_index(embeddings, all_chunks, all_metadata)
    
    return True

def retrieve_relevant_chunks(query, embedder, index, data, top_k=2):
    query_embedding = embedder.encode([query])
    D, I = index.search(query_embedding, top_k)
    
    # Dynamically load chunks from original files
    chunks = []
    metadata = data['metadata']
    
    for i in I[0]:
        file_path, chunk_idx = metadata[i]
        # Re-read and re-chunk the file to get the specific chunk
        try:
            if file_path.endswith('.txt') or file_path.endswith('.md'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    file_chunks = chunk_text(content)
                    if chunk_idx < len(file_chunks):
                        chunks.append(file_chunks[chunk_idx])
            elif file_path.endswith('.pdf'):
                with fitz.open(file_path) as doc:
                    content = ""
                    for page in doc:
                        content += page.get_text()
                    file_chunks = chunk_text(content)
                    if chunk_idx < len(file_chunks):
                        chunks.append(file_chunks[chunk_idx])
        # TODO: Add the png support here
                    
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return chunks

def build_prompt(retrieved_chunks, user_question):
    context = "\n\n".join(retrieved_chunks)
    return f"Here is some context about the user:\n\n{context}. You may not= need to use this information to answer the question; it's just to provide more context.\n\nHere is the question: {user_question}"

def load_faiss_index_and_metadata():
    try: 
        index = faiss.read_index("rag_index.faiss")
        with open("rag_metadata.pkl", "rb") as f:
            metadata = pickle.load(f)
        return index, metadata
    except RuntimeError as e:
        print("Add some user context")
        return None, None
    except Exception as e:
        print(f"Error loading FAISS index or metadata: {e}")
        return None, None
