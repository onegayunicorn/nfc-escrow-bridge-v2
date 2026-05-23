#!/usr/bin/env python3
"""
Escrow Models for NFC Escrow Bridge
=====================================
Escrow-specific data models and state management.

Features:
- Escrow state machine
- Escrow record management
- Condition evaluation
- Release/refund workflows

Author: Tyrone J Power Ω
Fold Entry: FE-OGUF-P1
Version: 2.0.0
"""

import time
import secrets
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from pydantic import BaseModel, Field, validator
from .transaction import TransactionStatus, TransactionType, Currency


# ============================================================================
# ENUMS
# ============================================================================

class EscrowState(Enum):
    """Escrow lifecycle states"""
    CREATED = "created"           # Escrow created, awaiting funds
    FUNDED = "funded"             # Funds received, awaiting conditions
    ACTIVE = "active"             # Conditions being evaluated
    COMPLETED = "completed"       # All conditions met, funds released
    CANCELED = "canceled"         # Escrow canceled by party
    REFUNDED = "refunded"         # Funds refunded to buyer
    DISPUTED = "disputed"         # Dispute in progress
    EXPIRED = "expired"           # Escrow expired


class EscrowConditionType(Enum):
    """Types of escrow conditions"""
    TIME_BASED = "time_based"      # Release after X time
    EVENT_BASED = "event_based"    # Release on specific event
    MANUAL = "manual"              # Manual release by admin
    MULTI_SIG = "multi_sig"        # Multiple signatures required
    SMART_CONTRACT = "smart_contract"  # Blockchain smart contract


class DisputeReason(Enum):
    """Dispute reasons"""
    FRAUD = "fraud"
    NOT_RECEIVED = "not_received"
    NOT_AS_DESCRIBED = "not_as_described"
    UNAUTHORIZED = "unauthorized"
    DUPLICATE = "duplicate"
    OTHER = "other"


# ============================================================================
# ESCROW RECORD
# ============================================================================

class EscrowRecord(BaseModel):
    """
    Complete escrow record with full lifecycle tracking.
    
    Represents a complete escrow transaction from creation to settlement,
    with all associated data and state transitions.
    """
    
    # Identification
    escrow_id: str = Field(..., description="Unique escrow identifier")
    transaction_hash: Optional[str] = Field(default=None, description="Blockchain transaction hash")
    
    # State
    state: EscrowState = Field(default=EscrowState.CREATED, description="Current escrow state")
    previous_state: Optional[EscrowState] = Field(default=None, description="Previous state")
    
    # Financial
    amount: int = Field(..., gt=0, description="Escrow amount in cents")
    currency: Currency = Field(default=Currency.USD, description="Currency code")
    fee: int = Field(default=0, ge=0, description="Escrow fee in cents")
    net_amount: int = Field(default=0, description="Net amount after fees")
    
    # Parties
    buyer: Dict[str, Any] = Field(default_factory=dict, description="Buyer information")
    seller: Dict[str, Any] = Field(default_factory=dict, description="Seller information")
    arbitrator: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrator information")
    
    # Linked transactions
    stripe_payment_intents: List[str] = Field(default_factory=list, description="Stripe PaymentIntent IDs")
    stripe_charges: List[str] = Field(default_factory=list, description="Stripe Charge IDs")
    nfc_tag_ids: List[str] = Field(default_factory=list, description="NFC tag IDs")
    
    # Conditions
    conditions: List[Dict[str, Any]] = Field(default_factory=list, description="Release conditions")
    condition_type: EscrowConditionType = Field(
        default=EscrowConditionType.MANUAL,
        description="Primary condition type"
    )
    
    # Timing
    created: int = Field(default_factory=lambda: int(time.time()), description="Creation timestamp")
    funded_at: Optional[int] = Field(default=None, description="When funds were received")
    completed_at: Optional[int] = Field(default=None, description="When escrow was completed")
    expires_at: Optional[int] = Field(default=None, description="Expiration timestamp")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    notes: str = Field(default="", description="Human-readable notes")
    
    # Computed fields
    amount_usd: float = Field(default=0.0, description="Amount in USD")
    fee_usd: float = Field(default=0.0, description="Fee in USD")
    net_amount_usd: float = Field(default=0.0, description="Net amount in USD")
    
    @validator('amount_usd', 'fee_usd', 'net_amount_usd', always=True)
    def compute_usd_values(cls, v, values, field):
        """Compute USD values"""
        if field.name == 'amount_usd':
            return values.get('amount', 0) / 100
        elif field.name == 'fee_usd':
            return values.get('fee', 0) / 100
        elif field.name == 'net_amount_usd':
            return (values.get('amount', 0) - values.get('fee', 0)) / 100
        return v
    
    @validator('net_amount', always=True)
    def compute_net_amount(cls, v, values):
        """Compute net amount"""
        return values.get('amount', 0) - values.get('fee', 0)
    
    @validator('conditions')
    def validate_conditions(cls, v):
        """Validate conditions"""
        for condition in v:
            if 'type' not in condition:
                raise ValueError("Condition must have a type")
            if condition['type'] not in [c.value for c in EscrowConditionType]:
                raise ValueError(f"Invalid condition type: {condition['type']}")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.dict(exclude_unset=True)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.json(exclude_unset=True)
    
    def transition_to(self, new_state: EscrowState, **kwargs) -> "EscrowRecord":
        """Transition to a new state"""
        # Validate state transition
        if not self._is_valid_transition(new_state):
            raise ValueError(f"Cannot transition from {self.state.value} to {new_state.value}")
        
        # Update state
        self.previous_state = self.state
        self.state = new_state
        
        # Update timestamps
        if new_state == EscrowState.FUNDED:
            self.funded_at = int(time.time())
        elif new_state == EscrowState.COMPLETED:
            self.completed_at = int(time.time())
        
        # Update metadata
        if kwargs:
            self.metadata.update(kwargs)
        
        return self
    
    def _is_valid_transition(self, new_state: EscrowState) -> bool:
        """Check if state transition is valid"""
        valid_transitions = {
            EscrowState.CREATED: [EscrowState.FUNDED, EscrowState.CANCELED],
            EscrowState.FUNDED: [EscrowState.ACTIVE, EscrowState.CANCELED, EscrowState.EXPIRED],
            EscrowState.ACTIVE: [EscrowState.COMPLETED, EscrowState.CANCELED, EscrowState.DISPUTED, EscrowState.EXPIRED],
            EscrowState.COMPLETED: [],  # Terminal state
            EscrowState.CANCELED: [EscrowState.REFUNDED],
            EscrowState.REFUNDED: [],  # Terminal state
            EscrowState.DISPUTED: [EscrowState.COMPLETED, EscrowState.REFUNDED],
            EscrowState.EXPIRED: [EscrowState.REFUNDED],
        }
        
        allowed = valid_transitions.get(self.state, [])
        return new_state in allowed
    
    def is_complete(self) -> bool:
        """Check if escrow is complete"""
        return self.state in [EscrowState.COMPLETED, EscrowState.REFUNDED, EscrowState.EXPIRED]
    
    def is_active(self) -> bool:
        """Check if escrow is active"""
        return self.state in [EscrowState.CREATED, EscrowState.FUNDED, EscrowState.ACTIVE, EscrowState.DISPUTED]
    
    def add_stripe_payment_intent(self, intent_id: str) -> "EscrowRecord":
        """Add a Stripe PaymentIntent"""
        if intent_id not in self.stripe_payment_intents:
            self.stripe_payment_intents.append(intent_id)
        return self
    
    def add_stripe_charge(self, charge_id: str) -> "EscrowRecord":
        """Add a Stripe Charge"""
        if charge_id not in self.stripe_charges:
            self.stripe_charges.append(charge_id)
        return self
    
    def add_nfc_tag(self, tag_id: str) -> "EscrowRecord":
        """Add an NFC tag ID"""
        if tag_id not in self.nfc_tag_ids:
            self.nfc_tag_ids.append(tag_id)
        return self
    
    def add_condition(self, condition: Dict[str, Any]) -> "EscrowRecord":
        """Add a release condition"""
        self.conditions.append(condition)
        return self
    
    def set_expiration(self, seconds: int) -> "EscrowRecord":
        """Set expiration time"""
        self.expires_at = int(time.time()) + seconds
        return self


# ============================================================================
# ESCROW CONDITION
# ============================================================================

class EscrowCondition(BaseModel):
    """
    Individual escrow condition that must be met for release.
    """
    
    condition_id: str = Field(default_factory=lambda: f"cond_{secrets.token_hex(4)}", description="Unique condition ID")
    condition_type: EscrowConditionType = Field(..., description="Type of condition")
    description: str = Field(default="", description="Human-readable description")
    
    # Type-specific fields
    target_value: Optional[Any] = Field(default=None, description="Target value to match")
    current_value: Optional[Any] = Field(default=None, description="Current value")
    comparison: Optional[str] = Field(default="equals", description="Comparison operator")
    
    # Timing (for time-based conditions)
    duration_seconds: Optional[int] = Field(default=None, description="Duration in seconds")
    start_time: Optional[int] = Field(default=None, description="Start timestamp")
    end_time: Optional[int] = Field(default=None, description="End timestamp")
    
    # Status
    met: bool = Field(default=False, description="Whether condition is met")
    checked_at: Optional[int] = Field(default=None, description="Last check timestamp")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def to_dict(self) -> Dict[str, Any]:
        return self.dict(exclude_unset=True)
    
    def check(self, current_value: Any = None) -> bool:
        """Check if condition is met"""
        if current_value is not None:
            self.current_value = current_value
            self.checked_at = int(time.time())
        
        if self.condition_type == EscrowConditionType.TIME_BASED:
            if self.end_time:
                self.met = time.time() >= self.end_time
            elif self.duration_seconds and self.start_time:
                self.met = time.time() >= (self.start_time + self.duration_seconds)
        
        elif self.condition_type == EscrowConditionType.EVENT_BASED:
            if self.comparison == "equals":
                self.met = self.current_value == self.target_value
            elif self.comparison == "greater_than":
                self.met = self.current_value > self.target_value
            elif self.comparison == "less_than":
                self.met = self.current_value < self.target_value
            elif self.comparison == "contains":
                self.met = self.target_value in self.current_value
        
        elif self.condition_type == EscrowConditionType.MANUAL:
            # Manual conditions are always "not met" until explicitly set
            pass
        
        elif self.condition_type == EscrowConditionType.MULTI_SIG:
            # Check if required signatures are present
            required = self.target_value or 1
            current = len(self.current_value or [])
            self.met = current >= required
        
        return self.met


# ============================================================================
# ESCROW CONDITION EVALUATOR
# ============================================================================

class EscrowConditionEvaluator:
    """
    Evaluates escrow conditions to determine if funds should be released.
    """
    
    def __init__(self):
        self.conditions: Dict[str, EscrowCondition] = {}
    
    def add_condition(self, condition: EscrowCondition) -> str:
        """Add a condition to evaluate"""
        condition_id = condition.condition_id
        self.conditions[condition_id] = condition
        return condition_id
    
    def remove_condition(self, condition_id: str) -> bool:
        """Remove a condition"""
        if condition_id in self.conditions:
            del self.conditions[condition_id]
            return True
        return False
    
    def check_condition(self, condition_id: str, current_value: Any = None) -> bool:
        """Check a specific condition"""
        condition = self.conditions.get(condition_id)
        if not condition:
            return False
        return condition.check(current_value)
    
    def check_all(self, current_values: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Check all conditions"""
        current_values = current_values or {}
        results = {}
        all_met = True
        
        for condition_id, condition in self.conditions.items():
            value = current_values.get(condition_id)
            met = condition.check(value)
            results[condition_id] = {
                "met": met,
                "condition": condition.to_dict(),
            }
            if not met:
                all_met = False
        
        return {
            "all_met": all_met,
            "results": results,
        }
    
    def get_unmet_conditions(self) -> List[EscrowCondition]:
        """Get all unmet conditions"""
        return [c for c in self.conditions.values() if not c.met]
    
    def get_met_conditions(self) -> List[EscrowCondition]:
        """Get all met conditions"""
        return [c for c in self.conditions.values() if c.met]
    
    def clear(self):
        """Clear all conditions"""
        self.conditions.clear()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Create escrow record
    escrow = EscrowRecord(
        escrow_id="escrow_test_123",
        amount=10000,  # $100.00
        currency=Currency.USD,
        fee=500,  # $5.00 fee
        buyer={"id": "user_1", "name": "Alice"},
        seller={"id": "user_2", "name": "Bob"},
        condition_type=EscrowConditionType.MANUAL,
    )
    
    print("=" * 60)
    print("ESCROW RECORD TEST")
    print("=" * 60)
    
    # Print initial state
    print(f"\n1. Initial State:")
    print(f"   Escrow ID: {escrow.escrow_id}")
    print(f"   Amount: ${escrow.amount_usd:.2f}")
    print(f"   Fee: ${escrow.fee_usd:.2f}")
    print(f"   Net: ${escrow.net_amount_usd:.2f}")
    print(f"   State: {escrow.state.value}")
    print(f"   Buyer: {escrow.buyer['name']}")
    print(f"   Seller: {escrow.seller['name']}")
    
    # Add Stripe PaymentIntent
    print(f"\n2. Adding Stripe PaymentIntent...")
    escrow.add_stripe_payment_intent("pi_test_456")
    print(f"   PaymentIntents: {escrow.stripe_payment_intents}")
    
    # Add NFC tag
    print(f"\n3. Adding NFC Tag...")
    escrow.add_nfc_tag("nfc_abc123")
    print(f"   NFC Tags: {escrow.nfc_tag_ids}")
    
    # Set expiration
    print(f"\n4. Setting Expiration (1 hour)...")
    escrow.set_expiration(3600)
    print(f"   Expires: {escrow.expires_at}")
    
    # Transition states
    print(f"\n5. Transitioning States...")
    print(f"   CREATED -> FUNDED")
    escrow.transition_to(EscrowState.FUNDED)
    print(f"   State: {escrow.state.value}")
    print(f"   Funded At: {escrow.funded_at}")
    
    print(f"   FUNDED -> ACTIVE")
    escrow.transition_to(EscrowState.ACTIVE)
    print(f"   State: {escrow.state.value}")
    
    print(f"   ACTIVE -> COMPLETED")
    escrow.transition_to(EscrowState.COMPLETED)
    print(f"   State: {escrow.state.value}")
    print(f"   Completed At: {escrow.completed_at}")
    
    # Check status
    print(f"\n6. Status Checks:")
    print(f"   Is Complete: {escrow.is_complete()}")
    print(f"   Is Active: {escrow.is_active()}")
    
    # JSON serialization
    print(f"\n7. JSON Serialization:")
    print(f"   {escrow.to_json()[:200]}...")
    
    # Condition evaluator
    print(f"\n8. Condition Evaluator Test:")
    evaluator = EscrowConditionEvaluator()
    
    # Add time-based condition
    time_condition = EscrowCondition(
        condition_type=EscrowConditionType.TIME_BASED,
        description="Wait 5 seconds",
        duration_seconds=5,
        start_time=int(time.time()),
    )
    evaluator.add_condition(time_condition)
    print(f"   Added time condition: {time_condition.condition_id}")
    
    # Add value-based condition
    value_condition = EscrowCondition(
        condition_type=EscrowConditionType.EVENT_BASED,
        description="Delivery confirmed",
        target_value="delivered",
        comparison="equals",
    )
    evaluator.add_condition(value_condition)
    print(f"   Added value condition: {value_condition.condition_id}")
    
    # Check conditions
    print(f"\n9. Checking Conditions:")
    result = evaluator.check_all({
        value_condition.condition_id: "delivered",
    })
    print(f"   All Met: {result['all_met']}")
    print(f"   Time condition met: {result['results'][time_condition.condition_id]['met']}")
    print(f"   Value condition met: {result['results'][value_condition.condition_id]['met']}")
    
    # Wait and check again
    print(f"\n10. Waiting 5 seconds and checking again...")
    time.sleep(5.1)
    result = evaluator.check_all()
    print(f"   All Met: {result['all_met']}")
    
    print("\n" + "=" * 60)
    print("ESCROW MODELS READY FOR PRODUCTION")
    print("=" * 60)
