#!/usr/bin/env python3
"""
PaymentIntent Models for NFC Escrow Bridge
===========================================
Stripe PaymentIntent-specific models with escrow integration.

Features:
- PaymentIntent data model
- PaymentIntent lifecycle management
- Escrow linking
- Status tracking

Author: Tyrone J Power Ω
Fold Entry: FE-OGUF-P1
Version: 2.0.0
"""

import time
import secrets
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator
from .transaction import Currency, TransactionStatus


# ============================================================================
# ENUMS
# ============================================================================

class PaymentIntentStatus(Enum):
    """Stripe PaymentIntent status"""
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    REQUIRES_ACTION = "requires_action"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class PaymentMethodType(Enum):
    """Payment method types"""
    CARD = "card"
    CARD_PRESENT = "card_present"
    SEPA_DEBIT = "sepa_debit"
    IDEAL = "ideal"
    GIROPAY = "giropay"
    SOFORT = "sofort"
    BANCONTACT = "bancontact"
    EPS = "eps"
    P24 = "p24"
    ACSS_DEBIT = "acss_debit"


class ConfirmationMethod(Enum):
    """Confirmation methods"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class CaptureMethod(Enum):
    """Capture methods"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"


# ============================================================================
# PAYMENT INTENT DATA
# ============================================================================

class PaymentIntentData(BaseModel):
    """
    Complete PaymentIntent data model with escrow integration.
    
    Represents a Stripe PaymentIntent with additional fields for
    NFC Escrow Bridge integration.
    """
    
    # Stripe fields
    id: str = Field(..., description="PaymentIntent ID")
    object: str = Field(default="payment_intent", description="Object type")
    amount: int = Field(..., gt=0, description="Amount in cents")
    amount_details: Optional[Dict[str, Any]] = Field(default=None, description="Amount details")
    amount_received: int = Field(default=0, description="Amount received in cents")
    currency: Currency = Field(default=Currency.USD, description="Currency code")
    
    # Status
    status: PaymentIntentStatus = Field(..., description="PaymentIntent status")
    
    # Payment method
    payment_method: Optional[str] = Field(default=None, description="PaymentMethod ID")
    payment_method_types: List[str] = Field(
        default=["card"],
        description="Allowed payment method types"
    )
    payment_method_configuration_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Payment method configuration"
    )
    
    # Confirmation
    confirmation_method: ConfirmationMethod = Field(
        default=ConfirmationMethod.AUTOMATIC,
        description="Confirmation method"
    )
    confirm: bool = Field(default=False, description="Whether to confirm immediately")
    
    # Capture
    capture_method: CaptureMethod = Field(
        default=CaptureMethod.AUTOMATIC,
        description="Capture method"
    )
    
    # Customer
    customer: Optional[str] = Field(default=None, description="Customer ID")
    
    # Description
    description: Optional[str] = Field(default=None, description="Description")
    statement_descriptor: Optional[str] = Field(default=None, description="Statement descriptor")
    statement_descriptor_suffix: Optional[str] = Field(default=None, description="Statement descriptor suffix")
    
    # Application
    application_fee_amount: Optional[int] = Field(default=None, description="Application fee in cents")
    on_behalf_of: Optional[str] = Field(default=None, description="Connected account ID")
    transfer_data: Optional[Dict[str, Any]] = Field(default=None, description="Transfer data")
    transfer_group: Optional[str] = Field(default=None, description="Transfer group")
    
    # Escrow fields
    escrow_id: Optional[str] = Field(default=None, description="Linked escrow ID")
    escrow_status: Optional[TransactionStatus] = Field(default=None, description="Escrow status")
    escrow_hold: bool = Field(default=False, description="Whether to hold funds in escrow")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    
    # Timing
    created: int = Field(default_factory=lambda: int(time.time()), description="Creation timestamp")
    last_payment_error: Optional[Dict[str, Any]] = Field(default=None, description="Last payment error")
    next_action: Optional[Dict[str, Any]] = Field(default=None, description="Next action required")
    
    # Computed fields
    amount_usd: float = Field(default=0.0, description="Amount in USD")
    amount_received_usd: float = Field(default=0.0, description="Amount received in USD")
    
    @validator('amount_usd', 'amount_received_usd', always=True)
    def compute_usd_values(cls, v, values, field):
        """Compute USD values"""
        if field.name == 'amount_usd':
            return values.get('amount', 0) / 100
        elif field.name == 'amount_received_usd':
            return values.get('amount_received', 0) / 100
        return v
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata"""
        if len(v) > 50:
            raise ValueError("Metadata cannot have more than 50 keys")
        return v
    
    @validator('payment_method_types')
    def validate_payment_method_types(cls, v):
        """Validate payment method types"""
        valid_types = [t.value for t in PaymentMethodType]
        for pt in v:
            if pt not in valid_types:
                raise ValueError(f"Invalid payment method type: {pt}")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.dict(exclude_unset=True)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.json(exclude_unset=True)
    
    @classmethod
    def from_stripe_response(
        cls,
        response: Dict[str, Any],
        escrow_id: Optional[str] = None,
        escrow_hold: bool = False,
    ) -> "PaymentIntentData":
        """Create from Stripe API response"""
        metadata = response.get("metadata", {})
        if escrow_id:
            metadata["escrow_id"] = escrow_id
        
        return cls(
            id=response.get("id", ""),
            object=response.get("object", "payment_intent"),
            amount=response.get("amount", 0),
            amount_details=response.get("amount_details"),
            amount_received=response.get("amount_received", 0),
            currency=response.get("currency", "usd"),
            status=response.get("status", "requires_payment_method"),
            payment_method=response.get("payment_method"),
            payment_method_types=response.get("payment_method_types", ["card"]),
            payment_method_configuration_details=response.get("payment_method_configuration_details"),
            confirmation_method=response.get("confirmation_method", "automatic"),
            confirm=response.get("confirm", False),
            capture_method=response.get("capture_method", "automatic"),
            customer=response.get("customer"),
            description=response.get("description"),
            statement_descriptor=response.get("statement_descriptor"),
            statement_descriptor_suffix=response.get("statement_descriptor_suffix"),
            application_fee_amount=response.get("application_fee_amount"),
            on_behalf_of=response.get("on_behalf_of"),
            transfer_data=response.get("transfer_data"),
            transfer_group=response.get("transfer_group"),
            metadata=metadata,
            created=response.get("created", int(time.time())),
            last_payment_error=response.get("last_payment_error"),
            next_action=response.get("next_action"),
            escrow_id=escrow_id,
            escrow_hold=escrow_hold,
        )
    
    def link_to_escrow(self, escrow_id: str) -> "PaymentIntentData":
        """Link to an escrow"""
        self.escrow_id = escrow_id
        if "escrow_id" not in self.metadata:
            self.metadata["escrow_id"] = escrow_id
        return self
    
    def set_escrow_hold(self, hold: bool = True) -> "PaymentIntentData":
        """Set escrow hold flag"""
        self.escrow_hold = hold
        self.capture_method = CaptureMethod.MANUAL if hold else CaptureMethod.AUTOMATIC
        return self
    
    def is_escrow(self) -> bool:
        """Check if this is an escrow payment"""
        return self.escrow_hold or self.escrow_id is not None
    
    def is_successful(self) -> bool:
        """Check if payment was successful"""
        return self.status == PaymentIntentStatus.SUCCEEDED
    
    def is_pending(self) -> bool:
        """Check if payment is pending"""
        return self.status in [
            PaymentIntentStatus.REQUIRES_PAYMENT_METHOD,
            PaymentIntentStatus.REQUIRES_CONFIRMATION,
            PaymentIntentStatus.REQUIRES_ACTION,
            PaymentIntentStatus.PROCESSING,
        ]
    
    def is_failed(self) -> bool:
        """Check if payment failed"""
        return self.status == PaymentIntentStatus.CANCELED


# ============================================================================
# PAYMENT INTENT MODEL
# ============================================================================

class PaymentIntentModel:
    """
    Models and manages PaymentIntents with escrow integration.
    
    Provides:
    - PaymentIntent creation and management
    - Escrow linking
    - Status tracking
    - Lifecycle management
    """
    
    def __init__(self):
        """Initialize PaymentIntent Model"""
        self.payment_intents: Dict[str, PaymentIntentData] = {}
        self.escrow_links: Dict[str, List[str]] = {}  # escrow_id -> [pi_ids]
    
    def create(
        self,
        amount: int,
        currency: str = "usd",
        escrow_id: Optional[str] = None,
        escrow_hold: bool = True,
        **kwargs,
    ) -> PaymentIntentData:
        """Create a new PaymentIntent"""
        pi_id = f"pi_{secrets.token_hex(14)}"
        
        pi = PaymentIntentData(
            id=pi_id,
            amount=amount,
            currency=currency,
            status=PaymentIntentStatus.REQUIRES_PAYMENT_METHOD,
            escrow_id=escrow_id,
            escrow_hold=escrow_hold,
            **kwargs,
        )
        
        self.payment_intents[pi_id] = pi
        
        if escrow_id:
            if escrow_id not in self.escrow_links:
                self.escrow_links[escrow_id] = []
            self.escrow_links[escrow_id].append(pi_id)
        
        return pi
    
    def retrieve(self, pi_id: str) -> Optional[PaymentIntentData]:
        """Retrieve a PaymentIntent"""
        return self.payment_intents.get(pi_id)
    
    def update(self, pi_id: str, **kwargs) -> Optional[PaymentIntentData]:
        """Update a PaymentIntent"""
        pi = self.retrieve(pi_id)
        if not pi:
            return None
        
        for key, value in kwargs.items():
            setattr(pi, key, value)
        
        return pi
    
    def confirm(self, pi_id: str, payment_method: Optional[str] = None) -> Optional[PaymentIntentData]:
        """Confirm a PaymentIntent"""
        pi = self.retrieve(pi_id)
        if not pi:
            return None
        
        pi.status = PaymentIntentStatus.SUCCEEDED
        if payment_method:
            pi.payment_method = payment_method
        pi.amount_received = pi.amount
        
        return pi
    
    def cancel(self, pi_id: str) -> Optional[PaymentIntentData]:
        """Cancel a PaymentIntent"""
        pi = self.retrieve(pi_id)
        if not pi:
            return None
        
        pi.status = PaymentIntentStatus.CANCELED
        return pi
    
    def link_to_escrow(self, pi_id: str, escrow_id: str) -> bool:
        """Link a PaymentIntent to an escrow"""
        pi = self.retrieve(pi_id)
        if not pi:
            return False
        
        pi.link_to_escrow(escrow_id)
        
        if escrow_id not in self.escrow_links:
            self.escrow_links[escrow_id] = []
        if pi_id not in self.escrow_links[escrow_id]:
            self.escrow_links[escrow_id].append(pi_id)
        
        return True
    
    def get_by_escrow(self, escrow_id: str) -> List[PaymentIntentData]:
        """Get all PaymentIntents for an escrow"""
        pi_ids = self.escrow_links.get(escrow_id, [])
        return [self.payment_intents[pi_id] for pi_id in pi_ids if pi_id in self.payment_intents]
    
    def get_escrow_by_payment(self, pi_id: str) -> Optional[str]:
        """Get the escrow ID for a PaymentIntent"""
        pi = self.retrieve(pi_id)
        return pi.escrow_id if pi else None
    
    def set_escrow_status(
        self,
        pi_id: str,
        status: TransactionStatus,
    ) -> bool:
        """Set the escrow status for a PaymentIntent"""
        pi = self.retrieve(pi_id)
        if not pi:
            return False
        
        pi.escrow_status = status
        return True
    
    def list_all(self, limit: int = 100) -> List[PaymentIntentData]:
        """List all PaymentIntents"""
        return list(self.payment_intents.values())[-limit:]
    
    def list_by_status(self, status: PaymentIntentStatus) -> List[PaymentIntentData]:
        """List PaymentIntents by status"""
        return [pi for pi in self.payment_intents.values() if pi.status == status]
    
    def list_escrow(self) -> List[PaymentIntentData]:
        """List all escrow PaymentIntents"""
        return [pi for pi in self.payment_intents.values() if pi.is_escrow()]
    
    def clear(self):
        """Clear all PaymentIntents"""
        self.payment_intents.clear()
        self.escrow_links.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        total = len(self.payment_intents)
        successful = len(self.list_by_status(PaymentIntentStatus.SUCCEEDED))
        pending = len(self.list_by_status(PaymentIntentStatus.REQUIRES_PAYMENT_METHOD))
        pending += len(self.list_by_status(PaymentIntentStatus.REQUIRES_CONFIRMATION))
        pending += len(self.list_by_status(PaymentIntentStatus.REQUIRES_ACTION))
        pending += len(self.list_by_status(PaymentIntentStatus.PROCESSING))
        canceled = len(self.list_by_status(PaymentIntentStatus.CANCELED))
        escrow = len(self.list_escrow())
        
        return {
            "total": total,
            "successful": successful,
            "pending": pending,
            "canceled": canceled,
            "escrow": escrow,
            "escrow_links": len(self.escrow_links),
        }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Create model
    model = PaymentIntentModel()
    
    print("=" * 60)
    print("PAYMENT INTENT MODEL TEST")
    print("=" * 60)
    
    # Create PaymentIntent
    print("\n1. Creating PaymentIntent...")
    pi = model.create(
        amount=5000,
        currency="usd",
        escrow_id="escrow_123",
        escrow_hold=True,
        description="Test payment",
    )
    print(f"   ID: {pi.id}")
    print(f"   Amount: ${pi.amount_usd:.2f}")
    print(f"   Status: {pi.status.value}")
    print(f"   Escrow ID: {pi.escrow_id}")
    print(f"   Escrow Hold: {pi.escrow_hold}")
    
    # Confirm PaymentIntent
    print("\n2. Confirming PaymentIntent...")
    pi = model.confirm(pi.id, payment_method="pm_456")
    print(f"   Status: {pi.status.value}")
    print(f"   Payment Method: {pi.payment_method}")
    print(f"   Amount Received: ${pi.amount_received_usd:.2f}")
    
    # Create another PaymentIntent
    print("\n3. Creating another PaymentIntent...")
    pi2 = model.create(
        amount=10000,
        currency="usd",
        escrow_id="escrow_123",
        description="Second payment",
    )
    print(f"   ID: {pi2.id}")
    print(f"   Amount: ${pi2.amount_usd:.2f}")
    
    # Get by escrow
    print("\n4. Getting PaymentIntents by Escrow...")
    escrow_pis = model.get_by_escrow("escrow_123")
    print(f"   Found {len(escrow_pis)} PaymentIntents")
    for pi in escrow_pis:
        print(f"   - {pi.id}: ${pi.amount_usd:.2f} ({pi.status.value})")
    
    # Set escrow status
    print("\n5. Setting Escrow Status...")
    model.set_escrow_status(pi.id, TransactionStatus.FUNDED)
    print(f"   Escrow Status: {pi.escrow_status.value}")
    
    # Statistics
    print("\n6. Statistics:")
    stats = model.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # JSON serialization
    print("\n7. JSON Serialization:")
    print(f"   {pi.to_json()[:200]}...")
    
    print("\n" + "=" * 60)
    print("PAYMENT INTENT MODEL READY FOR PRODUCTION")
    print("=" * 60)
