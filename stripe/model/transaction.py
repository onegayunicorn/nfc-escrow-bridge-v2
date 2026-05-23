from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import json

@dataclass
class StripeTransaction:
    """Models a Stripe transaction for the Escrow Bridge."""
    transaction_id: str
    amount: int
    currency: str
    status: str
    metadata: Dict[str, Any]
    timestamp: int
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_stripe_response(cls, response: Dict[str, Any]):
        return cls(
            transaction_id=response.get("id", ""),
            amount=response.get("amount", 0),
            currency=response.get("currency", "usd"),
            status=response.get("status", "unknown"),
            metadata=response.get("metadata", {}),
            timestamp=response.get("created", 0)
        )

class TransactionModeler:
    """Handles data modeling for escrow-linked transactions."""
    
    def model_escrow_payment(self, stripe_data: Dict[str, Any], escrow_id: str) -> StripeTransaction:
        tx = StripeTransaction.from_stripe_response(stripe_data)
        tx.metadata["escrow_id"] = escrow_id
        return tx
