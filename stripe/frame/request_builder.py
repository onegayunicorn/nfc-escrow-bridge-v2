from typing import Dict, Any, Optional, List

class StripeFrameBuilder:
    """Frames requests for the Stripe API based on NFC/Escrow context."""
    
    def build_payment_intent_frame(
        self,
        amount: int,
        currency: str = "usd",
        customer_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Constructs a standard frame for a PaymentIntent creation."""
        frame = {
            "amount": amount,
            "currency": currency,
            "payment_method_types": ["card_present"],
            "capture_method": "manual" # Essential for Escrow
        }
        
        if customer_id:
            frame["customer"] = customer_id
            
        if metadata:
            frame["metadata"] = metadata
            
        return frame

    def build_terminal_config_frame(self, location_id: str) -> Dict[str, Any]:
        """Constructs a frame for terminal configuration."""
        return {
            "location": location_id,
            "configuration": {
                "tipping": {"eligible": True}
            }
        }
