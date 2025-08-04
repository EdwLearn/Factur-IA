
"""
ML-powered product category classification using zero-shot learning
"""
from typing import Dict, Any, Optional
import logging
from transformers import pipeline
import re

logger = logging.getLogger(__name__)

class ProductCategoryClassifier:
    """Smart product categorization using ML zero-shot classification"""
    
    def __init__(self):
        self.classifier = None
        self.categories = [
            'calzado y zapatos',           # shoes
            'ropa y vestimenta',           # clothing  
            'electrónicos y tecnología',   # electronics
            'accesorios y joyería',        # accessories
            'deportes y ejercicio',        # sports
            'hogar y decoración',          # home
            'belleza y cuidado personal',  # beauty
            'juguetes y entretenimiento',  # toys
            'herramientas y ferretería',   # tools
            'productos de oficina',        # office
            'productos generales'          # general
        ]
        
        # Mapping to English categories for pricing engine
        self.category_mapping = {
            'calzado y zapatos': 'shoes',
            'ropa y vestimenta': 'clothing',
            'electrónicos y tecnología': 'electronics', 
            'accesorios y joyería': 'accessories',
            'deportes y ejercicio': 'sports',
            'hogar y decoración': 'home',
            'belleza y cuidado personal': 'beauty',
            'juguetes y entretenimiento': 'toys',
            'herramientas y ferretería': 'tools',
            'productos de oficina': 'office',
            'productos generales': 'general'
        }
        
        # Default margins per category
        self.category_margins = {
            'shoes': 55.0,
            'clothing': 60.0,
            'electronics': 35.0,
            'accessories': 70.0,
            'sports': 50.0,
            'home': 45.0,
            'beauty': 65.0,
            'toys': 60.0,
            'tools': 40.0,
            'office': 45.0,
            'general': 50.0
        }
        
        self._load_model()
    
    def _load_model(self):
        """Load zero-shot classification model"""
        try:
            # Using a smaller, faster model for production
            self.classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1  # Use CPU (set to 0 for GPU)
            )
            logger.info("Zero-shot classification model loaded successfully")
        except Exception as e:
            logger.error(f"Could not load ML classification model: {e}")
            self.classifier = None
    
    def classify_product(self, description: str) -> Dict[str, Any]:
        """
        Classify product using ML zero-shot classification
        
        Returns:
            Dict with category, confidence, and margin info
        """
        if not description or not description.strip():
            return self._get_default_classification()
        
        # Clean description for better classification
        clean_desc = self._clean_description(description)
        
        if self.classifier:
            try:
                result = self._ml_classify(clean_desc)
                return result
            except Exception as e:
                logger.warning(f"ML classification failed: {e}")
                return self._fallback_classify(clean_desc)
        else:
            return self._fallback_classify(clean_desc)
    
    def _ml_classify(self, description: str) -> Dict[str, Any]:
        """Use ML model for classification"""
        result = self.classifier(description, self.categories)
        
        spanish_category = result['labels'][0]
        english_category = self.category_mapping.get(spanish_category, 'general')
        confidence = result['scores'][0]
        
        return {
            'category': english_category,
            'category_spanish': spanish_category,
            'confidence': confidence,
            'margin_percentage': self.category_margins.get(english_category, 50.0),
            'method': 'ml_zero_shot',
            'all_scores': dict(zip(
                [self.category_mapping.get(cat, 'general') for cat in result['labels']],
                result['scores']
            ))
        }
    
    def _fallback_classify(self, description: str) -> Dict[str, Any]:
        """Fallback keyword-based classification"""
        desc_lower = description.lower()
        
        # Enhanced keyword categories
        keyword_categories = {
            'shoes': {
                'keywords': [
                    'zapato', 'calzado', 'sandalia', 'bota', 'tenis', 'chancleta',
                    'mocasin', 'tacón', 'deportivo', 'formal', 'casual', 'nike',
                    'adidas', 'converse', 'puma', 'crocs'
                ],
                'confidence': 0.90
            },
            'clothing': {
                'keywords': [
                    'camiseta', 'camisa', 'pantalon', 'vestido', 'falda', 'sudadera',
                    'chaqueta', 'blusa', 'short', 'jean', 'algodón', 'polyester',
                    'talla', 'manga', 'cuello', 'polo', 'hoodie'
                ],
                'confidence': 0.85
            },
            'electronics': {
                'keywords': [
                    'telefono', 'celular', 'computador', 'tablet', 'audifonos',
                    'parlante', 'cargador', 'cable', 'usb', 'bluetooth', 'wifi',
                    'samsung', 'apple', 'xiaomi', 'huawei', 'iphone', 'android'
                ],
                'confidence': 0.95
            },
            'sports': {
                'keywords': [
                    'pelota', 'balon', 'deporte', 'gimnasio', 'ejercicio', 'fitness',
                    'pesa', 'yoga', 'natacion', 'futbol', 'basketball', 'tenis',
                    'mancuerna', 'banda', 'colchoneta'
                ],
                'confidence': 0.88
            },
            'beauty': {
                'keywords': [
                    'crema', 'shampoo', 'perfume', 'maquillaje', 'labial', 'base',
                    'mascarilla', 'serum', 'locion', 'gel', 'jabon', 'cosmetico',
                    'skincare', 'facial'
                ],
                'confidence': 0.92
            },
            'accessories': {
                'keywords': [
                    'collar', 'pulsera', 'reloj', 'gafas', 'bolsa', 'cartera',
                    'cinturon', 'sombrero', 'gorra', 'lentes', 'anillo', 'arete'
                ],
                'confidence': 0.87
            },
            'home': {
                'keywords': [
                    'mesa', 'silla', 'sofa', 'cama', 'lampara', 'cortina',
                    'almohada', 'sabana', 'toalla', 'cocina', 'baño', 'decoracion',
                    'organizador', 'estante'
                ],
                'confidence': 0.80
            }
        }
        
        # Calculate scores for each category
        best_category = 'general'
        best_score = 0
        best_confidence = 0.60
        
        for category, config in keyword_categories.items():
            score = sum(1 for keyword in config['keywords'] if keyword in desc_lower)
            if score > best_score:
                best_score = score
                best_category = category
                best_confidence = min(config['confidence'], config['confidence'] + (score - 1) * 0.05)
        
        return {
            'category': best_category,
            'category_spanish': self._get_spanish_name(best_category),
            'confidence': best_confidence,
            'margin_percentage': self.category_margins.get(best_category, 50.0),
            'method': 'keyword_fallback',
            'keyword_matches': best_score
        }
    
    def _clean_description(self, description: str) -> str:
        """Clean and normalize product description"""
        # Remove extra spaces and normalize
        clean = re.sub(r'\s+', ' ', description.strip())
        
        # Remove common noise words that don't help classification
        noise_words = ['ref', 'codigo', 'item', 'producto', 'unidad', 'pieza']
        words = clean.lower().split()
        clean_words = [word for word in words if word not in noise_words]
        
        return ' '.join(clean_words)
    
    def _get_spanish_name(self, english_category: str) -> str:
        """Get Spanish name for English category"""
        reverse_mapping = {v: k for k, v in self.category_mapping.items()}
        return reverse_mapping.get(english_category, 'productos generales')
    
    def _get_default_classification(self) -> Dict[str, Any]:
        """Default classification for empty/invalid descriptions"""
        return {
            'category': 'general',
            'category_spanish': 'productos generales',
            'confidence': 0.50,
            'margin_percentage': 50.0,
            'method': 'default'
        }
    
    def get_category_margin(self, category: str) -> float:
        """Get default margin for a category"""
        return self.category_margins.get(category, 50.0)
    
    def update_category_margins(self, new_margins: Dict[str, float]):
        """Update category margins based on business rules"""
        self.category_margins.update(new_margins)
        logger.info(f"Updated category margins: {new_margins}")

# Singleton instance
_classifier_instance = None

def get_category_classifier() -> ProductCategoryClassifier:
    """Get singleton instance of category classifier"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ProductCategoryClassifier()
    return _classifier_instance