"""
Document analyzer using BERT for semantic analysis and information extraction
"""
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re
from typing import List, Dict, Tuple

class DocumentAnalyzer:
    """Analyzer for extracting insights from documents using BERT"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the document analyzer with BERT model
        
        Args:
            model_name (str): Name of the BERT model to use
        """
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()
        
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts using BERT
        
        Args:
            texts (List[str]): List of texts to embed
            
        Returns:
            np.ndarray: Array of embeddings
        """
        # Tokenize texts
        encoded_input = self.tokenizer(
            texts, 
            padding=True, 
            truncation=True, 
            return_tensors='pt',
            max_length=512
        )
        
        # Generate embeddings
        with torch.no_grad():
            model_output = self.model(**encoded_input)
            
        # Use mean pooling to get sentence embeddings
        embeddings = self.mean_pooling(model_output, encoded_input['attention_mask'])
        
        # Normalize embeddings
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        
        return embeddings.numpy()
    
    def mean_pooling(self, model_output: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """
        Apply mean pooling to get sentence embeddings
        
        Args:
            model_output (torch.Tensor): Output from BERT model
            attention_mask (torch.Tensor): Attention mask
            
        Returns:
            torch.Tensor: Mean pooled embeddings
        """
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    def find_similar_sections(self, query: str, document_text: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Find sections of the document most similar to the query
        
        Args:
            query (str): Query string
            document_text (str): Document text to search
            top_k (int): Number of top similar sections to return
            
        Returns:
            List[Tuple[str, float]]: List of (section, similarity_score) tuples
        """
        # Split document into sections (paragraphs)
        sections = [s.strip() for s in document_text.split('\n\n') if s.strip()]
        
        if not sections:
            return []
        
        # Get embeddings for query and sections
        query_embedding = self.get_embeddings([query])
        section_embeddings = self.get_embeddings(sections)
        
        # Calculate similarities
        similarities = cosine_similarity(query_embedding, section_embeddings)[0]
        
        # Get top-k most similar sections
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Only return sections with some similarity
                results.append((sections[idx], float(similarities[idx])))
                
        return results
    
    def extract_key_sentences(self, document_text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Extract key sentences from document based on centrality
        
        Args:
            document_text (str): Document text
            top_k (int): Number of key sentences to extract
            
        Returns:
            List[Tuple[str, float]]: List of (sentence, importance_score) tuples
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', document_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if len(sentences) < 2:
            return [(document_text, 1.0)] if document_text else []
        
        # Get embeddings
        sentence_embeddings = self.get_embeddings(sentences)
        
        # Calculate mean embedding
        mean_embedding = np.mean(sentence_embeddings, axis=0)
        
        # Calculate similarity to mean (centrality)
        similarities = cosine_similarity([mean_embedding], sentence_embeddings)[0]
        
        # Get top-k sentences
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            results.append((sentences[idx], float(similarities[idx])))
            
        return results
    
    def summarize_document(self, document_text: str, max_sentences: int = 5) -> str:
        """
        Generate a summary of the document
        
        Args:
            document_text (str): Document text to summarize
            max_sentences (int): Maximum number of sentences in summary
            
        Returns:
            str: Document summary
        """
        key_sentences = self.extract_key_sentences(document_text, max_sentences)
        
        if not key_sentences:
            return "No content to summarize."
        
        # Sort by position in document for coherent summary
        summary = " ".join([sentence for sentence, score in key_sentences])
        return summary
    
    def analyze_document_topics(self, document_text: str) -> Dict[str, float]:
        """
        Analyze document for key topics (simplified topic detection)
        
        Args:
            document_text (str): Document text to analyze
            
        Returns:
            Dict[str, float]: Dictionary of topics and their relevance scores
        """
        # Common medical/scientific topics
        topics = {
            "treatment": ["treatment", "therapy", "medication", "drug", "prescription"],
            "research": ["study", "research", "experiment", "trial", "investigation"],
            "diagnosis": ["diagnosis", "diagnostic", "test", "examination", "screening"],
            "prevention": ["prevention", "preventive", "prophylaxis", "vaccination"],
            "side_effects": ["side effect", "adverse", "reaction", "symptom"],
            "mechanism": ["mechanism", "pathway", "process", "function"],
            "clinical": ["clinical", "patient", "hospital", "medical"],
            "statistics": ["statistic", "data", "percentage", "rate", "frequency"]
        }
        
        document_lower = document_text.lower()
        topic_scores = {}
        
        for topic, keywords in topics.items():
            score = sum(1 for keyword in keywords if keyword in document_lower)
            if score > 0:
                topic_scores[topic] = min(score / len(keywords), 1.0)
        
        return topic_scores
    
    def get_document_insights(self, document_text: str, query: str = "") -> Dict:
        """
        Get comprehensive insights from document
        
        Args:
            document_text (str): Document text to analyze
            query (str): Optional query to find relevant sections
            
        Returns:
            Dict: Dictionary containing document insights
        """
        insights = {
            "summary": self.summarize_document(document_text),
            "topics": self.analyze_document_topics(document_text),
            "key_sentences": self.extract_key_sentences(document_text, 3)
        }
        
        if query:
            insights["relevant_sections"] = self.find_similar_sections(query, document_text, 3)
            
        return insights