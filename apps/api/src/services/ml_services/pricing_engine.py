"""
ML-powered pricing recommendation engine with smart categorization
"""
from typing import Dict, List, Optional
from decimal import Decimal
import logging
from datetime import datetime, timedelta
import statistics
from .category_classifier import get_category_classifier
from .price_utils import (
    round_price_colombian, 
    format_colombian_price,
    calculate_rounded_margin,
    suggest_price_alternatives,
    validate_price_business_rules
)

logger = logging.getLogger(__name__)

class PricingRecommendationEngine:
    """Smart pricing recommendations using ML categorization + historical data"""
    
    def __init__(self):
        self.category_classifier = get_category_classifier()
        
        # Business rules for pricing
        self.min_markup = 20.0  # Minimum 20% markup
        self.max_markup = 200.0  # Maximum 200% markup
        
        # Market adjustment factors
        self.market_factors = {
            'high_demand': 1.15,    # 15% premium for high-demand items
            'seasonal': 1.10,       # 10% for seasonal items
            'bulk_discount': 0.95   # 5% discount for bulk items
        }
    
    async def recommend_sale_price(self,
                                 product_code: str,
                                 description: str,
                                 cost_price: Decimal,
                                 quantity: Decimal,
                                 historical_data: List[Dict] = None,
                                 supplier: Optional[str] = None) -> Dict:
        """
        Comprehensive pricing recommendation using multiple ML and business factors
        """
        historical_data = historical_data or []
        
        try:
            # 1. ML-powered product categorization
            category_info = self.category_classifier.classify_product(description)
            logger.info(f"Product '{description[:50]}...' classified as: {category_info['category']} "
                       f"(confidence: {category_info['confidence']:.2f})")
            
            # 2. Historical pricing analysis
            historical_price = self._get_historical_price(product_code, historical_data)
            
            # 3. Supplier pattern analysis
            supplier_margin = self._get_supplier_margin(supplier, historical_data)
            
            # 4. Quantity-based adjustments
            quantity_factor = self._get_quantity_factor(quantity)
            
            # 5. Generate multiple recommendations with Colombian rounding
            recommendations = []
            
            # Category-based recommendation
            category_margin = category_info['margin_percentage']
            category_price_raw = cost_price * (1 + category_margin / 100) * quantity_factor
            category_price = round_price_colombian(category_price_raw)
            
            recommendations.append({
                'price': category_price,
                'price_formatted': format_colombian_price(category_price),
                'confidence': category_info['confidence'],
                'reasoning': f"ML categorizado como '{category_info['category_spanish']}' "
                           f"(margen {category_margin}%)",
                'method': 'ml_category',
                'margin': calculate_rounded_margin(cost_price, category_price)
            })
            
            # Historical-based recommendation (if available)
            if historical_price:
                historical_price_rounded = round_price_colombian(historical_price * quantity_factor)
                historical_margin = calculate_rounded_margin(cost_price, historical_price_rounded)
                recommendations.append({
                    'price': historical_price_rounded,
                    'price_formatted': format_colombian_price(historical_price_rounded),
                    'confidence': 0.95,
                    'reasoning': f"Basado en precio histórico del producto (margen {historical_margin:.1f}%)",
                    'method': 'historical',
                    'margin': historical_margin
                })
            
            # Supplier pattern recommendation (if available)
            if supplier_margin:
                supplier_price_raw = cost_price * (1 + supplier_margin / 100) * quantity_factor
                supplier_price = round_price_colombian(supplier_price_raw)
                recommendations.append({
                    'price': supplier_price,
                    'price_formatted': format_colombian_price(supplier_price),
                    'confidence': 0.85,
                    'reasoning': f"Patrón del proveedor {supplier} (margen promedio {supplier_margin:.1f}%)",
                    'method': 'supplier_pattern',
                    'margin': calculate_rounded_margin(cost_price, supplier_price)
                })
            
            # Conservative recommendation (for risk-averse pricing)
            conservative_margin = max(category_margin * 0.8, self.min_markup)
            conservative_price_raw = cost_price * (1 + conservative_margin / 100) * quantity_factor
            conservative_price = round_price_colombian(conservative_price_raw)
            
            recommendations.append({
                'price': conservative_price,
                'price_formatted': format_colombian_price(conservative_price),
                'confidence': 0.70,
                'reasoning': f"Opción conservadora (margen {conservative_margin:.1f}%)",
                'method': 'conservative',
                'margin': calculate_rounded_margin(cost_price, conservative_price)
            })
            
            # Aggressive recommendation (for high-margin strategy)
            aggressive_margin = min(category_margin * 1.3, self.max_markup)
            aggressive_price_raw = cost_price * (1 + aggressive_margin / 100) * quantity_factor
            aggressive_price = round_price_colombian(aggressive_price_raw)
            
            recommendations.append({
                'price': aggressive_price,
                'price_formatted': format_colombian_price(aggressive_price),
                'confidence': 0.60,
                'reasoning': f"Opción agresiva para mayor margen ({aggressive_margin:.1f}%)",
                'method': 'aggressive',
                'margin': calculate_rounded_margin(cost_price, aggressive_price)
            })
            
            # Apply business rule validations
            recommendations = self._validate_recommendations(recommendations, cost_price)
            
            # Select best recommendation (highest confidence with reasonable margin)
            best_rec = self._select_best_recommendation(recommendations)
            
            # Calculate additional metrics
            profit_per_unit = best_rec['price'] - cost_price
            total_profit = profit_per_unit * quantity
            roi_percentage = (profit_per_unit / cost_price) * 100
            
            return {
                'recommended_price': float(best_rec['price']),
                'confidence': best_rec['confidence'],
                'reasoning': best_rec['reasoning'],
                'method': best_rec['method'],
                'margin_percentage': float(best_rec['margin']),
                'category_info': category_info,
                'profit_per_unit': float(profit_per_unit),
                'total_profit': float(total_profit),
                'roi_percentage': float(roi_percentage),
                'quantity_factor': float(quantity_factor),
                'all_recommendations': [
                    {
                        'price': float(rec['price']),
                        'confidence': rec['confidence'],
                        'reasoning': rec['reasoning'],
                        'method': rec['method'],
                        'margin': float(rec['margin'])
                    }
                    for rec in recommendations
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating pricing recommendation: {str(e)}")
            # Fallback to simple calculation
            return self._fallback_pricing(cost_price, quantity)
    
    def _get_historical_price(self, product_code: str, historical_data: List[Dict]) -> Optional[Decimal]:
        """Analyze historical pricing for this specific product"""
        if not product_code:
            return None
            
        product_history = [
            item for item in historical_data 
            if item.get('product_code') == product_code and 
               item.get('sale_price') and 
               item.get('sale_price') > 0
        ]
        
        if len(product_history) >= 2:  # Need at least 2 data points
            # Use recent prices with more weight
            recent_cutoff = datetime.now() - timedelta(days=90)
            recent_prices = []
            older_prices = []
            
            for item in product_history:
                price = Decimal(str(item['sale_price']))
                item_date = item.get('date')
                
                if item_date and item_date > recent_cutoff:
                    recent_prices.append(price)
                else:
                    older_prices.append(price)
            
            if recent_prices:
                return Decimal(str(statistics.median(recent_prices)))
            elif older_prices:
                return Decimal(str(statistics.median(older_prices)))
        
        return None
    
    def _get_supplier_margin(self, supplier: str, historical_data: List[Dict]) -> Optional[float]:
        """Calculate average margin for this supplier"""
        if not supplier:
            return None
            
        supplier_items = [
            item for item in historical_data 
            if (item.get('supplier', '').lower() == supplier.lower() and 
                item.get('sale_price') and item.get('cost_price') and
                item.get('sale_price') > 0 and item.get('cost_price') > 0)
        ]
        
        if len(supplier_items) >= 3:  # Need at least 3 data points for reliability
            margins = []
            for item in supplier_items:
                cost = Decimal(str(item['cost_price']))
                sale = Decimal(str(item['sale_price']))
                
                if cost > 0:  # Avoid division by zero
                    margin = ((sale - cost) / cost) * 100
                    # Filter out unrealistic margins
                    if self.min_markup <= margin <= self.max_markup:
                        margins.append(float(margin))
            
            if len(margins) >= 2:
                return statistics.median(margins)
        
        return None
    
    def _get_quantity_factor(self, quantity: Decimal) -> float:
        """Apply quantity-based pricing adjustments"""
        qty = float(quantity)
        
        if qty >= 50:
            return 0.95  # 5% discount for bulk (50+ units)
        elif qty >= 20:
            return 0.98  # 2% discount for medium bulk (20+ units)
        elif qty <= 3:
            return 1.05  # 5% premium for small quantities (1-3 units)
        else:
            return 1.0   # No adjustment for normal quantities
    
    def _validate_recommendations(self, recommendations: List[Dict], cost_price: Decimal) -> List[Dict]:
        """Apply business rules validation to recommendations"""
        validated = []
        
        for rec in recommendations:
            margin = ((rec['price'] - cost_price) / cost_price) * 100
            
            # Ensure minimum and maximum margins
            if margin < self.min_markup:
                new_price = cost_price * (1 + self.min_markup / 100)
                rec['price'] = new_price
                rec['margin'] = self.min_markup
                rec['reasoning'] += f" (ajustado a margen mínimo {self.min_markup}%)"
            
            elif margin > self.max_markup:
                new_price = cost_price * (1 + self.max_markup / 100)
                rec['price'] = new_price
                rec['margin'] = self.max_markup
                rec['reasoning'] += f" (ajustado a margen máximo {self.max_markup}%)"
            
            validated.append(rec)
        
        return validated
    
    def _select_best_recommendation(self, recommendations: List[Dict]) -> Dict:
        """Select the best recommendation based on confidence and business logic"""
        # Sort by confidence first, then by reasonableness of margin
        def recommendation_score(rec):
            confidence = rec['confidence']
            margin = rec['margin']
            
            # Prefer margins in the sweet spot (30-80%)
            margin_score = 1.0
            if 30 <= margin <= 80:
                margin_score = 1.2
            elif margin < 30:
                margin_score = 0.8
            elif margin > 100:
                margin_score = 0.7
            
            return confidence * margin_score
        
        recommendations.sort(key=recommendation_score, reverse=True)
        return recommendations[0]
    
    def _fallback_pricing(self, cost_price: Decimal, quantity: Decimal) -> Dict:
        """Fallback pricing when ML fails"""
        logger.warning("Using fallback pricing calculation")
        
        quantity_factor = self._get_quantity_factor(quantity)
        fallback_margin = 50.0  # 50% default margin
        fallback_price_raw = cost_price * (1 + fallback_margin / 100) * quantity_factor
        fallback_price = round_price_colombian(fallback_price_raw)
        
        return {
            'recommended_price': float(fallback_price),
            'recommended_price_formatted': format_colombian_price(fallback_price),
            'confidence': 0.50,
            'reasoning': 'Cálculo de respaldo (50% margen estándar)',
            'method': 'fallback',
            'margin_percentage': float(calculate_rounded_margin(cost_price, fallback_price)),
            'category_info': {'category': 'general', 'confidence': 0.5},
            'profit_per_unit': float(fallback_price - cost_price),
            'total_profit': float((fallback_price - cost_price) * quantity),
            'roi_percentage': float(calculate_rounded_margin(cost_price, fallback_price)),
            'quantity_factor': quantity_factor,
            'validation': validate_price_business_rules(cost_price, fallback_price)
        }

# Singleton instance
_pricing_engine_instance = None

def get_pricing_engine() -> PricingRecommendationEngine:
    """Get singleton instance of pricing engine"""
    global _pricing_engine_instance
    if _pricing_engine_instance is None:
        _pricing_engine_instance = PricingRecommendationEngine()
    return _pricing_engine_instance