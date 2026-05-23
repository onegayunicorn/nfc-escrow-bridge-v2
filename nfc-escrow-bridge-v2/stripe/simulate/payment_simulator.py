#!/usr/bin/env python3
"""
Stripe Payment Simulator for NFC Escrow Bridge
==================================================
Simulates complete Stripe Terminal payment flows for testing and development.

Features:
- PaymentIntent simulation (create, confirm, cancel)
- Terminal handshake simulation (Verifone/BBPOS)
- Card tap simulation with configurable success rates
- NFC tag integration simulation
- Escrow-linked transaction simulation

Author: Tyrone J Power Ω
Fold Entry: FE-OGUF-P1
Version: 2.0.0
"""

import asyncio
import json
import random
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class TerminalStatus(Enum):
    """Stripe Terminal status"""
    IDLE = "idle"
    PROCESSING = "processing"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class PaymentStatus(Enum):
    """Payment status"""
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    REQUIRES_ACTION = "requires_action"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class CardBrand(Enum):
    """Card brands"""
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"
    DISCOVER = "discover"
    DINERS = "diners_club"
    JCB = "jcb"
    UNION_PAY = "union_pay"


# Default configuration
DEFAULT_SUCCESS_RATE = 0.98  # 98% success rate
DEFAULT_PROCESSING_TIME = (0.05, 0.3)  # 50-300ms
DEFAULT_TERMINAL_ID = "tmr_sim_" + secrets.token_hex(4)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class MockCard:
    """Mock credit/debit card"""
    brand: CardBrand
    last4: str
    exp_month: int
    exp_year: int
    cvc: str
    name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand": self.brand.value,
            "last4": self.last4,
            "exp_month": self.exp_month,
            "exp_year": self.exp_year,
            "cvc": self.cvc,
            "name": self.name,
        }


@dataclass
class MockPaymentMethod:
    """Mock Stripe payment method"""
    id: str
    type: str = "card"
    card: Optional[MockCard] = None
    billing_details: Optional[Dict[str, Any]] = None
    created: int = field(default_factory=lambda: int(time.time()))
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "type": self.type,
            "created": self.created,
        }
        if self.card:
            result["card"] = self.card.to_dict()
        if self.billing_details:
            result["billing_details"] = self.billing_details
        return result


@dataclass
class MockPaymentIntent:
    """Mock Stripe PaymentIntent"""
    id: str
    amount: int
    currency: str
    status: PaymentStatus
    payment_method: Optional[str] = None
    customer: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created: int = field(default_factory=lambda: int(time.time()))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "object": "payment_intent",
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status.value,
            "payment_method": self.payment_method,
            "customer": self.customer,
            "description": self.description,
            "metadata": self.metadata,
            "created": self.created,
        }


@dataclass
class MockTerminal:
    """Mock Stripe Terminal device"""
    id: str
    device_type: str
    status: TerminalStatus
    serial_number: str
    label: str
    location: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "device_type": self.device_type,
            "status": self.status.value,
            "serial_number": self.serial_number,
            "label": self.label,
            "location": self.location,
        }


# ============================================================================
# PAYMENT SIMULATOR
# ============================================================================

class PaymentSimulator:
    """
    Simulates Stripe payment flows for testing and development.
    
    Features:
    - Create and confirm PaymentIntents
    - Simulate terminal handshakes
    - Simulate card taps and NFC payments
    - Configurable success rates and processing times
    - Escrow-linked transaction simulation
    """
    
    def __init__(
        self,
        success_rate: float = DEFAULT_SUCCESS_RATE,
        processing_time_range: Tuple[float, float] = DEFAULT_PROCESSING_TIME,
        terminal_id: Optional[str] = None,
    ):
        """Initialize Payment Simulator"""
        self.success_rate = success_rate
        self.processing_time_range = processing_time_range
        self.terminal_id = terminal_id or DEFAULT_TERMINAL_ID
        
        # Terminal state
        self.terminal_status = TerminalStatus.IDLE
        self.connected_terminal: Optional[MockTerminal] = None
        
        # Payment methods
        self.payment_methods: Dict[str, MockPaymentMethod] = {}
        self.payment_intents: Dict[str, MockPaymentIntent] = {}
        self.customers: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self.total_payments = 0
        self.successful_payments = 0
        self.failed_payments = 0
        self.total_amount = 0
        
        # Initialize with some test data
        self._initialize_test_data()
    
    def _initialize_test_data(self):
        """Initialize with test payment methods and customers"""
        # Test payment methods
        self._create_payment_method(
            card=MockCard(
                brand=CardBrand.VISA,
                last4="4242",
                exp_month=12,
                exp_year=2026,
                cvc="123",
                name="Test Card",
            )
        )
        
        self._create_payment_method(
            card=MockCard(
                brand=CardBrand.MASTERCARD,
                last4="2223",
                exp_month=6,
                exp_year=2025,
                cvc="456",
            )
        )
        
        self._create_payment_method(
            card=MockCard(
                brand=CardBrand.AMEX,
                last4="1234",
                exp_month=9,
                exp_year=2027,
                cvc="7894",
            )
        )
        
        # Test customers
        self._create_customer(
            email="test@example.com",
            name="Test Customer",
            metadata={"test": True},
        )
    
    def _generate_id(self, prefix: str = "pi") -> str:
        """Generate a mock ID"""
        return f"{prefix}_{secrets.token_hex(12)}"
    
    def _simulate_processing_delay(self):
        """Simulate payment processing delay"""
        delay = random.uniform(*self.processing_time_range)
        time.sleep(delay)
    
    def _should_succeed(self) -> bool:
        """Determine if payment should succeed"""
        return random.random() < self.success_rate
    
    # ========================================================================
    # PAYMENT INTENT OPERATIONS
    # ========================================================================
    
    def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        payment_method: Optional[str] = None,
        customer: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        escrow_id: Optional[str] = None,
        **kwargs,
    ) -> MockPaymentIntent:
        """
        Create a mock PaymentIntent.
        
        Args:
            amount: Amount in cents
            currency: Currency code (default: usd)
            payment_method: Payment method ID (optional)
            customer: Customer ID (optional)
            description: Description (optional)
            metadata: Metadata (optional)
            escrow_id: Escrow ID to link (optional)
            **kwargs: Additional parameters
            
        Returns:
            MockPaymentIntent
        """
        intent_id = self._generate_id()
        
        # Set default payment method if not provided
        if not payment_method:
            payment_method = list(self.payment_methods.keys())[0]
        
        # Set default customer if not provided
        if not customer:
            customer = list(self.customers.keys())[0] if self.customers else None
        
        # Add escrow ID to metadata
        if escrow_id:
            if not metadata:
                metadata = {}
            metadata["escrow_id"] = escrow_id
        
        # Create intent with initial status
        intent = MockPaymentIntent(
            id=intent_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.REQUIRES_PAYMENT_METHOD,
            payment_method=payment_method,
            customer=customer,
            description=description,
            metadata=metadata or {},
        )
        
        self.payment_intents[intent_id] = intent
        self.total_payments += 1
        self.total_amount += amount
        
        return intent
    
    def confirm_payment_intent(
        self,
        intent_id: str,
        payment_method: Optional[str] = None,
        **kwargs,
    ) -> MockPaymentIntent:
        """
        Confirm a mock PaymentIntent.
        
        Args:
            intent_id: PaymentIntent ID
            payment_method: Payment method ID (optional)
            **kwargs: Additional parameters
            
        Returns:
            MockPaymentIntent with updated status
        """
        if intent_id not in self.payment_intents:
            raise ValueError(f"PaymentIntent {intent_id} not found")
        
        intent = self.payment_intents[intent_id]
        
        # Update payment method if provided
        if payment_method:
            intent.payment_method = payment_method
        
        # Simulate processing
        self._simulate_processing_delay()
        
        # Determine success
        if self._should_succeed():
            intent.status = PaymentStatus.SUCCEEDED
            self.successful_payments += 1
        else:
            # Random failure mode
            failure_modes = [
                PaymentStatus.REQUIRES_PAYMENT_METHOD,
                PaymentStatus.REQUIRES_ACTION,
                PaymentStatus.CANCELED,
            ]
            intent.status = random.choice(failure_modes)
            self.failed_payments += 1
        
        return intent
    
    def cancel_payment_intent(self, intent_id: str) -> MockPaymentIntent:
        """Cancel a mock PaymentIntent."""
        if intent_id not in self.payment_intents:
            raise ValueError(f"PaymentIntent {intent_id} not found")
        
        intent = self.payment_intents[intent_id]
        intent.status = PaymentStatus.CANCELED
        self.failed_payments += 1
        
        return intent
    
    def retrieve_payment_intent(self, intent_id: str) -> Optional[MockPaymentIntent]:
        """Retrieve a mock PaymentIntent."""
        return self.payment_intents.get(intent_id)
    
    def list_payment_intents(self, limit: int = 10) -> List[MockPaymentIntent]:
        """List recent PaymentIntents."""
        return list(self.payment_intents.values())[-limit:]
    
    # ========================================================================
    # PAYMENT METHOD OPERATIONS
    # ========================================================================
    
    def create_payment_method(
        self,
        card: Optional[MockCard] = None,
        type: str = "card",
        **kwargs,
    ) -> MockPaymentMethod:
        """Create a mock payment method."""
        pm_id = self._generate_id("pm")
        
        pm = MockPaymentMethod(
            id=pm_id,
            type=type,
            card=card,
            billing_details=kwargs.get("billing_details"),
        )
        
        self.payment_methods[pm_id] = pm
        return pm
    
    def retrieve_payment_method(self, pm_id: str) -> Optional[MockPaymentMethod]:
        """Retrieve a mock payment method."""
        return self.payment_methods.get(pm_id)
    
    def list_payment_methods(self, limit: int = 10) -> List[MockPaymentMethod]:
        """List recent payment methods."""
        return list(self.payment_methods.values())[-limit:]
    
    # ========================================================================
    # CUSTOMER OPERATIONS
    # ========================================================================
    
    def create_customer(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """Create a mock customer."""
        customer_id = self._generate_id("cus")
        
        customer = {
            "id": customer_id,
            "email": email or f"test_{self._generate_id()[:8]}@example.com",
            "name": name or "Test Customer",
            "description": description,
            "metadata": metadata or {},
            "created": int(time.time()),
        }
        customer.update(kwargs)
        
        self.customers[customer_id] = customer
        return customer_id
    
    def retrieve_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a mock customer."""
        return self.customers.get(customer_id)
    
    def list_customers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent customers."""
        return list(self.customers.values())[-limit:]
    
    # ========================================================================
    # TERMINAL OPERATIONS
    # ========================================================================
    
    def create_terminal(
        self,
        device_type: str = "verifone_p400",
        label: str = "Test Terminal",
        location: Optional[str] = None,
    ) -> MockTerminal:
        """Create a mock terminal."""
        terminal_id = self._generate_id("tmr")
        
        terminal = MockTerminal(
            id=terminal_id,
            device_type=device_type,
            status=TerminalStatus.IDLE,
            serial_number=f"SN_{secrets.token_hex(6)}",
            label=label,
            location=location,
        )
        
        self.connected_terminal = terminal
        self.terminal_id = terminal_id
        self.terminal_status = terminal.status
        
        return terminal
    
    def connect_terminal(self, terminal_id: Optional[str] = None) -> bool:
        """Connect to a terminal."""
        if terminal_id:
            # In real implementation, would connect to specific terminal
            self.terminal_id = terminal_id
        
        if not self.connected_terminal:
            self.connected_terminal = self.create_terminal()
        
        self.connected_terminal.status = TerminalStatus.CONNECTED
        self.terminal_status = TerminalStatus.CONNECTED
        return True
    
    def disconnect_terminal(self) -> bool:
        """Disconnect from terminal."""
        if self.connected_terminal:
            self.connected_terminal.status = TerminalStatus.DISCONNECTED
            self.terminal_status = TerminalStatus.DISCONNECTED
            return True
        return False
    
    def get_terminal_status(self) -> TerminalStatus:
        """Get current terminal status."""
        return self.terminal_status
    
    # ========================================================================
    # NFC-SPECIFIC SIMULATIONS
    # ========================================================================
    
    def simulate_nfc_tap(
        self,
        amount: int,
        currency: str = "usd",
        tag_id: Optional[str] = None,
        **kwargs,
    ) -> MockPaymentIntent:
        """
        Simulate an NFC tap payment.
        
        This simulates a user tapping an NFC card/phone on a Stripe Terminal
        to make a payment that will be linked to an escrow transaction.
        """
        # Generate tag ID if not provided
        if not tag_id:
            tag_id = f"nfc_{secrets.token_hex(6)}"
        
        # Create payment intent with NFC metadata
        intent = self.create_payment_intent(
            amount=amount,
            currency=currency,
            metadata={
                "nfc": True,
                "tag_id": tag_id,
                "source": "nfc_tap",
                **kwargs.get("metadata", {}),
            },
        )
        
        # Simulate terminal interaction
        self.connect_terminal()
        self._simulate_processing_delay()
        
        # Auto-confirm for NFC (in real scenario, would wait for terminal)
        intent = self.confirm_payment_intent(intent.id)
        
        return intent
    
    def simulate_nfc_escrow_flow(
        self,
        amount: int,
        currency: str = "usd",
        escrow_id: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Simulate complete NFC → Escrow → Stripe flow.
        
        Returns a dictionary with all components of the flow.
        """
        if not escrow_id:
            escrow_id = f"escrow_{secrets.token_hex(8)}"
        
        # Step 1: NFC Tap
        nfc_result = self.simulate_nfc_tap(
            amount=amount,
            currency=currency,
            tag_id=kwargs.get("tag_id"),
        )
        
        # Step 2: Create Escrow record
        escrow_record = {
            "escrow_id": escrow_id,
            "status": "pending",
            "amount": amount,
            "currency": currency,
            "payment_intent_id": nfc_result.id,
            "created": int(time.time()),
        }
        
        # Step 3: Link to Stripe
        if nfc_result.status == PaymentStatus.SUCCEEDED:
            escrow_record["status"] = "funded"
        
        return {
            "nfc_tap": {
                "tag_id": kwargs.get("tag_id", f"nfc_{secrets.token_hex(6)}"),
                "amount": amount,
                "currency": currency,
            },
            "payment_intent": nfc_result.to_dict(),
            "escrow": escrow_record,
            "status": nfc_result.status.value,
            "success": nfc_result.status == PaymentStatus.SUCCEEDED,
        }
    
    # ========================================================================
    # STATISTICS & STATUS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get simulator statistics."""
        return {
            "total_payments": self.total_payments,
            "successful_payments": self.successful_payments,
            "failed_payments": self.failed_payments,
            "success_rate": self.successful_payments / self.total_payments if self.total_payments > 0 else 0,
            "total_amount": self.total_amount,
            "total_amount_usd": self.total_amount / 100,
            "payment_intents": len(self.payment_intents),
            "payment_methods": len(self.payment_methods),
            "customers": len(self.customers),
            "terminal_id": self.terminal_id,
            "terminal_status": self.terminal_status.value,
        }
    
    def reset(self):
        """Reset simulator state."""
        self.payment_intents.clear()
        self.payment_methods.clear()
        self.customers.clear()
        self.total_payments = 0
        self.successful_payments = 0
        self.failed_payments = 0
        self.total_amount = 0
        self.connected_terminal = None
        self.terminal_status = TerminalStatus.IDLE
        
        # Re-initialize test data
        self._initialize_test_data()


# ============================================================================
# TERMINAL MOCK
# ============================================================================

class TerminalMock:
    """
    Mock Stripe Terminal device (Verifone P400, BBPOS Chipper, etc.)
    
    Simulates terminal behavior for testing without physical hardware.
    """
    
    def __init__(self, device_type: str = "verifone_p400"):
        """Initialize terminal mock"""
        self.device_type = device_type
        self.terminal_id = f"tmr_mock_{secrets.token_hex(4)}"
        self.serial_number = f"SN_{secrets.token_hex(6)}"
        self.status = TerminalStatus.IDLE
        self.connected = False
        self.last_command = None
        self.last_response = None
        
        # Device capabilities
        self.capabilities = [
            "card_present",
            "chip_card",
            "contactless",
            "nfc",
        ]
    
    def connect(self) -> bool:
        """Simulate terminal connection."""
        self.status = TerminalStatus.CONNECTED
        self.connected = True
        return True
    
    def disconnect(self) -> bool:
        """Simulate terminal disconnection."""
        self.status = TerminalStatus.DISCONNECTED
        self.connected = False
        return True
    
    def handshake(self) -> Dict[str, Any]:
        """Simulate terminal handshake."""
        if not self.connected:
            self.connect()
        
        self.last_command = "handshake"
        self.last_response = {
            "status": "success",
            "terminal_id": self.terminal_id,
            "device_type": self.device_type,
            "serial_number": self.serial_number,
            "capabilities": self.capabilities,
            "timestamp": int(time.time()),
        }
        
        return self.last_response
    
    def process_payment(
        self,
        amount: int,
        currency: str = "usd",
        **kwargs,
    ) -> Dict[str, Any]:
        """Simulate payment processing on terminal."""
        if not self.connected:
            return {"status": "error", "error": "Terminal not connected"}
        
        self.last_command = "process_payment"
        
        # Simulate processing
        time.sleep(random.uniform(0.1, 0.5))
        
        # Random success/failure
        success = random.random() < 0.95  # 95% success rate
        
        if success:
            self.last_response = {
                "status": "success",
                "amount": amount,
                "currency": currency,
                "payment_intent_id": f"pi_{secrets.token_hex(12)}",
                "timestamp": int(time.time()),
            }
        else:
            self.last_response = {
                "status": "error",
                "error": random.choice([
                    "card_declined",
                    "timeout",
                    "connection_error",
                    "invalid_amount",
                ]),
                "timestamp": int(time.time()),
            }
        
        return self.last_response
    
    def read_card(self) -> Dict[str, Any]:
        """Simulate card read."""
        if not self.connected:
            return {"status": "error", "error": "Terminal not connected"}
        
        self.last_command = "read_card"
        
        # Generate random card data
        brands = [b.value for b in CardBrand]
        brand = random.choice(brands)
        
        self.last_response = {
            "status": "success",
            "card": {
                "brand": brand,
                "last4": secrets.token_hex(2).upper(),
                "exp_month": random.randint(1, 12),
                "exp_year": random.randint(2024, 2030),
                "cvc": secrets.token_hex(2),
            },
            "payment_method_id": f"pm_{secrets.token_hex(12)}",
            "timestamp": int(time.time()),
        }
        
        return self.last_response
    
    def get_status(self) -> Dict[str, Any]:
        """Get terminal status."""
        return {
            "terminal_id": self.terminal_id,
            "device_type": self.device_type,
            "serial_number": self.serial_number,
            "status": self.status.value,
            "connected": self.connected,
            "capabilities": self.capabilities,
            "last_command": self.last_command,
        }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Create simulator
    simulator = PaymentSimulator()
    
    print("=" * 60)
    print("STRIPE PAYMENT SIMULATOR")
    print("=" * 60)
    
    # Test payment intent flow
    print("\n1. Creating PaymentIntent...")
    intent = simulator.create_payment_intent(
        amount=1000,
        currency="usd",
        escrow_id="escrow_1234",
    )
    print(f"   Created: {intent.id} (${intent.amount / 100:.2f})")
    
    # Confirm payment
    print("\n2. Confirming PaymentIntent...")
    confirmed = simulator.confirm_payment_intent(intent.id)
    print(f"   Status: {confirmed.status.value}")
    print(f"   Result: {'✅ SUCCESS' if confirmed.status == PaymentStatus.SUCCEEDED else '❌ FAILED'}")
    
    # NFC tap simulation
    print("\n3. Simulating NFC Tap...")
    nfc_result = simulator.simulate_nfc_tap(
        amount=2000,
        currency="usd",
        tag_id="nfc_abc123",
    )
    print(f"   NFC Tap: {nfc_result.id}")
    print(f"   Status: {nfc_result.status.value}")
    
    # Full flow
    print("\n4. Simulating NFC-Escrow-Stripe Flow...")
    flow = simulator.simulate_nfc_escrow_flow(
        amount=5000,
        currency="usd",
        escrow_id="escrow_5678",
    )
    print(f"   NFC Tap: {flow['nfc_tap']['tag_id']}")
    print(f"   Payment Intent: {flow['payment_intent']['id']}")
    print(f"   Escrow: {flow['escrow']['escrow_id']}")
    print(f"   Status: {flow['status']}")
    
    # Terminal simulation
    print("\n5. Terminal Simulation...")
    terminal = TerminalMock()
    terminal.connect()
    handshake = terminal.handshake()
    print(f"   Handshake: {handshake['status']}")
    print(f"   Terminal: {handshake['terminal_id']}")
    
    # Statistics
    print("\n6. Simulator Statistics:")
    stats = simulator.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("SIMULATOR READY FOR INTEGRATION")
    print("=" * 60)
