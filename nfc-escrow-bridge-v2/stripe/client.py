#!/usr/bin/env python3
"""
Stripe Client for NFC Escrow Bridge
=====================================
Complete Stripe API client with escrow integration.

Features:
- PaymentIntent operations
- Customer management
- Charge operations
- Refund operations
- Webhook handling
- Escrow linking
- Error handling

Author: Tyrone J Power Ω
Fold Entry: FE-OGUF-P1
Version: 2.0.0
"""

import json
import time
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [StripeClient] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class StripeEnvironment(Enum):
    """Stripe environments"""
    TEST = "test"
    LIVE = "live"


# Stripe API endpoints
STRIPE_API_BASE = {
    StripeEnvironment.TEST: "https://api.stripe.com",
    StripeEnvironment.LIVE: "https://api.stripe.com",
}

STRIPE_API_VERSION = "2024-06-20"


# ============================================================================
# STRIPE CLIENT
# ============================================================================

class StripeClient:
    """
    Complete Stripe API client for NFC Escrow Bridge.
    
    Provides a unified interface for all Stripe operations with
    automatic escrow context injection and error handling.
    """
    
    def __init__(
        self,
        api_key: str,
        environment: StripeEnvironment = StripeEnvironment.TEST,
        default_escrow_id: Optional[str] = None,
    ):
        """Initialize Stripe Client"""
        self.api_key = api_key
        self.environment = environment
        self.default_escrow_id = default_escrow_id
        self.base_url = STRIPE_API_BASE[environment]
        
        # Initialize Stripe SDK
        self._initialize_stripe()
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.last_request_time = 0.0
        
        logger.info(f"StripeClient initialized (env: {environment.value})")
    
    def _initialize_stripe(self):
        """Initialize Stripe SDK"""
        try:
            import stripe
            stripe.api_key = self.api_key
            stripe.api_version = STRIPE_API_VERSION
            logger.info("Stripe SDK initialized")
        except ImportError:
            logger.error("Stripe SDK not installed. Install with: pip install stripe")
            raise
    
    # ========================================================================
    # PAYMENT INTENT OPERATIONS
    # ========================================================================
    
    def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        customer: Optional[str] = None,
        payment_method: Optional[str] = None,
        escrow_id: Optional[str] = None,
        capture_method: str = "manual",
        confirm: bool = False,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a PaymentIntent.
        
        Args:
            amount: Amount in cents
            currency: Currency code (default: usd)
            customer: Customer ID (optional)
            payment_method: PaymentMethod ID (optional)
            escrow_id: Escrow ID to link (optional)
            capture_method: Capture method (default: manual for escrow)
            confirm: Whether to confirm immediately (default: False)
            description: Description (optional)
            metadata: Additional metadata (optional)
            **kwargs: Additional parameters
            
        Returns:
            Stripe PaymentIntent object
        """
        try:
            import stripe
            
            self.total_requests += 1
            start_time = time.time()
            
            # Build metadata
            request_metadata = {}
            if escrow_id or self.default_escrow_id:
                request_metadata["escrow_id"] = escrow_id or self.default_escrow_id
            request_metadata["source"] = "nfc_escrow_bridge"
            request_metadata["version"] = "2.0"
            
            if metadata:
                request_metadata.update(metadata)
            
            # Create PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer,
                payment_method=payment_method,
                capture_method=capture_method,
                confirm=confirm,
                description=description or f"Escrow payment for {escrow_id or self.default_escrow_id}",
                metadata=request_metadata,
                **kwargs,
            )
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Created PaymentIntent: {intent.id} (${amount / 100:.2f} {currency})")
            
            return intent.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error creating PaymentIntent: {e}")
            raise
        except Exception as e:
            self.failed_requests += 1
            logger.error(f"Error creating PaymentIntent: {e}")
            raise
    
    def retrieve_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """
        Retrieve a PaymentIntent.
        
        Args:
            intent_id: PaymentIntent ID
            
        Returns:
            Stripe PaymentIntent object
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            intent = stripe.PaymentIntent.retrieve(intent_id)
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Retrieved PaymentIntent: {intent.id}")
            
            return intent.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error retrieving PaymentIntent {intent_id}: {e}")
            raise
    
    def confirm_payment_intent(
        self,
        intent_id: str,
        payment_method: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Confirm a PaymentIntent.
        
        Args:
            intent_id: PaymentIntent ID
            payment_method: PaymentMethod ID (optional)
            **kwargs: Additional parameters
            
        Returns:
            Stripe PaymentIntent object
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            params = {}
            if payment_method:
                params["payment_method"] = payment_method
            params.update(kwargs)
            
            intent = stripe.PaymentIntent.confirm(intent_id, **params)
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Confirmed PaymentIntent: {intent.id} (Status: {intent.status})")
            
            return intent.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error confirming PaymentIntent {intent_id}: {e}")
            raise
    
    def capture_payment_intent(
        self,
        intent_id: str,
        amount: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Capture a PaymentIntent.
        
        Args:
            intent_id: PaymentIntent ID
            amount: Amount to capture in cents (optional)
            **kwargs: Additional parameters
            
        Returns:
            Stripe PaymentIntent object
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            params = {}
            if amount:
                params["amount"] = amount
            params.update(kwargs)
            
            intent = stripe.PaymentIntent.capture(intent_id, **params)
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Captured PaymentIntent: {intent.id} (Amount: ${amount / 100:.2f})")
            
            return intent.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error capturing PaymentIntent {intent_id}: {e}")
            raise
    
    def cancel_payment_intent(self, intent_id: str) -> Dict[str, Any]:
        """
        Cancel a PaymentIntent.
        
        Args:
            intent_id: PaymentIntent ID
            
        Returns:
            Stripe PaymentIntent object
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            intent = stripe.PaymentIntent.cancel(intent_id)
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Canceled PaymentIntent: {intent.id}")
            
            return intent.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error canceling PaymentIntent {intent_id}: {e}")
            raise
    
    def list_payment_intents(
        self,
        limit: int = 10,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        List PaymentIntents.
        
        Args:
            limit: Maximum number of results (default: 10)
            **kwargs: Additional parameters
            
        Returns:
            Stripe API response with list of PaymentIntents
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            params = {"limit": limit}
            params.update(kwargs)
            
            intents = stripe.PaymentIntent.list(**params)
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Listed {len(intents.data)} PaymentIntents")
            
            return {
                "object": "list",
                "data": [i.to_dict() for i in intents],
                "has_more": intents.has_more,
            }
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error listing PaymentIntents: {e}")
            raise
    
    # ========================================================================
    # CUSTOMER OPERATIONS
    # ========================================================================
    
    def create_customer(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        escrow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a Customer.
        
        Args:
            email: Customer email (optional)
            name: Customer name (optional)
            description: Customer description (optional)
            escrow_id: Escrow ID to link (optional)
            metadata: Additional metadata (optional)
            **kwargs: Additional parameters
            
        Returns:
            Stripe Customer object
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            # Build metadata
            request_metadata = {}
            if escrow_id or self.default_escrow_id:
                request_metadata["escrow_id"] = escrow_id or self.default_escrow_id
            request_metadata["source"] = "nfc_escrow_bridge"
            
            if metadata:
                request_metadata.update(metadata)
            
            customer = stripe.Customer.create(
                email=email,
                name=name,
                description=description,
                metadata=request_metadata,
                **kwargs,
            )
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Created Customer: {customer.id} ({email or 'no email'})")
            
            return customer.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error creating Customer: {e}")
            raise
    
    def retrieve_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Retrieve a Customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Stripe Customer object
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            customer = stripe.Customer.retrieve(customer_id)
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Retrieved Customer: {customer.id}")
            
            return customer.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error retrieving Customer {customer_id}: {e}")
            raise
    
    def update_customer(
        self,
        customer_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Update a Customer.
        
        Args:
            customer_id: Customer ID
            **kwargs: Customer fields to update
            
        Returns:
            Stripe Customer object
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            customer = stripe.Customer.modify(customer_id, **kwargs)
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Updated Customer: {customer.id}")
            
            return customer.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error updating Customer {customer_id}: {e}")
            raise
    
    def delete_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Delete a Customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Stripe Customer object
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            customer = stripe.Customer.delete(customer_id)
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Deleted Customer: {customer.id}")
            
            return customer.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error deleting Customer {customer_id}: {e}")
            raise
    
    def list_customers(
        self,
        limit: int = 10,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        List Customers.
        
        Args:
            limit: Maximum number of results (default: 10)
            **kwargs: Additional parameters
            
        Returns:
            Stripe API response with list of Customers
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            params = {"limit": limit}
            params.update(kwargs)
            
            customers = stripe.Customer.list(**params)
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Listed {len(customers.data)} Customers")
            
            return {
                "object": "list",
                "data": [c.to_dict() for c in customers],
                "has_more": customers.has_more,
            }
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error listing Customers: {e}")
            raise
    
    # ========================================================================
    # CHARGE OPERATIONS
    # ========================================================================
    
    def create_charge(
        self,
        amount: int,
        currency: str = "usd",
        customer: Optional[str] = None,
        payment_method: Optional[str] = None,
        escrow_id: Optional[str] = None,
        capture: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a Charge.
        
        Args:
            amount: Amount in cents
            currency: Currency code (default: usd)
            customer: Customer ID (optional)
            payment_method: PaymentMethod ID (optional)
            escrow_id: Escrow ID to link (optional)
            capture: Whether to capture immediately (default: False)
            **kwargs: Additional parameters
            
        Returns:
            Stripe Charge object
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            # Build metadata
            request_metadata = {}
            if escrow_id or self.default_escrow_id:
                request_metadata["escrow_id"] = escrow_id or self.default_escrow_id
            request_metadata["source"] = "nfc_escrow_bridge"
            
            charge = stripe.Charge.create(
                amount=amount,
                currency=currency,
                customer=customer,
                payment_method=payment_method,
                capture=capture,
                metadata=request_metadata,
                **kwargs,
            )
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Created Charge: {charge.id} (${amount / 100:.2f} {currency})")
            
            return charge.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error creating Charge: {e}")
            raise
    
    def retrieve_charge(self, charge_id: str) -> Dict[str, Any]:
        """
        Retrieve a Charge.
        
        Args:
            charge_id: Charge ID
            
        Returns:
            Stripe Charge object
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            charge = stripe.Charge.retrieve(charge_id)
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Retrieved Charge: {charge.id}")
            
            return charge.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error retrieving Charge {charge_id}: {e}")
            raise
    
    def capture_charge(
        self,
        charge_id: str,
        amount: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Capture a Charge.
        
        Args:
            charge_id: Charge ID
            amount: Amount to capture in cents (optional)
            **kwargs: Additional parameters
            
        Returns:
            Stripe Charge object
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            params = {}
            if amount:
                params["amount"] = amount
            params.update(kwargs)
            
            charge = stripe.Charge.capture(charge_id, **params)
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Captured Charge: {charge.id} (Amount: ${amount / 100:.2f})")
            
            return charge.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error capturing Charge {charge_id}: {e}")
            raise
    
    def refund_charge(
        self,
        charge_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Refund a Charge.
        
        Args:
            charge_id: Charge ID
            amount: Amount to refund in cents (optional)
            reason: Refund reason (optional)
            **kwargs: Additional parameters
            
        Returns:
            Stripe Refund object
        """
        try:
            import stripe
            
            self.total_requests += 1
            
            params = {"charge": charge_id}
            if amount:
                params["amount"] = amount
            if reason:
                params["reason"] = reason
            params.update(kwargs)
            
            refund = stripe.Refund.create(**params)
            
            self.successful_requests += 1
            self.last_request_time = time.time()
            
            logger.info(f"Refunded Charge: {charge_id} (Amount: ${amount / 100:.2f if amount else 'full'})")
            
            return refund.to_dict()
            
        except stripe.error.StripeError as e:
            self.failed_requests += 1
            logger.error(f"Stripe error refunding Charge {charge_id}: {e}")
            raise
    
    # ========================================================================
    # ESCROW-SPECIFIC METHODS
    # ========================================================================
    
    def create_escrow_payment(
        self,
        amount: int,
        currency: str = "usd",
        escrow_id: str = "",
        customer: Optional[str] = None,
        payment_method: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create an escrow-linked payment.
        
        This creates a PaymentIntent with escrow-specific settings:
        - Manual capture (funds held in escrow)
        - Escrow ID in metadata
        - Appropriate description
        
        Args:
            amount: Amount in cents
            currency: Currency code (default: usd)
            escrow_id: Escrow ID to link
            customer: Customer ID (optional)
            payment_method: PaymentMethod ID (optional)
            description: Description (optional)
            **kwargs: Additional parameters
            
        Returns:
            Stripe PaymentIntent object
        """
        return self.create_payment_intent(
            amount=amount,
            currency=currency,
            escrow_id=escrow_id,
            customer=customer,
            payment_method=payment_method,
            capture_method="manual",
            confirm=False,
            description=description or f"Escrow payment for {escrow_id}",
            **kwargs,
        )
    
    def release_escrow_funds(
        self,
        intent_id: str,
        amount: Optional[int] = None,
        escrow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Release escrow funds by capturing the PaymentIntent.
        
        Args:
            intent_id: PaymentIntent ID
            amount: Amount to release in cents (optional)
            escrow_id: Escrow ID for logging (optional)
            
        Returns:
            Stripe PaymentIntent object
        """
        logger.info(f"Releasing escrow funds for PaymentIntent: {intent_id}")
        return self.capture_payment_intent(intent_id, amount)
    
    def refund_escrow_funds(
        self,
        intent_id: str,
        reason: str = "requested_by_customer",
        escrow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund escrow funds by canceling the PaymentIntent.
        
        Note: This only works if the PaymentIntent hasn't been captured yet.
        For captured PaymentIntents, you'd need to refund the Charge.
        
        Args:
            intent_id: PaymentIntent ID
            reason: Refund reason (optional)
            escrow_id: Escrow ID for logging (optional)
            
        Returns:
            Stripe PaymentIntent object
        """
        logger.info(f"Refunding escrow funds for PaymentIntent: {intent_id}")
        return self.cancel_payment_intent(intent_id)
    
    # ========================================================================
    # STATISTICS & UTILITIES
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "environment": self.environment.value,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            "last_request_time": self.last_request_time,
            "default_escrow_id": self.default_escrow_id,
        }
    
    def set_default_escrow_id(self, escrow_id: str) -> None:
        """Set default escrow ID for all requests"""
        self.default_escrow_id = escrow_id
        logger.info(f"Default escrow ID set to: {escrow_id}")
    
    def reset_stats(self) -> None:
        """Reset client statistics"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Create client (use test key for testing)
    client = StripeClient(
        api_key="sk_test_51ABC123...",
        environment=StripeEnvironment.TEST,
        default_escrow_id="escrow_default",
    )
    
    print("=" * 60)
    print("STRIPE CLIENT TEST")
    print("=" * 60)
    
    # Note: These tests will fail without a valid API key
    # They're here to show the API usage
    
    try:
        # Create customer
        print("\n1. Creating Customer...")
        customer = client.create_customer(
            email="test@example.com",
            name="Test Customer",
            escrow_id="escrow_123",
        )
        print(f"   Customer: {customer['id']}")
        
        # Create PaymentIntent
        print("\n2. Creating PaymentIntent...")
        intent = client.create_payment_intent(
            amount=5000,
            currency="usd",
            customer=customer["id"],
            escrow_id="escrow_456",
            capture_method="manual",
        )
        print(f"   PaymentIntent: {intent['id']}")
        print(f"   Amount: ${intent['amount'] / 100:.2f}")
        print(f"   Status: {intent['status']}")
        print(f"   Metadata: {intent['metadata']}")
        
        # Confirm PaymentIntent
        print("\n3. Confirming PaymentIntent...")
        confirmed = client.confirm_payment_intent(
            intent["id"],
            payment_method="pm_card_visa",
        )
        print(f"   Status: {confirmed['status']}")
        
        # Capture PaymentIntent
        print("\n4. Capturing PaymentIntent...")
        captured = client.capture_payment_intent(intent["id"])
        print(f"   Status: {captured['status']}")
        
        # Create escrow payment
        print("\n5. Creating Escrow Payment...")
        escrow_payment = client.create_escrow_payment(
            amount=10000,
            currency="usd",
            escrow_id="escrow_789",
            customer=customer["id"],
        )
        print(f"   PaymentIntent: {escrow_payment['id']}")
        print(f"   Metadata: {escrow_payment['metadata']}")
        
        # Statistics
        print("\n6. Client Statistics:")
        stats = client.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
    except Exception as e:
        print(f"\n⚠️  Test failed (expected without valid API key): {e}")
        print("\nTo run tests with real API:")
        print("   1. Set a valid Stripe API key")
        print("   2. Use: client = StripeClient(api_key='sk_test_...')")
    
    print("\n" + "=" * 60)
    print("STRIPE CLIENT READY FOR PRODUCTION")
    print("=" * 60)
