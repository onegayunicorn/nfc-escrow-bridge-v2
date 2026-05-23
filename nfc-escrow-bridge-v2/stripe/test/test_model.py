#!/usr/bin/env python3
"""
Unit Tests for Stripe Model Module
===================================
Tests for TransactionModeler, EscrowRecord, and PaymentIntentData classes.
"""

import unittest
from stripe.model.transaction import (
    StripeTransaction, 
    EscrowTransaction, 
    TransactionModeler,
    TransactionStatus,
    TransactionType,
    Currency,
)
from stripe.model.escrow import EscrowRecord, EscrowState, EscrowConditionType
from stripe.model.payment_intent import PaymentIntentData, PaymentIntentModel, PaymentIntentStatus


class TestStripeTransaction(unittest.TestCase):
    """Tests for StripeTransaction model"""
    
    def test_create_stripe_transaction(self):
        """Test creating a StripeTransaction"""
        tx = StripeTransaction(
            id="pi_test_123",
            amount=1000,
            currency=Currency.USD,
            status="succeeded",
        )
        
        self.assertEqual(tx.id, "pi_test_123")
        self.assertEqual(tx.amount, 1000)
        self.assertEqual(tx.currency, Currency.USD)
        self.assertEqual(tx.status, "succeeded")
        self.assertEqual(tx.amount_usd, 10.0)
    
    def test_link_to_escrow(self):
        """Test linking to escrow"""
        tx = StripeTransaction(
            id="pi_test_123",
            amount=1000,
            currency=Currency.USD,
            status="succeeded",
        )
        
        tx.link_to_escrow("escrow_456")
        
        self.assertEqual(tx.escrow_id, "escrow_456")
        self.assertIn("escrow_id", tx.metadata)
    
    def test_to_dict(self):
        """Test converting to dictionary"""
        tx = StripeTransaction(
            id="pi_test_123",
            amount=1000,
            currency=Currency.USD,
        )
        
        d = tx.to_dict()
        self.assertIn("id", d)
        self.assertIn("amount", d)
        self.assertIn("currency", d)
    
    def test_to_json(self):
        """Test converting to JSON"""
        tx = StripeTransaction(
            id="pi_test_123",
            amount=1000,
            currency=Currency.USD,
        )
        
        j = tx.to_json()
        self.assertIsInstance(j, str)
        self.assertIn("pi_test_123", j)
    
    def test_from_stripe_response(self):
        """Test creating from Stripe API response"""
        response = {
            "id": "pi_test_123",
            "amount": 1000,
            "currency": "usd",
            "status": "succeeded",
            "payment_method": "pm_456",
            "customer": "cus_789",
        }
        
        tx = StripeTransaction.from_stripe_response(response, escrow_id="escrow_123")
        
        self.assertEqual(tx.id, "pi_test_123")
        self.assertEqual(tx.escrow_id, "escrow_123")
        self.assertIn("escrow_id", tx.metadata)


class TestEscrowTransaction(unittest.TestCase):
    """Tests for EscrowTransaction model"""
    
    def test_create_escrow_transaction(self):
        """Test creating an EscrowTransaction"""
        tx = EscrowTransaction(
            escrow_id="escrow_123",
            amount=5000,
            currency=Currency.USD,
            buyer={"id": "user_1"},
            seller={"id": "user_2"},
        )
        
        self.assertEqual(tx.escrow_id, "escrow_123")
        self.assertEqual(tx.amount, 5000)
        self.assertEqual(tx.currency, Currency.USD)
        self.assertEqual(tx.amount_usd, 50.0)
    
    def test_add_stripe_transaction(self):
        """Test adding a Stripe transaction"""
        tx = EscrowTransaction(
            escrow_id="escrow_123",
            amount=5000,
            currency=Currency.USD,
        )
        
        tx.add_stripe_transaction("pi_test_123")
        
        self.assertIn("pi_test_123", tx.stripe_transaction_ids)
    
    def test_add_payment_intent(self):
        """Test adding a PaymentIntent"""
        tx = EscrowTransaction(
            escrow_id="escrow_123",
            amount=5000,
            currency=Currency.USD,
        )
        
        tx.add_payment_intent("pi_test_456")
        
        self.assertIn("pi_test_456", tx.payment_intent_ids)
    
    def test_release(self):
        """Test releasing escrow"""
        tx = EscrowTransaction(
            escrow_id="escrow_123",
            amount=5000,
            currency=Currency.USD,
        )
        
        tx.release()
        
        self.assertEqual(tx.status, TransactionStatus.SUCCEEDED)
        self.assertIn("release_reason", tx.metadata)
    
    def test_cancel(self):
        """Test canceling escrow"""
        tx = EscrowTransaction(
            escrow_id="escrow_123",
            amount=5000,
            currency=Currency.USD,
        )
        
        tx.cancel()
        
        self.assertEqual(tx.status, TransactionStatus.CANCELED)
        self.assertIn("cancel_reason", tx.metadata)


class TestPaymentIntentData(unittest.TestCase):
    """Tests for PaymentIntentData model"""
    
    def test_create_payment_intent_data(self):
        """Test creating PaymentIntentData"""
        pi = PaymentIntentData(
            id="pi_test_123",
            amount=1000,
            currency=Currency.USD,
            status=PaymentIntentStatus.SUCCEEDED,
        )
        
        self.assertEqual(pi.id, "pi_test_123")
        self.assertEqual(pi.amount, 1000)
        self.assertEqual(pi.currency, Currency.USD)
        self.assertEqual(pi.status, PaymentIntentStatus.SUCCEEDED)
    
    def test_link_to_escrow(self):
        """Test linking to escrow"""
        pi = PaymentIntentData(
            id="pi_test_123",
            amount=1000,
            currency=Currency.USD,
            status=PaymentIntentStatus.SUCCEEDED,
        )
        
        pi.link_to_escrow("escrow_456")
        
        self.assertEqual(pi.escrow_id, "escrow_456")
    
    def test_set_escrow_hold(self):
        """Test setting escrow hold"""
        pi = PaymentIntentData(
            id="pi_test_123",
            amount=1000,
            currency=Currency.USD,
        )
        
        pi.set_escrow_hold(True)
        
        self.assertTrue(pi.escrow_hold)
        self.assertEqual(pi.capture_method, "manual")
    
    def test_is_escrow(self):
        """Test checking if escrow"""
        pi = PaymentIntentData(
            id="pi_test_123",
            amount=1000,
            currency=Currency.USD,
        )
        
        self.assertFalse(pi.is_escrow())
        
        pi.set_escrow_hold(True)
        self.assertTrue(pi.is_escrow())
    
    def test_is_successful(self):
        """Test checking if successful"""
        pi = PaymentIntentData(
            id="pi_test_123",
            amount=1000,
            currency=Currency.USD,
            status=PaymentIntentStatus.SUCCEEDED,
        )
        
        self.assertTrue(pi.is_successful())
        
        pi.status = PaymentIntentStatus.REQUIRES_PAYMENT_METHOD
        self.assertFalse(pi.is_successful())


class TestTransactionModeler(unittest.TestCase):
    """Tests for TransactionModeler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.modeler = TransactionModeler()
    
    def test_create_stripe_transaction(self):
        """Test creating a Stripe transaction"""
        tx = self.modeler.create_stripe_transaction(
            amount=1000,
            currency="usd",
            escrow_id="escrow_123",
        )
        
        self.assertIsInstance(tx, StripeTransaction)
        self.assertEqual(tx.escrow_id, "escrow_123")
        self.assertIn(tx.id, self.modeler.transactions)
    
    def test_create_escrow_transaction(self):
        """Test creating an escrow transaction"""
        tx = self.modeler.create_escrow_transaction(
            amount=5000,
            currency="usd",
            escrow_id="escrow_456",
        )
        
        self.assertIsInstance(tx, EscrowTransaction)
        self.assertEqual(tx.escrow_id, "escrow_456")
        self.assertIn(tx.escrow_id, self.modeler.transactions)
    
    def test_link_transactions(self):
        """Test linking transactions"""
        stripe_tx = self.modeler.create_stripe_transaction(
            amount=1000,
            currency="usd",
        )
        escrow_tx = self.modeler.create_escrow_transaction(
            amount=1000,
            currency="usd",
            escrow_id="escrow_789",
        )
        
        success = self.modeler.link_transactions(stripe_tx.id, escrow_tx.escrow_id)
        
        self.assertTrue(success)
        self.assertEqual(stripe_tx.escrow_id, escrow_tx.escrow_id)
    
    def test_get_linked_transactions(self):
        """Test getting linked transactions"""
        stripe_tx = self.modeler.create_stripe_transaction(
            amount=1000,
            currency="usd",
            escrow_id="escrow_123",
        )
        
        linked = self.modeler.get_linked_transactions("escrow_123")
        
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0].id, stripe_tx.id)
    
    def test_get_escrow_by_stripe(self):
        """Test getting escrow by Stripe ID"""
        stripe_tx = self.modeler.create_stripe_transaction(
            amount=1000,
            currency="usd",
            escrow_id="escrow_456",
        )
        
        escrow = self.modeler.get_escrow_by_stripe(stripe_tx.id)
        
        self.assertIsNotNone(escrow)
        self.assertEqual(escrow.escrow_id, "escrow_456")
    
    def test_sync_status(self):
        """Test syncing status"""
        stripe_tx = self.modeler.create_stripe_transaction(
            amount=1000,
            currency="usd",
            escrow_id="escrow_789",
        )
        
        success = self.modeler.sync_status(
            stripe_tx.id,
            TransactionStatus.SUCCEEDED,
        )
        
        self.assertTrue(success)
        self.assertEqual(stripe_tx.escrow_status, TransactionStatus.SUCCEEDED)
    
    def test_validate_transaction(self):
        """Test validating a transaction"""
        tx = StripeTransaction(
            id="pi_test_123",
            amount=1000,
            currency=Currency.USD,
        )
        
        result = self.modeler.validate_transaction(tx)
        
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["errors"]), 0)
    
    def test_get_all_transactions(self):
        """Test getting all transactions"""
        self.modeler.create_stripe_transaction(amount=1000, currency="usd")
        self.modeler.create_escrow_transaction(amount=5000, currency="usd")
        
        all_tx = self.modeler.get_all_transactions()
        
        self.assertEqual(len(all_tx), 2)
    
    def test_clear(self):
        """Test clearing all transactions"""
        self.modeler.create_stripe_transaction(amount=1000, currency="usd")
        self.modeler.clear()
        
        self.assertEqual(len(self.modeler.get_all_transactions()), 0)


class TestPaymentIntentModel(unittest.TestCase):
    """Tests for PaymentIntentModel"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.model = PaymentIntentModel()
    
    def test_create(self):
        """Test creating a PaymentIntent"""
        pi = self.model.create(
            amount=1000,
            currency="usd",
            escrow_id="escrow_123",
            escrow_hold=True,
        )
        
        self.assertIsInstance(pi, PaymentIntentData)
        self.assertEqual(pi.escrow_id, "escrow_123")
        self.assertTrue(pi.escrow_hold)
    
    def test_retrieve(self):
        """Test retrieving a PaymentIntent"""
        pi = self.model.create(amount=1000, currency="usd")
        retrieved = self.model.retrieve(pi.id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, pi.id)
    
    def test_confirm(self):
        """Test confirming a PaymentIntent"""
        pi = self.model.create(amount=1000, currency="usd")
        confirmed = self.model.confirm(pi.id, payment_method="pm_456")
        
        self.assertIsNotNone(confirmed)
        self.assertEqual(confirmed.status, PaymentIntentStatus.SUCCEEDED)
    
    def test_cancel(self):
        """Test canceling a PaymentIntent"""
        pi = self.model.create(amount=1000, currency="usd")
        canceled = self.model.cancel(pi.id)
        
        self.assertIsNotNone(canceled)
        self.assertEqual(canceled.status, PaymentIntentStatus.CANCELED)
    
    def test_link_to_escrow(self):
        """Test linking to escrow"""
        pi = self.model.create(amount=1000, currency="usd")
        success = self.model.link_to_escrow(pi.id, "escrow_456")
        
        self.assertTrue(success)
        self.assertEqual(pi.escrow_id, "escrow_456")
    
    def test_get_by_escrow(self):
        """Test getting by escrow"""
        pi = self.model.create(amount=1000, currency="usd", escrow_id="escrow_123")
        
        pis = self.model.get_by_escrow("escrow_123")
        
        self.assertEqual(len(pis), 1)
        self.assertEqual(pis[0].id, pi.id)
    
    def test_list_all(self):
        """Test listing all PaymentIntents"""
        self.model.create(amount=1000, currency="usd")
        self.model.create(amount=2000, currency="usd")
        
        pis = self.model.list_all()
        
        self.assertEqual(len(pis), 2)
    
    def test_get_stats(self):
        """Test getting statistics"""
        self.model.create(amount=1000, currency="usd", escrow_id="escrow_1")
        self.model.create(amount=2000, currency="usd", escrow_id="escrow_2")
        
        stats = self.model.get_stats()
        
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["escrow"], 2)


if __name__ == "__main__":
    unittest.main()
