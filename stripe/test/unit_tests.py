import unittest
from stripe.simulate.processor import StripeSimulator
from stripe.evaluate.risk import RiskEvaluator

class TestStripeModules(unittest.TestCase):
    
    def setUp(self):
        self.sim = StripeSimulator()
        self.evaluator = RiskEvaluator()
        
    def test_simulation(self):
        res = self.sim.simulate_payment_intent(500)
        self.assertEqual(res["status"], "succeeded")
        self.assertEqual(res["amount"], 500)
        
    def test_risk_evaluation(self):
        low_risk = {"amount": 100, "currency": "usd"}
        res = self.evaluator.evaluate_transaction(low_risk)
        self.assertTrue(res["is_safe"])
        
        high_risk = {"amount": 2000000, "currency": "xyz"}
        res = self.evaluator.evaluate_transaction(high_risk)
        self.assertFalse(res["is_safe"])

if __name__ == "__main__":
    unittest.main()
