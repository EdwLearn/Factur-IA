"""
ML-powered product matching service
"""
import asyncio
from typing import List, Dict, Any, Tuple, Optional
from decimal import Decimal
import logging
from sentence_transformers import SentenceTransformer
from fuzzywuzzy import fuzz
import numpy as np

logger = logging.getLogger(__name__)

class IntelligentProductMatcher:
    """Smart product matching using ML + fuzzy matching"""
    
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load sentence transformer model"""
        try:
            # Usar modelo multilingüe para español
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("Product matching model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load ML model: {e}")
            self.model = None
    
    async def find_similar_products(self, 
                                   new_description: str, 
                                   existing_products: List[Dict],
                                   threshold: float = 0.75) -> List[Dict]:
        """
        Find similar products using ML + fuzzy matching
        """
        if not existing_products:
            return []
        
        matches = []
        
        # 1. Fuzzy string matching (fast)
        for product in existing_products:
            existing_desc = product.get('description', '')
            fuzzy_score = fuzz.ratio(new_description.lower(), existing_desc.lower()) / 100
            
            if fuzzy_score >= threshold:
                matches.append({
                    'product': product,
                    'similarity_score': fuzzy_score,
                    'match_type': 'fuzzy',
                    'confidence': 'high' if fuzzy_score > 0.9 else 'medium'
                })
        
        # 2. ML semantic matching (if available and no good fuzzy matches)
        if self.model and len(matches) < 3:
            try:
                semantic_matches = await self._semantic_matching(
                    new_description, existing_products, threshold
                )
                matches.extend(semantic_matches)
            except Exception as e:
                logger.warning(f"Semantic matching failed: {e}")
        
        # Sort by similarity score
        matches.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return matches[:5]  # Top 5 matches
    
    async def _semantic_matching(self, 
                                new_description: str,
                                existing_products: List[Dict],
                                threshold: float) -> List[Dict]:
        """Semantic similarity using embeddings"""
        
        # Get embeddings
        descriptions = [new_description] + [p.get('description', '') for p in existing_products]
        embeddings = self.model.encode(descriptions)
        
        new_embedding = embeddings[0]
        existing_embeddings = embeddings[1:]
        
        # Calculate cosine similarity
        similarities = np.dot(existing_embeddings, new_embedding) / (
            np.linalg.norm(existing_embeddings, axis=1) * np.linalg.norm(new_embedding)
        )
        
        matches = []
        for i, similarity in enumerate(similarities):
            if similarity >= threshold:
                matches.append({
                    'product': existing_products[i],
                    'similarity_score': float(similarity),
                    'match_type': 'semantic',
                    'confidence': 'high' if similarity > 0.85 else 'medium'
                })
        
        return matches
