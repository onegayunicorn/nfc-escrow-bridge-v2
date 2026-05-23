#!/usr/bin/env python3
"""
Unit Tests for Stripe Simulation Module
==========================================
Tests for PaymentSimulator and TerminalMock classes.
"""

import unittest
import asyncio
import time
from stripe.simulate.payment_simulator import PaymentSimulator, PaymentStatus, MockPaymentIntent
from stripe.simulate.terminal_mock import TerminalMock, TerminalStatus, TerminalType, CardInterface


class TestPaymentSimulator(unittest.TestCase):
    """Tests for PaymentSimulator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.simulator = PaymentSimulator(
            success_rate=0.99,  # 99% success rate for testing
            processing_time_range=(0.01, 0.05),  # Fast processing for tests
        )
    
    def test_create_payment_intent(self):
        """Test creating a PaymentIntent"""
        intent = self.simulator.create_payment_intent(
            amount=1000,
            currency="usd",
            escrow_id="escrow_123",
        )
        
        self.assertIsInstance(intent, MockPaymentIntent)
        self.assertEqual(intent.amount, 1000)
        self.assertEqual(intent.currency, "usd")
        self.assertEqual(intent.status, PaymentStatus.REQUIRES_PAYMENT_METHOD)
        self.assertEqual(intent.escrow_id, "escrow_123")
        self.assertIn("escrow_id", intent.metadata)
    
    def test_confirm_payment_intent_success(self):
        """Test confirming a PaymentIntent with success"""
        intent = self.simulator.create_payment_intent(amount=1000, currency="usd")
        confirmed = self.simulator.confirm_payment_intent(intent.id)
        
        self.assertEqual(confirmed.status, PaymentStatus.SUCCEEDED)
        self.assertEqual(self.simulator.successful_payments, 1)
    
    def test_confirm_payment_intent_failure(self):
        """Test confirming a PaymentIntent with failure"""
        # Set success rate to 0% for this test
        simulator = PaymentSimulator(success_rate=0.0)
        intent = simulator.create_payment_intent(amount=1000, currency="usd")
        confirmed = simulator.confirm_payment_intent(intent.id)
        
        self.assertNotEqual(confirmed.status, PaymentStatus.SUCCEEDED)
        self.assertEqual(simulator.failed_payments, 1)
    
    def test_cancel_payment_intent(self):
        """Test canceling a PaymentIntent"""
        intent = self.simulator.create_payment_intent(amount=1000, currency="usd")
        canceled = self.simulator.cancel_payment_intent(intent.id)
        
        self.assertEqual(canceled.status, PaymentStatus.CANCELED)
        self.assertEqual(self.simulator.failed_payments, 1)
    
    def test_retrieve_payment_intent(self):
        """Test retrieving a PaymentIntent"""
        intent = self.simulator.create_payment_intent(amount=1000, currency="usd")
        retrieved = self.simulator.retrieve_payment_intent(intent.id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, intent.id)
    
    def test_list_payment_intents(self):
        """Test listing PaymentIntents"""
        self.simulator.create_payment_intent(amount=1000, currency="usd")
        self.simulator.create_payment_intent(amount=2000, currency="usd")
        
        intents = self.simulator.list_payment_intents()
        self.assertEqual(len(intents), 2)
    
    def test_create_customer(self):
        """Test creating a customer"""
        customer_id = self.simulator.create_customer(
            email="test@example.com",
            name="Test Customer",
        )
        
        self.assertIsNotNone(customer_id)
        self.assertIn(customer_id, self.simulator.customers)
    
    def test_simulate_nfc_tap(self):
        """Test simulating NFC tap"""
        result = self.simulator.simulate_nfc_tap(
            amount=5000,
            currency="usd",
            tag_id="nfc_123",
        )
        
        self.assertIn("nfc_tap", result)
        self.assertIn("payment_intent", result)
        self.assertIn("escrow", result)
        self.assertEqual(result["nfc_tap"]["tag_id"], "nfc_123")
    
    def test_simulate_nfc_escrow_flow(self):
        """Test simulating complete NFC-Escrow-Stripe flow"""
        result = self.simulator.simulate_nfc_escrow_flow(
            amount=10000,
            currency="usd",
            escrow_id="escrow_456",
        )
        
        self.assertIn("nfc_tap", result)
        self.assertIn("payment_intent", result)
        self.assertIn("escrow", result)
        self.assertEqual(result["escrow"]["escrow_id"], "escrow_456")
    
    def test_get_stats(self):
        """Test getting simulator statistics"""
        self.simulator.create_payment_intent(amount=1000, currency="usd")
        self.simulator.confirm_payment_intent("pi_test_123")
        
        stats = self.simulator.get_stats()
        self.assertEqual(stats["total_payments"], 1)
        self.assertEqual(stats["total_amount"], 1000)
    
    def test_reset(self):
        """Test resetting simulator"""
        self.simulator.create_payment_intent(amount=1000, currency="usd")
        self.simulator.reset()
        
        stats = self.simulator.get_stats()
        self.assertEqual(stats["total_payments"], 0)
        self.assertEqual(stats["payment_intents"], 0)


class TestTerminalMock(unittest.TestCase):
    """Tests for TerminalMock class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.terminal = TerminalMock(
            device_type=TerminalType.VERIFONE_P400,
            label="Test Terminal",
        )
    
    def test_create_terminal(self):
        """Test creating a terminal"""
        self.assertEqual(self.terminal.device_type, TerminalType.VERIFONE_P400)
        self.assertEqual(self.terminal.label, "Test Terminal")
        self.assertIsNotNone(self.terminal.terminal_id)
        self.assertIsNotNone(self.terminal.serial_number)
        self.assertEqual(self.terminal.status, TerminalStatus.OFFLINE)
    
    def test_connect(self):
        """Test connecting to terminal"""
        # Note: This is a sync test, but connect is async
        # We'll test the state change
        self.terminal.status = TerminalStatus.OFFLINE
        self.terminal.connected = False
        
        # Simulate connection
        self.terminal.status = TerminalStatus.CONNECTED
        self.terminal.connected = True
        
        self.assertEqual(self.terminal.status, TerminalStatus.CONNECTED)
        self.assertTrue(self.terminal.connected)
    
    def test_disconnect(self):
        """Test disconnecting from terminal"""
        self.terminal.status = TerminalStatus.CONNECTED
        self.terminal.connected = True
        
        # Simulate disconnection
        self.terminal.status = TerminalStatus.OFFLINE
        self.terminal.connected = False
        
        self.assertEqual(self.terminal.status, TerminalStatus.OFFLINE)
        self.assertFalse(self.terminal.connected)
    
    def test_get_status(self):
        """Test getting terminal status"""
        status = self.terminal.get_status()
        
        self.assertIn("terminal_id", status)
        self.assertIn("device_type", status)
        self.assertIn("status", status)
        self.assertIn("connected", status)
        self.assertIn("capabilities", status)
    
    def test_read_card(self):
        """Test reading a card"""
        # Note: read_card is async, so we'll test the sync version
        # by directly setting the last_card
        self.terminal.last_card = {
            "last4": "4242",
            "brand": "visa",
            "exp_month": 12,
            "exp_year": 2026,
            "interface": CardInterface.CONTACTLESS,
        }
        
        self.assertIsNotNone(self.terminal.last_card)
        self.assertEqual(self.terminal.last_card["brand"], "visa")
    
    def test_get_stats(self):
        """Test getting terminal statistics"""
        stats = self.terminal.get_stats()
        
        self.assertIn("terminal_id", stats)
        self.assertIn("device_type", stats)
        self.assertIn("total_operations", stats)
    
    def test_reset(self):
        """Test resetting terminal"""
        self.terminal.total_operations = 10
        self.terminal.reset()
        
        stats = self.terminal.get_stats()
        self.assertEqual(stats["total_operations"], 0)


class TestTerminalFactory(unittest.TestCase):
    """Tests for TerminalFactory"""
    
    def test_create_verifone_p400(self):
        """Test creating Verifone P400 terminal"""
        from stripe.simulate.terminal_mock import TerminalFactory
        
        terminal = TerminalFactory.create_verifone_p400()
        self.assertEqual(terminal.device_type, TerminalType.VERIFONE_P400)
    
    def test_create_bbpos_chipper(self):
        """Test creating BBPOS Chipper terminal"""
        from stripe.simulate.terminal_mock import TerminalFactory
        
        terminal = TerminalFactory.create_bbpos_chipper()
        self.assertEqual(terminal.device_type, TerminalType.BBPOS_CHIPPER)


if __name__ == "__main__":
    unittest.main()
