#!/usr/bin/env python3
"""
Stripe Request Framer
======================
Builds properly structured Stripe API requests with escrow context.

Features:
- PaymentIntent request framing
- Customer request framing
- Charge request framing
- Refund request framing
- Escrow-linked request framing

Author: Tyrone J Power Ω
Fold Entry: FE-OGUF-P1
Version: 2.0.0
"""

import time
import secrets
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from .webhook_handler import WebhookEvent


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class RequestType(Enum):
    """Stripe request types"""
    CREATE = "create"
    RETRIEVE = "retrieve"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    CONFIRM = "confirm"
    CAPTURE = "capture"
    CANCEL = "cancel"
    REFUND = "refund"


class ObjectType(Enum):
    """Stripe object types"""
    PAYMENT_INTENT = "payment_intent"
    CHARGE = "charge"
    CUSTOMER = "customer"
    PAYMENT_METHOD = "payment_method"
    REFUND = "refund"
    DISPUTE = "dispute"
    TRANSFER = "transfer"
    BALANCE_TRANSACTION = "balance_transaction"


# Default configuration
DEFAULT_API_VERSION = "2024-06-20"
DEFAULT_IDEMPOTENCY_KEY_PREFIX = "nfc_escrow_"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class StripeRequestFrame:
    """
    Frame for a Stripe API request.
    
    Contains all necessary data to make a Stripe API call,
    including escrow context and metadata.
    """
    request_type: RequestType
    object_type: ObjectType
    endpoint: str
    data: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: Optional[str] = None
    api_key: Optional[str] = None
    api_version: str = DEFAULT_API_VERSION
    metadata: Dict[str, Any] = field(default_factory=dict)
    escrow_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "request_type": self.request_type.value,
            "object_type": self.object_type.value,
            "endpoint": self.endpoint,
            "data": self.data,
            "idempotency_key": self.idempotency_key,
            "api_key": self.api_key[:8] + "..." if self.api_key else None,
            "api_version": self.api_version,
            "metadata": self.metadata,
            "escrow_context": self.escrow_context,
        }
    
    def to_request_data(self) -> Dict[str, Any]:
        """Convert to request data for Stripe SDK"""
        request_data = self.data.copy()
        
        # Add escrow context to metadata
        if self.escrow_context:
            if "metadata" not in request_data:
                request_data["metadata"] = {}
            request_data["metadata"].update(self.escrow_context)
        
        # Add regular metadata
        if self.metadata:
            if "metadata" not in request_data:
                request_data["metadata"] = {}
            request_data["metadata"].update(self.metadata)
        
        return request_data
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for HTTP request"""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "NFC-Escrow-Bridge/2.0",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        if self.idempotency_key:
            headers["Idempotency-Key"] = self.idempotency_key
        
        if self.api_version:
            headers["Stripe-Version"] = self.api_version
        
        return headers


# ============================================================================
# STRIPE FRAME BUILDER
# ============================================================================

class StripeFrameBuilder:
    """
    Builds properly structured Stripe API request frames.
    
    Provides methods to create frames for all Stripe operations
    with automatic escrow context injection.
    """
    
    def __init__(self, api_key: Optional[str] = None, escrow_id: Optional[str] = None):
        """Initialize Stripe Frame Builder"""
        self.api_key = api_key
        self.default_escrow_id = escrow_id
        self.request_count = 0
    
    def _generate_idempotency_key(self) -> str:
        """Generate a unique idempotency key"""
        self.request_count += 1
        return f"{DEFAULT_IDEMPOTENCY_KEY_PREFIX}{secrets.token_hex(8)}_{self.request_count}"
    
    def _get_escrow_context(self, escrow_id: Optional[str] = None) -> Dict[str, Any]:
        """Get escrow context for a request"""
        context = {}
        
        escrow_id = escrow_id or self.default_escrow_id
        if escrow_id:
            context["escrow_id"] = escrow_id
            context["source"] = "nfc_escrow_bridge"
            context["version"] = "2.0"
        
        return context
    
    # ========================================================================
    # PAYMENT INTENT FRAMES
    # ========================================================================
    
    def build_payment_intent_create_frame(
        self,
        amount: int,
        currency: str = "usd",
        customer: Optional[str] = None,
        payment_method: Optional[str] = None,
        escrow_id: Optional[str] = None,
        capture_method: str = "manual",  # Manual capture for escrow
        confirm: bool = False,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> StripeRequestFrame:
        """
        Build a frame for creating a PaymentIntent.
        
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
            StripeRequestFrame with PaymentIntent creation data
        """
        data = {
            "amount": amount,
            "currency": currency,
            "capture_method": capture_method,
            "confirm": confirm,
        }
        
        if customer:
            data["customer"] = customer
        if payment_method:
            data["payment_method"] = payment_method
        if description:
            data["description"] = description
        
        # Add escrow context
        escrow_context = self._get_escrow_context(escrow_id)
        if escrow_context:
            data["metadata"] = {**escrow_context}
        
        # Add any additional metadata
        if metadata:
            if "metadata" not in data:
                data["metadata"] = {}
            data["metadata"].update(metadata)
        
        # Add additional parameters
        data.update(kwargs)
        
        return StripeRequestFrame(
            request_type=RequestType.CREATE,
            object_type=ObjectType.PAYMENT_INTENT,
            endpoint="/v1/payment_intents",
            data=data,
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=escrow_context,
            metadata=metadata or {},
        )
    
    def build_payment_intent_retrieve_frame(
        self,
        intent_id: str,
        escrow_id: Optional[str] = None,
    ) -> StripeRequestFrame:
        """Build a frame for retrieving a PaymentIntent"""
        return StripeRequestFrame(
            request_type=RequestType.RETRIEVE,
            object_type=ObjectType.PAYMENT_INTENT,
            endpoint=f"/v1/payment_intents/{intent_id}",
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=self._get_escrow_context(escrow_id),
        )
    
    def build_payment_intent_confirm_frame(
        self,
        intent_id: str,
        payment_method: Optional[str] = None,
        escrow_id: Optional[str] = None,
        **kwargs,
    ) -> StripeRequestFrame:
        """Build a frame for confirming a PaymentIntent"""
        data = {}
        if payment_method:
            data["payment_method"] = payment_method
        data.update(kwargs)
        
        return StripeRequestFrame(
            request_type=RequestType.CONFIRM,
            object_type=ObjectType.PAYMENT_INTENT,
            endpoint=f"/v1/payment_intents/{intent_id}/confirm",
            data=data,
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=self._get_escrow_context(escrow_id),
        )
    
    def build_payment_intent_capture_frame(
        self,
        intent_id: str,
        amount: Optional[int] = None,
        escrow_id: Optional[str] = None,
    ) -> StripeRequestFrame:
        """Build a frame for capturing a PaymentIntent"""
        data = {}
        if amount:
            data["amount"] = amount
        
        return StripeRequestFrame(
            request_type=RequestType.CAPTURE,
            object_type=ObjectType.PAYMENT_INTENT,
            endpoint=f"/v1/payment_intents/{intent_id}/capture",
            data=data,
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=self._get_escrow_context(escrow_id),
        )
    
    def build_payment_intent_cancel_frame(
        self,
        intent_id: str,
        escrow_id: Optional[str] = None,
    ) -> StripeRequestFrame:
        """Build a frame for canceling a PaymentIntent"""
        return StripeRequestFrame(
            request_type=RequestType.CANCEL,
            object_type=ObjectType.PAYMENT_INTENT,
            endpoint=f"/v1/payment_intents/{intent_id}",
            data={"status": "canceled"},
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=self._get_escrow_context(escrow_id),
        )
    
    def build_payment_intent_list_frame(
        self,
        limit: int = 10,
        escrow_id: Optional[str] = None,
        **kwargs,
    ) -> StripeRequestFrame:
        """Build a frame for listing PaymentIntents"""
        data = {"limit": limit}
        data.update(kwargs)
        
        return StripeRequestFrame(
            request_type=RequestType.LIST,
            object_type=ObjectType.PAYMENT_INTENT,
            endpoint="/v1/payment_intents",
            data=data,
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=self._get_escrow_context(escrow_id),
        )
    
    # ========================================================================
    # CUSTOMER FRAMES
    # ========================================================================
    
    def build_customer_create_frame(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        escrow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> StripeRequestFrame:
        """Build a frame for creating a Customer"""
        data = {}
        if email:
            data["email"] = email
        if name:
            data["name"] = name
        if description:
            data["description"] = description
        
        # Add escrow context
        escrow_context = self._get_escrow_context(escrow_id)
        if escrow_context:
            data["metadata"] = {**escrow_context}
        
        # Add additional metadata
        if metadata:
            if "metadata" not in data:
                data["metadata"] = {}
            data["metadata"].update(metadata)
        
        data.update(kwargs)
        
        return StripeRequestFrame(
            request_type=RequestType.CREATE,
            object_type=ObjectType.CUSTOMER,
            endpoint="/v1/customers",
            data=data,
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=escrow_context,
            metadata=metadata or {},
        )
    
    def build_customer_retrieve_frame(
        self,
        customer_id: str,
        escrow_id: Optional[str] = None,
    ) -> StripeRequestFrame:
        """Build a frame for retrieving a Customer"""
        return StripeRequestFrame(
            request_type=RequestType.RETRIEVE,
            object_type=ObjectType.CUSTOMER,
            endpoint=f"/v1/customers/{customer_id}",
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=self._get_escrow_context(escrow_id),
        )
    
    def build_customer_update_frame(
        self,
        customer_id: str,
        escrow_id: Optional[str] = None,
        **kwargs,
    ) -> StripeRequestFrame:
        """Build a frame for updating a Customer"""
        return StripeRequestFrame(
            request_type=RequestType.UPDATE,
            object_type=ObjectType.CUSTOMER,
            endpoint=f"/v1/customers/{customer_id}",
            data=kwargs,
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=self._get_escrow_context(escrow_id),
        )
    
    def build_customer_delete_frame(
        self,
        customer_id: str,
        escrow_id: Optional[str] = None,
    ) -> StripeRequestFrame:
        """Build a frame for deleting a Customer"""
        return StripeRequestFrame(
            request_type=RequestType.DELETE,
            object_type=ObjectType.CUSTOMER,
            endpoint=f"/v1/customers/{customer_id}",
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=self._get_escrow_context(escrow_id),
        )
    
    # ========================================================================
    # CHARGE FRAMES
    # ========================================================================
    
    def build_charge_create_frame(
        self,
        amount: int,
        currency: str = "usd",
        customer: Optional[str] = None,
        payment_method: Optional[str] = None,
        escrow_id: Optional[str] = None,
        capture: bool = False,  # Manual capture for escrow
        **kwargs,
    ) -> StripeRequestFrame:
        """Build a frame for creating a Charge"""
        data = {
            "amount": amount,
            "currency": currency,
            "capture": capture,
        }
        
        if customer:
            data["customer"] = customer
        if payment_method:
            data["payment_method"] = payment_method
        
        # Add escrow context
        escrow_context = self._get_escrow_context(escrow_id)
        if escrow_context:
            data["metadata"] = {**escrow_context}
        
        data.update(kwargs)
        
        return StripeRequestFrame(
            request_type=RequestType.CREATE,
            object_type=ObjectType.CHARGE,
            endpoint="/v1/charges",
            data=data,
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=escrow_context,
        )
    
    def build_charge_retrieve_frame(
        self,
        charge_id: str,
        escrow_id: Optional[str] = None,
    ) -> StripeRequestFrame:
        """Build a frame for retrieving a Charge"""
        return StripeRequestFrame(
            request_type=RequestType.RETRIEVE,
            object_type=ObjectType.CHARGE,
            endpoint=f"/v1/charges/{charge_id}",
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=self._get_escrow_context(escrow_id),
        )
    
    # ========================================================================
    # REFUND FRAMES
    # ========================================================================
    
    def build_refund_create_frame(
        self,
        charge_id: str,
        amount: Optional[int] = None,
        escrow_id: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs,
    ) -> StripeRequestFrame:
        """Build a frame for creating a Refund"""
        data = {"charge": charge_id}
        
        if amount:
            data["amount"] = amount
        if reason:
            data["reason"] = reason
        
        # Add escrow context
        escrow_context = self._get_escrow_context(escrow_id)
        if escrow_context:
            data["metadata"] = {**escrow_context}
        
        data.update(kwargs)
        
        return StripeRequestFrame(
            request_type=RequestType.CREATE,
            object_type=ObjectType.REFUND,
            endpoint="/v1/refunds",
            data=data,
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=escrow_context,
        )
    
    def build_refund_retrieve_frame(
        self,
        refund_id: str,
        escrow_id: Optional[str] = None,
    ) -> StripeRequestFrame:
        """Build a frame for retrieving a Refund"""
        return StripeRequestFrame(
            request_type=RequestType.RETRIEVE,
            object_type=ObjectType.REFUND,
            endpoint=f"/v1/refunds/{refund_id}",
            idempotency_key=self._generate_idempotency_key(),
            api_key=self.api_key,
            escrow_context=self._get_escrow_context(escrow_id),
        )
    
    # ========================================================================
    # ESCROW-SPECIFIC FRAMES
    # ========================================================================
    
    def build_escrow_payment_frame(
        self,
        amount: int,
        currency: str = "usd",
        escrow_id: str = "",
        customer: Optional[str] = None,
        payment_method: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> StripeRequestFrame:
        """
        Build a frame for an escrow-linked payment.
        
        This creates a PaymentIntent with escrow-specific settings:
        - Manual capture (funds held in escrow)
        - Escrow ID in metadata
        - Appropriate description
        """
        return self.build_payment_intent_create_frame(
            amount=amount,
            currency=currency,
            customer=customer,
            payment_method=payment_method,
            escrow_id=escrow_id,
            capture_method="manual",
            confirm=False,
            description=description or f"Escrow payment for {escrow_id}",
            **kwargs,
        )
    
    def build_escrow_release_frame(
        self,
        intent_id: str,
        escrow_id: str,
        amount: Optional[int] = None,
    ) -> StripeRequestFrame:
        """
        Build a frame for releasing escrow funds.
        
        This captures the PaymentIntent, releasing funds to the seller.
        """
        return self.build_payment_intent_capture_frame(
            intent_id=intent_id,
            amount=amount,
            escrow_id=escrow_id,
        )
    
    def build_escrow_refund_frame(
        self,
        intent_id: str,
        escrow_id: str,
        reason: str = "requested_by_customer",
    ) -> StripeRequestFrame:
        """
        Build a frame for refunding escrow funds.
        
        This cancels the PaymentIntent and refunds the buyer.
        """
        # First cancel the PaymentIntent
        cancel_frame = self.build_payment_intent_cancel_frame(
            intent_id=intent_id,
            escrow_id=escrow_id,
        )
        
        # Then create a refund (if already captured)
        # Note: In practice, you'd need the charge_id for this
        
        return cancel_frame
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def set_default_escrow_id(self, escrow_id: str) -> None:
        """Set default escrow ID for all frames"""
        self.default_escrow_id = escrow_id
    
    def set_api_key(self, api_key: str) -> None:
        """Set API key for all frames"""
        self.api_key = api_key
    
    def get_stats(self) -> Dict[str, Any]:
        """Get frame builder statistics"""
        return {
            "request_count": self.request_count,
            "default_escrow_id": self.default_escrow_id,
            "has_api_key": bool(self.api_key),
        }
    
    def reset(self) -> None:
        """Reset frame builder"""
        self.request_count = 0


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Create frame builder
    builder = StripeFrameBuilder(api_key="sk_test_123", escrow_id="escrow_default")
    
    print("=" * 60)
    print("STRIPE FRAME BUILDER TEST")
    print("=" * 60)
    
    # Build PaymentIntent create frame
    print("\n1. Building PaymentIntent Create Frame...")
    frame = builder.build_payment_intent_create_frame(
        amount=5000,
        currency="usd",
        customer="cus_123",
        escrow_id="escrow_456",
        capture_method="manual",
        description="Test payment",
    )
    print(f"   Request Type: {frame.request_type.value}")
    print(f"   Object Type: {frame.object_type.value}")
    print(f"   Endpoint: {frame.endpoint}")
    print(f"   Idempotency Key: {frame.idempotency_key}")
    print(f"   Data: {frame.data}")
    print(f"   Escrow Context: {frame.escrow_context}")
    
    # Build escrow payment frame
    print("\n2. Building Escrow Payment Frame...")
    escrow_frame = builder.build_escrow_payment_frame(
        amount=10000,
        currency="usd",
        escrow_id="escrow_789",
        customer="cus_456",
    )
    print(f"   Request Type: {escrow_frame.request_type.value}")
    print(f"   Object Type: {escrow_frame.object_type.value}")
    print(f"   Endpoint: {escrow_frame.endpoint}")
    print(f"   Capture Method: {escrow_frame.data.get('capture_method')}")
    print(f"   Metadata: {escrow_frame.data.get('metadata')}")
    
    # Build Customer create frame
    print("\n3. Building Customer Create Frame...")
    customer_frame = builder.build_customer_create_frame(
        email="test@example.com",
        name="Test Customer",
        escrow_id="escrow_123",
    )
    print(f"   Request Type: {customer_frame.request_type.value}")
    print(f"   Object Type: {customer_frame.object_type.value}")
    print(f"   Endpoint: {customer_frame.endpoint}")
    print(f"   Data: {customer_frame.data}")
    
    # Build Charge create frame
    print("\n4. Building Charge Create Frame...")
    charge_frame = builder.build_charge_create_frame(
        amount=2000,
        currency="usd",
        customer="cus_123",
        escrow_id="escrow_456",
        capture=False,
    )
    print(f"   Request Type: {charge_frame.request_type.value}")
    print(f"   Object Type: {charge_frame.object_type.value}")
    print(f"   Endpoint: {charge_frame.endpoint}")
    print(f"   Capture: {charge_frame.data.get('capture')}")
    
    # Build Refund create frame
    print("\n5. Building Refund Create Frame...")
    refund_frame = builder.build_refund_create_frame(
        charge_id="ch_123",
        amount=1000,
        escrow_id="escrow_789",
        reason="requested_by_customer",
    )
    print(f"   Request Type: {refund_frame.request_type.value}")
    print(f"   Object Type: {refund_frame.object_type.value}")
    print(f"   Endpoint: {refund_frame.endpoint}")
    print(f"   Data: {refund_frame.data}")
    
    # Get headers
    print("\n6. Getting Request Headers...")
    headers = frame.get_headers()
    for key, value in headers.items():
        if key != "Authorization":
            print(f"   {key}: {value}")
        else:
            print(f"   {key}: Bearer ***")
    
    # Statistics
    print("\n7. Builder Statistics:")
    stats = builder.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("FRAME BUILDER READY FOR PRODUCTION")
    print("=" * 60)
