from typing import Dict, Any

class RiskEvaluator:
    """Evaluates transaction risk for the NFC Escrow system."""
    
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        
    def evaluate_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Performs basic risk scoring on a transaction."""
        amount = transaction_data.get("amount", 0)
        risk_score = 0.1
        
        # Simple heuristics
        if amount > 1000000: # Over $10k
            risk_score += 0.5
        
        if transaction_data.get("currency") not in ["usd", "eur", "gbp"]:
            risk_score += 0.2
            
        is_safe = risk_score < self.threshold
        
        return {
            "risk_score": round(risk_score, 2),
            "is_safe": is_safe,
            "recommendation": "approve" if is_safe else "manual_review"
        }
