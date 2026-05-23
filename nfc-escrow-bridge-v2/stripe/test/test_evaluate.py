#!/usr/bin/env python3
"""
Unit Tests for Stripe Evaluation Module
=========================================
Tests for RiskEngine and FraudDetector classes.
"""

import unittest
import time
from stripe.evaluate.risk_engine import RiskEngine, RiskAssessment, RiskLevel, RiskFactor
from stripe.evaluate.fraud_detector import FraudDetector, FraudAssessment, FraudType, FraudSignal


class TestRiskEngine(unittest.TestCase):
    """Tests for RiskEngine class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = RiskEngine()
    
    def test_assess_low_risk(self):
        """Test assessing a low-risk transaction"""
        tx = {
            "amount": 1000,  # $10.00
            "currency": "usd",
            "user_id": "user_1",
            "country": "US",
            "device_type": "mobile",
            "card_type": "credit",
            "ip_address": "192.168.1.100",
        }
        
        # Add some history for the user
        self.engine.transaction_history["user_1"] = [
            {**tx, "timestamp": time.time() - 3600},  # 1 hour ago
            {**tx, "timestamp": time.time() - 7200},  # 2 hours ago
        ]
        
        assessment = self.engine.assess(tx, "user_1")
        
        self.assertIsInstance(assessment, RiskAssessment)
        self.assertLess(assessment.score, 30)  # Should be low risk
        self.assertEqual(assessment.level, RiskLevel.LOW)
        self.assertEqual(assessment.recommendation, "approve")
    
    def test_assess_high_risk(self):
        """Test assessing a high-risk transaction"""
        tx = {
            "amount": 500000,  # $5000.00
            "currency": "usd",
            "user_id": "user_2",  # New user
            "country": "RU",  # High-risk country
            "device_type": "mobile",
            "card_type": "prepaid",
            "ip_address": "103.86.96.1",  # Known VPN
        }
        
        assessment = self.engine.assess(tx, "user_2")
        
        self.assertIsInstance(assessment, RiskAssessment)
        self.assertGreater(assessment.score, 70)  # Should be high risk
        self.assertIn(assessment.level, [RiskLevel.HIGH, RiskLevel.VERY_HIGH, RiskLevel.CRITICAL])
        self.assertIn(assessment.recommendation, ["flag_for_review", "reject"])
    
    def test_assess_medium_risk(self):
        """Test assessing a medium-risk transaction"""
        tx = {
            "amount": 100000,  # $1000.00
            "currency": "usd",
            "user_id": "user_3",  # New user
            "country": "US",
            "device_type": "mobile",
            "card_type": "credit",
            "ip_address": "192.168.1.102",
        }
        
        assessment = self.engine.assess(tx, "user_3")
        
        self.assertIsInstance(assessment, RiskAssessment)
        self.assertGreater(assessment.score, 30)
        self.assertLess(assessment.score, 70)
        self.assertEqual(assessment.level, RiskLevel.MEDIUM)
        self.assertEqual(assessment.recommendation, "review")
    
    def test_assess_batch(self):
        """Test assessing multiple transactions"""
        txs = [
            {"amount": 1000, "currency": "usd", "user_id": "user_1", "country": "US"},
            {"amount": 5000, "currency": "usd", "user_id": "user_2", "country": "GB"},
            {"amount": 10000, "currency": "usd", "user_id": "user_3", "country": "CA"},
        ]
        
        assessments = self.engine.assess_batch(txs)
        
        self.assertEqual(len(assessments), 3)
        for assessment in assessments:
            self.assertIsInstance(assessment, RiskAssessment)
    
    def test_add_rule(self):
        """Test adding a custom rule"""
        from stripe.evaluate.risk_engine import RiskRule
        
        rule = RiskRule(
            name="test_rule",
            factor=RiskFactor.AMOUNT,
            condition=lambda tx: tx.get("amount", 0) > 1000000,
            score=90.0,
            description="Test rule",
        )
        
        self.engine.add_rule(rule)
        
        self.assertEqual(len(self.engine.rules), len(self.engine._initial_default_rules()) + 1)
    
    def test_remove_rule(self):
        """Test removing a rule"""
        initial_count = len(self.engine.rules)
        
        # Remove a default rule
        removed = self.engine.remove_rule("high_amount")
        
        self.assertTrue(removed)
        self.assertEqual(len(self.engine.rules), initial_count - 1)
    
    def test_set_weight(self):
        """Test setting weight for a factor"""
        self.engine.set_weight(RiskFactor.AMOUNT, 0.5)
        
        weights = self.engine.get_weights()
        self.assertEqual(weights[RiskFactor.AMOUNT], 0.5)
    
    def test_get_stats(self):
        """Test getting engine statistics"""
        self.engine.assess({"amount": 1000, "currency": "usd", "user_id": "user_1"})
        self.engine.assess({"amount": 2000, "currency": "usd", "user_id": "user_2"})
        
        stats = self.engine.get_stats()
        
        self.assertEqual(stats["total_assessments"], 2)
        self.assertEqual(stats["unique_users"], 2)
    
    def test_reset(self):
        """Test resetting engine"""
        self.engine.assess({"amount": 1000, "currency": "usd", "user_id": "user_1"})
        self.engine.reset()
        
        stats = self.engine.get_stats()
        self.assertEqual(stats["total_assessments"], 0)


class TestFraudDetector(unittest.TestCase):
    """Tests for FraudDetector class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = FraudDetector()
    
    def test_detect_low_fraud(self):
        """Test detecting low fraud probability"""
        tx = {
            "amount": 1000,
            "currency": "usd",
            "user_id": "user_1",
            "country": "US",
            "device_type": "mobile",
            "ip_address": "192.168.1.100",
            "payment_method": "pm_1",
        }
        
        # Add some history
        self.detector.user_transactions["user_1"] = [
            {**tx, "timestamp": time.time() - 3600},
            {**tx, "timestamp": time.time() - 7200},
        ]
        
        assessment = self.detector.detect(tx, "user_1")
        
        self.assertIsInstance(assessment, FraudAssessment)
        self.assertFalse(assessment.is_fraud)
        self.assertLess(assessment.fraud_probability, 0.3)
        self.assertEqual(assessment.recommendation, "approve")
    
    def test_detect_high_fraud(self):
        """Test detecting high fraud probability"""
        tx = {
            "amount": 500000,
            "currency": "usd",
            "user_id": "user_2",  # New user
            "country": "RU",
            "device_type": "mobile",
            "ip_address": "103.86.96.1",  # Known VPN
            "payment_method": "pm_2",
        }
        
        assessment = self.detector.detect(tx, "user_2")
        
        self.assertIsInstance(assessment, FraudAssessment)
        self.assertTrue(assessment.is_fraud)
        self.assertGreater(assessment.fraud_probability, 0.5)
        self.assertIn(assessment.recommendation, ["review", "reject"])
    
    def test_detect_vpn_ip(self):
        """Test detecting VPN IP"""
        tx = {
            "amount": 1000,
            "currency": "usd",
            "user_id": "user_3",
            "country": "US",
            "ip_address": "103.86.96.1",  # Known VPN
        }
        
        assessment = self.detector.detect(tx, "user_3")
        
        # Check for proxy signal
        proxy_signals = [s for s in assessment.signals if s.signal == FraudSignal.PROXY_IP]
        self.assertEqual(len(proxy_signals), 1)
        self.assertTrue(proxy_signals[0].detected)
    
    def test_detect_high_velocity(self):
        """Test detecting high velocity"""
        user_id = "user_4"
        
        # Create history with high velocity
        for i in range(6):
            self.detector.user_transactions[user_id].append({
                "amount": 1000,
                "currency": "usd",
                "user_id": user_id,
                "country": "US",
                "ip_address": "192.168.1.100",
                "timestamp": time.time() - (i * 10),  # Last 60 seconds
            })
        
        tx = {
            "amount": 1000,
            "currency": "usd",
            "user_id": user_id,
            "country": "US",
            "ip_address": "192.168.1.100",
        }
        
        assessment = self.detector.detect(tx, user_id)
        
        # Check for velocity signal
        velocity_signals = [s for s in assessment.signals if s.signal == FraudSignal.HIGH_VELOCITY]
        self.assertEqual(len(velocity_signals), 1)
        self.assertTrue(velocity_signals[0].detected)
    
    def test_add_fraud_pattern(self):
        """Test adding a custom fraud pattern"""
        pattern = {
            "name": "test_pattern",
            "type": FraudType.CARD_TESTING,
            "conditions": [
                lambda tx, history: len(history) > 10,
            ],
            "score": 95.0,
        }
        
        self.detector.add_fraud_pattern(pattern)
        
        self.assertEqual(len(self.detector.fraud_patterns), len(self.detector._initial_fraud_patterns()) + 1)
    
    def test_remove_fraud_pattern(self):
        """Test removing a fraud pattern"""
        initial_count = len(self.detector.fraud_patterns)
        
        removed = self.detector.remove_fraud_pattern("card_testing")
        
        self.assertTrue(removed)
        self.assertEqual(len(self.detector.fraud_patterns), initial_count - 1)
    
    def test_register_device(self):
        """Test registering a device fingerprint"""
        from stripe.evaluate.fraud_detector import DeviceFingerprint
        
        fingerprint = DeviceFingerprint(
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.100",
            device_type="mobile",
            os="Android",
            browser="Chrome",
        )
        
        fp_id = self.detector.register_device(fingerprint)
        
        self.assertIsNotNone(fp_id)
        self.assertIn(fp_id, self.detector.device_fingerprints)
    
    def test_get_stats(self):
        """Test getting detector statistics"""
        self.detector.detect({"amount": 1000, "currency": "usd", "user_id": "user_1", "ip_address": "192.168.1.100"})
        self.detector.detect({"amount": 2000, "currency": "usd", "user_id": "user_2", "ip_address": "192.168.1.101"})
        
        stats = self.detector.get_stats()
        
        self.assertEqual(stats["total_transactions"], 2)
        self.assertEqual(stats["unique_users"], 2)
        self.assertEqual(stats["unique_ips"], 2)
    
    def test_reset(self):
        """Test resetting detector"""
        self.detector.detect({"amount": 1000, "currency": "usd", "user_id": "user_1"})
        self.detector.reset()
        
        stats = self.detector.get_stats()
        self.assertEqual(stats["total_transactions"], 0)


if __name__ == "__main__":
    unittest.main()
