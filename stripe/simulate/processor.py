import random
import time
from typing import Dict, Any, Optional

class StripeSimulator:
    """Simulates Stripe Terminal and Payment Intent operations."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "sk_test_simulated"
        self.active_readers = ["tmr_123", "tmr_456"]
        
    def simulate_payment_intent(self, amount: int, currency: str = "usd") -> Dict[str, Any]:
        """Simulates the creation and processing of a PaymentIntent."""
        pi_id = f"pi_sim_{random.randint(1000, 9999)}"
        print(f"Creating simulated PaymentIntent: {pi_id} for {amount} {currency}")
        
        # Simulate processing time
        time.sleep(0.5)
        
        return {
            "id": pi_id,
            "object": "payment_intent",
            "amount": amount,
            "currency": currency,
            "status": "succeeded",
            "payment_method": "pm_sim_visa",
            "created": int(time.time())
        }

    def simulate_terminal_handshake(self, reader_id: str) -> bool:
        """Simulates connection to a physical Stripe Terminal."""
        if reader_id in self.active_readers:
            print(f"Handshake successful with reader: {reader_id}")
            return True
        print(f"Handshake failed for reader: {reader_id}")
        return False

if __name__ == "__main__":
    sim = StripeSimulator()
    result = sim.simulate_payment_intent(2000)
    print(f"Simulation Result: {result}")
