"""
Stripe Test Module
==================
Unit and integration tests for Stripe modules.
"""

from .test_simulate import TestPaymentSimulator, TestTerminalMock
from .test_model import TestTransactionModel, TestEscrowModel, TestPaymentIntentModel
from .test_evaluate import TestRiskEngine, TestFraudDetector

__all__ = [
    "TestPaymentSimulator",
    "TestTerminalMock",
    "TestTransactionModel",
    "TestEscrowModel",
    "TestPaymentIntentModel",
    "TestRiskEngine",
    "TestFraudDetector",
]


def run_tests():
    """Run all Stripe module tests"""
    import unittest
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add tests from all modules
    suite.addTests(loader.loadTestsFromModule(TestPaymentSimulator()))
    suite.addTests(loader.loadTestsFromModule(TestTerminalMock()))
    suite.addTests(loader.loadTestsFromModule(TestTransactionModel()))
    suite.addTests(loader.loadTestsFromModule(TestEscrowModel()))
    suite.addTests(loader.loadTestsFromModule(TestPaymentIntentModel()))
    suite.addTests(loader.loadTestsFromModule(TestRiskEngine()))
    suite.addTests(loader.loadTestsFromModule(TestFraudDetector()))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()
