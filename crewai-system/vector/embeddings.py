"""
Embeddings and Pinecone integration
"""
import os
import pinecone
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import numpy as np

# Load environment variables
load_dotenv()

# Model configuration
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def init_pinecone():
    """
    Initialize Pinecone connection
    
    Returns:
        pinecone.Index: Pinecone index object
    """
    try:
        key = os.environ.get("PINECONE_API_KEY")
        env = os.environ.get("PINECONE_ENV")
        
        if not key:
            raise ValueError("PINECONE_API_KEY not found in environment variables")
        
        pinecone.init(api_key=key, environment=env)
        index_name = "pharma-docs"
        
        # Create index if it doesn't exist
        if index_name not in pinecone.list_indexes():
            print(f"Creating Pinecone index: {index_name}")
            pinecone.create_index(index_name, dimension=384, metric="cosine")
        
        return pinecone.Index(index_name)
    except Exception as e:
        print(f"Error initializing Pinecone: {str(e)}")
        raise

def get_embedding_model():
    """
    Load and return the sentence transformer model
    
    Returns:
        SentenceTransformer: Loaded model
    """
    try:
        print(f"Loading embedding model: {MODEL_NAME}")
        return SentenceTransformer(MODEL_NAME)
    except Exception as e:
        print(f"Error loading embedding model: {str(e)}")
        raise

def embed_text(text, model=None):
    """
    Generate embedding for a single text
    
    Args:
        text (str): Text string to embed
        model (SentenceTransformer): Optional pre-loaded model
    
    Returns:
        list: Embedding vector
    """
    try:
        if model is None:
            model = get_embedding_model()
        
        embedding = model.encode([text])[0].tolist()
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        raise

def embed_texts(texts, model=None):
    """
    Generate embeddings for a list of texts
    
    Args:
        texts (list): List of text strings to embed
        model (SentenceTransformer): Optional pre-loaded model
    
    Returns:
        list: List of embeddings
    """
    try:
        if model is None:
            model = get_embedding_model()
        
        print(f"Generating embeddings for {len(texts)} texts")
        embeddings = model.encode(texts, show_progress_bar=True)
        return embeddings.tolist()
    except Exception as e:
        print(f"Error generating embeddings: {str(e)}")
        raise

def upsert_docs(docs, index=None):
    """
    Upsert documents to Pinecone
    
    Args:
        docs (list): List of documents with format {"id": str, "text": str, "meta": dict}
        index (pinecone.Index): Optional pre-initialized Pinecone index
    
    Returns:
        bool: True if successful
    """
    try:
        if index is None:
            index = init_pinecone()
        
        if not docs:
            print("No documents to upsert")
            return True
        
        # Extract texts and generate embeddings
        texts = [d["text"] for d in docs]
        embeddings = embed_texts(texts)
        
        # Prepare items for upsert
        items = []
        for i, d in enumerate(docs):
            item = (d["id"], embeddings[i], d["meta"])
            items.append(item)
        
        # Upsert to Pinecone
        print(f"Upserting {len(items)} documents to Pinecone")
        index.upsert(items)
        print("Successfully upserted documents to Pinecone")
        return True
        
    except Exception as e:
        print(f"Error upserting documents to Pinecone: {str(e)}")
        raise

def search_similar_texts(query_text, top_k=5, index=None, model=None):
    """
    Search for similar texts in Pinecone
    
    Args:
        query_text (str): Text to search for
        top_k (int): Number of results to return
        index (pinecone.Index): Optional pre-initialized Pinecone index
        model (SentenceTransformer): Optional pre-loaded model
    
    Returns:
        list: List of similar documents with scores
    """
    try:
        if index is None:
            index = init_pinecone()
        
        if model is None:
            model = get_embedding_model()
        
        # Generate embedding for query text
        query_embedding = model.encode([query_text])[0].tolist()
        
        # Search in Pinecone
        print(f"Searching for similar texts to: {query_text}")
        results = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
        
        # Format results
        similar_docs = []
        for match in results["matches"]:
            doc = {
                "id": match["id"],
                "score": match["score"],
                "metadata": match["metadata"]
            }
            similar_docs.append(doc)
        
        return similar_docs
        
    except Exception as e:
        print(f"Error searching similar texts: {str(e)}")
        raise

# Example usage:
# docs = [{"id": "doc1", "text": "This is a sample document", "meta": {"source": "sample"}}]
# upsert_docs(docs)
# results = search_similar_texts("sample document")