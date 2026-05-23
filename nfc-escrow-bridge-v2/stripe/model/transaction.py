#!/usr/bin/env python3
"""
Stripe Transaction Models for NFC Escrow Bridge
==================================================
Data models for Stripe transactions linked to escrow operations.

Features:
- Stripe Transaction model with escrow linking
- Escrow Transaction model with Stripe integration
- Transaction Modeler for data transformation
- Pydantic validation for data integrity

Author: Tyrone J Power Ω
Fold Entry: FE-OGUF-P1
Version: 2.0.0
"""

import json
import time
import secrets
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator


# ============================================================================
# ENUMS
# ============================================================================

class TransactionStatus(Enum):
    """Transaction status"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class TransactionType(Enum):
    """Transaction types"""
    PAYMENT = "payment"
    REFUND = "refund"
    CHARGEBACK = "chargeback"
    ESCROW_HOLD = "escrow_hold"
    ESCROW_RELEASE = "escrow_release"
    ESCROW_REFUND = "escrow_refund"


class Currency(Enum):
    """Supported currencies"""
    USD = "usd"
    EUR = "eur"
    GBP = "gbp"
    JPY = "jpy"
    CAD = "cad"
    AUD = "aud"
    CHF = "chf"
    CNY = "cny"
    HKD = "hkd"
    SGD = "sgd"


# ============================================================================
# STRIPE TRANSACTION MODEL
# ============================================================================

class StripeTransaction(BaseModel):
    """
    Stripe transaction model with escrow linking.
    
    Represents a payment transaction processed through Stripe,
    with additional fields for escrow integration.
    """
    
    # Stripe fields
    id: str = Field(..., description="Stripe transaction ID")
    object: str = Field(default="payment_intent", description="Stripe object type")
    amount: int = Field(..., gt=0, description="Amount in cents")
    currency: Currency = Field(default=Currency.USD, description="Currency code")
    status: str = Field(..., description="Stripe status")
    payment_method: Optional[str] = Field(default=None, description="Payment method ID")
    customer: Optional[str] = Field(default=None, description="Customer ID")
    description: Optional[str] = Field(default=None, description="Transaction description")
    
    # Escrow fields
    escrow_id: Optional[str] = Field(default=None, description="Linked escrow ID")
    escrow_status: Optional[TransactionStatus] = Field(default=None, description="Escrow status")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Transaction metadata")
    created: int = Field(default_factory=lambda: int(time.time()), description="Creation timestamp")
    
    # Computed fields
    amount_usd: float = Field(default=0.0, description="Amount in USD (computed)")
    
    @validator('amount_usd', always=True)
    def compute_amount_usd(cls, v, values):
        """Compute amount in USD"""
        amount = values.get('amount', 0)
        currency = values.get('currency', Currency.USD)
        
        # For simplicity, assume 1:1 conversion for now
        # In production, use real exchange rates
        return amount / 100
    
    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata size"""
        if len(v) > 50:
            raise ValueError("Metadata cannot have more than 50 keys")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.dict(exclude_unset=True)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.json(exclude_unset=True)
    
    @classmethod
    def from_stripe_response(cls, response: Dict[str, Any], escrow_id: Optional[str] = None) -> "StripeTransaction":
        """Create from Stripe API response"""
        metadata = response.get("metadata", {})
        if escrow_id:
            metadata["escrow_id"] = escrow_id
        
        return cls(
            id=response.get("id", ""),
            object=response.get("object", "payment_intent"),
            amount=response.get("amount", 0),
            currency=response.get("currency", "usd"),
            status=response.get("status", "unknown"),
            payment_method=response.get("payment_method"),
            customer=response.get("customer"),
            description=response.get("description"),
            metadata=metadata,
            escrow_id=escrow_id,
            created=response.get("created", int(time.time())),
        )
    
    def link_to_escrow(self, escrow_id: str, status: TransactionStatus = TransactionStatus.PENDING) -> "StripeTransaction":
        """Link this transaction to an escrow"""
        self.escrow_id = escrow_id
        self.escrow_status = status
        if "escrow_id" not in self.metadata:
            self.metadata["escrow_id"] = escrow_id
        return self


# ============================================================================
# ESCROW TRANSACTION MODEL
# ============================================================================

class EscrowTransaction(BaseModel):
    """
    Escrow transaction model with Stripe integration.
    
    Represents an escrow transaction that may be linked to
    one or more Stripe payment transactions.
    """
    
    # Escrow fields
    escrow_id: str = Field(..., description="Unique escrow identifier")
    status: TransactionStatus = Field(default=TransactionStatus.PENDING, description="Escrow status")
    type: TransactionType = Field(default=TransactionType.ESCROW_HOLD, description="Transaction type")
    
    # Amount and currency
    amount: int = Field(..., gt=0, description="Amount in cents")
    currency: Currency = Field(default=Currency.USD, description="Currency code")
    
    # Parties
    buyer: Optional[str] = Field(default=None, description="Buyer ID or identifier")
    seller: Optional[str] = Field(default=None, description="Seller ID or identifier")
    
    # Linked transactions
    stripe_transaction_ids: List[str] = Field(default_factory=list, description="Linked Stripe transaction IDs")
    payment_intent_ids: List[str] = Field(default_factory=list, description="Linked PaymentIntent IDs")
    
    # Conditions
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Release conditions")
    release_date: Optional[int] = Field(default=None, description="Automatic release timestamp")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Escrow metadata")
    created: int = Field(default_factory=lambda: int(time.time()), description="Creation timestamp")
    updated: int = Field(default_factory=lambda: int(time.time()), description="Last update timestamp")
    
    # Computed fields
    amount_usd: float = Field(default=0.0, description="Amount in USD (computed)")
    
    @validator('amount_usd', always=True)
    def compute_amount_usd(cls, v, values):
        """Compute amount in USD"""
        amount = values.get('amount', 0)
        return amount / 100
    
    @validator('conditions')
    def validate_conditions(cls, v):
        """Validate conditions"""
        if len(v) > 20:
            raise ValueError("Cannot have more than 20 conditions")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.dict(exclude_unset=True)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.json(exclude_unset=True)
    
    def add_stripe_transaction(self, transaction_id: str) -> "EscrowTransaction":
        """Add a linked Stripe transaction"""
        if transaction_id not in self.stripe_transaction_ids:
            self.stripe_transaction_ids.append(transaction_id)
        return self
    
    def add_payment_intent(self, intent_id: str) -> "EscrowTransaction":
        """Add a linked PaymentIntent"""
        if intent_id not in self.payment_intent_ids:
            self.payment_intent_ids.append(intent_id)
        return self
    
    def release(self, reason: str = "conditions_met") -> "EscrowTransaction":
        """Release the escrow"""
        self.status = TransactionStatus.SUCCEEDED
        self.metadata["release_reason"] = reason
        self.updated = int(time.time())
        return self
    
    def cancel(self, reason: str = "user_request") -> "EscrowTransaction":
        """Cancel the escrow"""
        self.status = TransactionStatus.CANCELED
        self.metadata["cancel_reason"] = reason
        self.updated = int(time.time())
        return self
    
    def dispute(self, reason: str = "fraud") -> "EscrowTransaction":
        """Dispute the escrow"""
        self.status = TransactionStatus.DISPUTED
        self.metadata["dispute_reason"] = reason
        self.updated = int(time.time())
        return self


# ============================================================================
# TRANSACTION MODELER
# ============================================================================

class TransactionModeler:
    """
    Models and transforms transactions between Stripe and Escrow systems.
    
    Provides:
    - Data transformation between Stripe and Escrow formats
    - Transaction validation
    - Escrow linking
    - State synchronization
    """
    
    def __init__(self):
        """Initialize Transaction Modeler"""
        self.transactions: Dict[str, Union[StripeTransaction, EscrowTransaction]] = {}
        self.links: Dict[str, List[str]] = {}  # escrow_id -> [stripe_tx_ids]
    
    def create_stripe_transaction(
        self,
        amount: int,
        currency: str = "usd",
        status: str = "succeeded",
        escrow_id: Optional[str] = None,
        **kwargs,
    ) -> StripeTransaction:
        """Create a Stripe transaction"""
        tx = StripeTransaction(
            id=f"tx_stripe_{secrets.token_hex(8)}",
            amount=amount,
            currency=currency,
            status=status,
            escrow_id=escrow_id,
            **kwargs,
        )
        
        self.transactions[tx.id] = tx
        
        if escrow_id:
            if escrow_id not in self.links:
                self.links[escrow_id] = []
            self.links[escrow_id].append(tx.id)
        
        return tx
    
    def create_escrow_transaction(
        self,
        amount: int,
        currency: str = "usd",
        escrow_id: Optional[str] = None,
        **kwargs,
    ) -> EscrowTransaction:
        """Create an escrow transaction"""
        if not escrow_id:
            escrow_id = f"escrow_{secrets.token_hex(8)}"
        
        tx = EscrowTransaction(
            escrow_id=escrow_id,
            amount=amount,
            currency=currency,
            **kwargs,
        )
        
        self.transactions[escrow_id] = tx
        
        if escrow_id not in self.links:
            self.links[escrow_id] = []
        
        return tx
    
    def link_transactions(
        self,
        stripe_transaction_id: str,
        escrow_transaction_id: str,
    ) -> bool:
        """Link a Stripe transaction to an escrow transaction"""
        stripe_tx = self.transactions.get(stripe_transaction_id)
        escrow_tx = self.transactions.get(escrow_transaction_id)
        
        if not stripe_tx or not escrow_tx:
            return False
        
        # Update Stripe transaction
        if isinstance(stripe_tx, StripeTransaction):
            stripe_tx.escrow_id = escrow_tx.escrow_id
            stripe_tx.escrow_status = escrow_tx.status
        
        # Update Escrow transaction
        if isinstance(escrow_tx, EscrowTransaction):
            escrow_tx.add_stripe_transaction(stripe_tx.id)
        
        # Update links
        if escrow_tx.escrow_id not in self.links:
            self.links[escrow_tx.escrow_id] = []
        if stripe_tx.id not in self.links[escrow_tx.escrow_id]:
            self.links[escrow_tx.escrow_id].append(stripe_tx.id)
        
        return True
    
    def get_linked_transactions(self, escrow_id: str) -> List[StripeTransaction]:
        """Get all Stripe transactions linked to an escrow"""
        tx_ids = self.links.get(escrow_id, [])
        return [tx for tx in self.transactions.values() 
                if isinstance(tx, StripeTransaction) and tx.id in tx_ids]
    
    def get_escrow_by_stripe(self, stripe_id: str) -> Optional[EscrowTransaction]:
        """Get the escrow transaction linked to a Stripe transaction"""
        stripe_tx = self.transactions.get(stripe_id)
        if not stripe_tx or not isinstance(stripe_tx, StripeTransaction):
            return None
        
        if stripe_tx.escrow_id:
            escrow_tx = self.transactions.get(stripe_tx.escrow_id)
            if isinstance(escrow_tx, EscrowTransaction):
                return escrow_tx
        
        return None
    
    def sync_status(
        self,
        stripe_id: str,
        escrow_status: TransactionStatus,
    ) -> bool:
        """Synchronize status between Stripe and Escrow"""
        stripe_tx = self.transactions.get(stripe_id)
        if not stripe_tx or not isinstance(stripe_tx, StripeTransaction):
            return False
        
        # Update Stripe transaction
        stripe_tx.escrow_status = escrow_status
        
        # Update linked Escrow transaction
        escrow_tx = self.get_escrow_by_stripe(stripe_id)
        if escrow_tx:
            escrow_tx.status = escrow_status
            escrow_tx.updated = int(time.time())
        
        return True
    
    def validate_transaction(self, tx: Union[StripeTransaction, EscrowTransaction]) -> Dict[str, Any]:
        """Validate a transaction"""
        errors = []
        
        if tx.amount <= 0:
            errors.append("Amount must be positive")
        
        if not tx.currency:
            errors.append("Currency is required")
        
        if isinstance(tx, EscrowTransaction):
            if not tx.escrow_id:
                errors.append("Escrow ID is required")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
    
    def get_all_transactions(self) -> List[Union[StripeTransaction, EscrowTransaction]]:
        """Get all transactions"""
        return list(self.transactions.values())
    
    def get_by_type(self, tx_type: type) -> List[Union[StripeTransaction, EscrowTransaction]]:
        """Get transactions by type"""
        return [tx for tx in self.transactions.values() if isinstance(tx, tx_type)]
    
    def clear(self):
        """Clear all transactions"""
        self.transactions.clear()
        self.links.clear()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Create modeler
    modeler = TransactionModeler()
    
    print("=" * 60)
    print("TRANSACTION MODELER TEST")
    print("=" * 60)
    
    # Create Stripe transaction
    print("\n1. Creating Stripe Transaction...")
    stripe_tx = modeler.create_stripe_transaction(
        amount=5000,
        currency="usd",
        status="succeeded",
        payment_method="pm_123",
        customer="cus_456",
    )
    print(f"   ID: {stripe_tx.id}")
    print(f"   Amount: ${stripe_tx.amount_usd:.2f}")
    print(f"   Status: {stripe_tx.status}")
    
    # Create Escrow transaction
    print("\n2. Creating Escrow Transaction...")
    escrow_tx = modeler.create_escrow_transaction(
        amount=5000,
        currency="usd",
        escrow_id="escrow_789",
        buyer="user_1",
        seller="user_2",
    )
    print(f"   Escrow ID: {escrow_tx.escrow_id}")
    print(f"   Amount: ${escrow_tx.amount_usd:.2f}")
    print(f"   Status: {escrow_tx.status.value}")
    
    # Link transactions
    print("\n3. Linking Transactions...")
    success = modeler.link_transactions(stripe_tx.id, escrow_tx.escrow_id)
    print(f"   Linked: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    # Get linked transactions
    print("\n4. Getting Linked Transactions...")
    linked = modeler.get_linked_transactions(escrow_tx.escrow_id)
    print(f"   Found {len(linked)} linked Stripe transactions")
    for tx in linked:
        print(f"   - {tx.id}: ${tx.amount_usd:.2f}")
    
    # Sync status
    print("\n5. Syncing Status...")
    escrow_tx.release()
    modeler.sync_status(stripe_tx.id, TransactionStatus.SUCCEEDED)
    print(f"   Stripe Status: {stripe_tx.escrow_status.value}")
    print(f"   Escrow Status: {escrow_tx.status.value}")
    
    # Validate
    print("\n6. Validating Transactions...")
    stripe_valid = modeler.validate_transaction(stripe_tx)
    escrow_valid = modeler.validate_transaction(escrow_tx)
    print(f"   Stripe Valid: {stripe_valid['valid']}")
    print(f"   Escrow Valid: {escrow_valid['valid']}")
    
    # JSON serialization
    print("\n7. JSON Serialization...")
    print(f"   Stripe JSON: {stripe_tx.to_json()[:100]}...")
    print(f"   Escrow JSON: {escrow_tx.to_json()[:100]}...")
    
    print("\n" + "=" * 60)
    print("MODELER READY FOR PRODUCTION")
    print("=" * 60)
