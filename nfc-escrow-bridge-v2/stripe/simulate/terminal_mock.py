#!/usr/bin/env python3
"""
Stripe Terminal Mock for NFC Escrow Bridge
==========================================
Simulates Verifone P400, BBPOS Chipper, and other Stripe Terminal devices.

Features:
- Terminal connection/disconnection simulation
- Card tap/insert/swipe simulation
- Payment processing simulation
- NFC tag reading simulation
- Error condition simulation

Author: Tyrone J Power Ω
Fold Entry: FE-OGUF-P1
Version: 2.0.0
"""

import asyncio
import random
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Awaitable
from enum import Enum
from datetime import datetime


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class TerminalType(Enum):
    """Supported terminal types"""
    VERIFONE_P400 = "verifone_p400"
    BBPOS_CHIPPER = "bbpos_chipper2x"
    BBPOS_CHIPPER_PLUS = "bbpos_chipper_plus"
    STRIPE_S700 = "stripe_s700"
    CUSTOM = "custom"


class TerminalStatus(Enum):
    """Terminal connection status"""
    OFFLINE = "offline"
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    PROCESSING = "processing"
    ERROR = "error"
    UPDATE_AVAILABLE = "update_available"


class CardInterface(Enum):
    """Card interface types"""
    CONTACT = "contact"  # Chip card inserted
    CONTACTLESS = "contactless"  # NFC tap
    MAGSTRIPE = "magstripe"  # Swipe
    MANUAL = "manual"  # Manual entry


class TerminalError(Enum):
    """Terminal error types"""
    CONNECTION_FAILED = "connection_failed"
    TIMEOUT = "timeout"
    CARD_DECLINED = "card_declined"
    INVALID_AMOUNT = "invalid_amount"
    TERMINAL_BUSY = "terminal_busy"
    CARD_REMOVED = "card_removed"
    UNSUPPORTED_CARD = "unsupported_card"
    PIN_REQUIRED = "pin_required"


# Default configuration
DEFAULT_TERMINAL_TYPES = [
    TerminalType.VERIFONE_P400,
    TerminalType.BBPOS_CHIPPER,
]
DEFAULT_PROCESSING_TIME = (0.1, 0.5)  # 100-500ms
DEFAULT_SUCCESS_RATE = 0.95  # 95% success rate


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TerminalConfig:
    """Terminal configuration"""
    terminal_id: str
    device_type: TerminalType
    label: str
    serial_number: str
    location_id: Optional[str] = None
    status: TerminalStatus = TerminalStatus.OFFLINE
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "terminal_id": self.terminal_id,
            "device_type": self.device_type.value,
            "label": self.label,
            "serial_number": self.serial_number,
            "location_id": self.location_id,
            "status": self.status.value,
        }


@dataclass
class CardData:
    """Card data from terminal"""
    last4: str
    brand: str
    exp_month: int
    exp_year: int
    interface: CardInterface
    emv_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "last4": self.last4,
            "brand": self.brand,
            "exp_month": self.exp_month,
            "exp_year": self.exp_year,
            "interface": self.interface.value,
        }
        if self.emv_data:
            result["emv_data"] = self.emv_data
        return result


@dataclass
class TerminalResponse:
    """Terminal response"""
    success: bool
    status: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "status": self.status,
            "timestamp": self.timestamp,
        }
        if self.data:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        if self.error_code:
            result["error_code"] = self.error_code
        return result


# ============================================================================
# TERMINAL MOCK
# ============================================================================

class TerminalMock:
    """
    Mock Stripe Terminal device for testing without physical hardware.
    
    Supports:
    - Verifone P400
    - BBPOS Chipper 2x/Plus
    - Stripe S700
    - Custom terminals
    
    Features:
    - Connection/disconnection simulation
    - Card present operations
    - Contactless/NFC payments
    - Error condition simulation
    - Realistic timing and behavior
    """
    
    def __init__(
        self,
        device_type: TerminalType = TerminalType.VERIFONE_P400,
        label: str = "Test Terminal",
        location_id: Optional[str] = None,
    ):
        """Initialize terminal mock"""
        self.device_type = device_type
        self.label = label
        self.location_id = location_id
        self.terminal_id = f"tmr_{secrets.token_hex(6)}"
        self.serial_number = f"SN_{device_type.value}_{secrets.token_hex(4)}"
        
        # State
        self.status = TerminalStatus.OFFLINE
        self.connected = False
        self.busy = False
        
        # Capabilities based on device type
        self.capabilities = self._get_capabilities()
        
        # Last operation
        self.last_command: Optional[str] = None
        self.last_response: Optional[TerminalResponse] = None
        self.last_card: Optional[CardData] = None
        
        # Statistics
        self.total_operations = 0
        self.successful_operations = 0
        self.failed_operations = 0
        
        # Event handlers
        self._event_handlers: Dict[str, List[Callable[[TerminalResponse], Awaitable[None]]]] = {}
    
    def _get_capabilities(self) -> List[str]:
        """Get capabilities based on device type"""
        base_capabilities = ["card_present", "chip_card"]
        
        if self.device_type in [TerminalType.VERIFONE_P400, TerminalType.BBPOS_CHIPPER_PLUS]:
            base_capabilities.extend(["contactless", "nfc", "magstripe"])
        elif self.device_type == TerminalType.BBPOS_CHIPPER:
            base_capabilities.extend(["contactless"])
        
        return base_capabilities
    
    # ========================================================================
    # CONNECTION MANAGEMENT
    # ========================================================================
    
    async def connect(self, timeout: float = 10.0) -> TerminalResponse:
        """Simulate terminal connection."""
        if self.connected:
            return TerminalResponse(
                success=True,
                status="already_connected",
                data={"terminal_id": self.terminal_id},
            )
        
        self.last_command = "connect"
        
        # Simulate connection delay
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Random connection success
        success = random.random() < 0.98  # 98% success rate
        
        if success:
            self.status = TerminalStatus.CONNECTED
            self.connected = True
            self.total_operations += 1
            self.successful_operations += 1
            
            response = TerminalResponse(
                success=True,
                status="connected",
                data={
                    "terminal_id": self.terminal_id,
                    "device_type": self.device_type.value,
                    "serial_number": self.serial_number,
                    "label": self.label,
                    "capabilities": self.capabilities,
                },
            )
        else:
            self.status = TerminalStatus.ERROR
            self.total_operations += 1
            self.failed_operations += 1
            
            response = TerminalResponse(
                success=False,
                status="connection_failed",
                error="Failed to connect to terminal",
                error_code=TerminalError.CONNECTION_FAILED.value,
            )
        
        self.last_response = response
        await self._trigger_event("connect", response)
        return response
    
    async def disconnect(self) -> TerminalResponse:
        """Simulate terminal disconnection."""
        if not self.connected:
            return TerminalResponse(
                success=True,
                status="already_disconnected",
            )
        
        self.last_command = "disconnect"
        
        self.status = TerminalStatus.OFFLINE
        self.connected = False
        self.busy = False
        self.total_operations += 1
        self.successful_operations += 1
        
        response = TerminalResponse(
            success=True,
            status="disconnected",
            data={"terminal_id": self.terminal_id},
        )
        
        self.last_response = response
        await self._trigger_event("disconnect", response)
        return response
    
    async def get_status(self) -> TerminalResponse:
        """Get terminal status."""
        self.last_command = "status"
        
        response = TerminalResponse(
            success=True,
            status="status",
            data={
                "terminal_id": self.terminal_id,
                "device_type": self.device_type.value,
                "serial_number": self.serial_number,
                "label": self.label,
                "location_id": self.location_id,
                "status": self.status.value,
                "connected": self.connected,
                "busy": self.busy,
                "capabilities": self.capabilities,
            },
        )
        
        self.last_response = response
        return response
    
    # ========================================================================
    # CARD OPERATIONS
    # ========================================================================
    
    async def read_card(
        self,
        timeout: float = 30.0,
        cancel_on: Optional[List[str]] = None,
    ) -> TerminalResponse:
        """
        Simulate reading a card from the terminal.
        
        Args:
            timeout: Timeout in seconds
            cancel_on: List of events that cancel the read (e.g., ["card_removed"])
            
        Returns:
            TerminalResponse with card data
        """
        if not self.connected:
            return TerminalResponse(
                success=False,
                status="error",
                error="Terminal not connected",
                error_code=TerminalError.CONNECTION_FAILED.value,
            )
        
        if self.busy:
            return TerminalResponse(
                success=False,
                status="error",
                error="Terminal is busy",
                error_code=TerminalError.TERMINAL_BUSY.value,
            )
        
        self.last_command = "read_card"
        self.busy = True
        
        # Simulate card insertion delay
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Random interface type
        interface = random.choice(list(CardInterface))
        
        # Generate card data
        brands = ["visa", "mastercard", "amex", "discover", "diners_club", "jcb"]
        brand = random.choice(brands)
        
        card = CardData(
            last4=secrets.token_hex(2).upper(),
            brand=brand,
            exp_month=random.randint(1, 12),
            exp_year=random.randint(2024, 2030),
            interface=interface,
            emv_data={"aid": secrets.token_hex(4), "tvr": secrets.token_hex(4)},
        )
        
        self.last_card = card
        self.busy = False
        self.total_operations += 1
        self.successful_operations += 1
        
        response = TerminalResponse(
            success=True,
            status="card_read",
            data={
                "card": card.to_dict(),
                "payment_method_id": f"pm_{secrets.token_hex(12)}",
                "interface": interface.value,
            },
        )
        
        self.last_response = response
        await self._trigger_event("card_read", response)
        return response
    
    async def process_payment(
        self,
        amount: int,
        currency: str = "usd",
        payment_intent_id: Optional[str] = None,
        customer: Optional[str] = None,
        **kwargs,
    ) -> TerminalResponse:
        """
        Simulate payment processing on the terminal.
        
        Args:
            amount: Amount in cents
            currency: Currency code
            payment_intent_id: PaymentIntent ID (optional)
            customer: Customer ID (optional)
            **kwargs: Additional parameters
            
        Returns:
            TerminalResponse with payment result
        """
        if not self.connected:
            return TerminalResponse(
                success=False,
                status="error",
                error="Terminal not connected",
                error_code=TerminalError.CONNECTION_FAILED.value,
            )
        
        if self.busy:
            return TerminalResponse(
                success=False,
                status="error",
                error="Terminal is busy",
                error_code=TerminalError.TERMINAL_BUSY.value,
            )
        
        self.last_command = "process_payment"
        self.busy = True
        
        # Simulate processing delay
        await asyncio.sleep(random.uniform(*DEFAULT_PROCESSING_TIME))
        
        # Determine success
        success = random.random() < DEFAULT_SUCCESS_RATE
        
        if success:
            self.total_operations += 1
            self.successful_operations += 1
            
            response = TerminalResponse(
                success=True,
                status="payment_success",
                data={
                    "amount": amount,
                    "currency": currency,
                    "payment_intent_id": payment_intent_id or f"pi_{secrets.token_hex(12)}",
                    "customer": customer,
                    "timestamp": int(time.time()),
                },
            )
        else:
            self.total_operations += 1
            self.failed_operations += 1
            
            # Random error
            error = random.choice(list(TerminalError))
            
            response = TerminalResponse(
                success=False,
                status="payment_failed",
                error=error.value.replace("_", " ").title(),
                error_code=error.value,
            )
        
        self.busy = False
        self.last_response = response
        await self._trigger_event("payment_processed", response)
        return response
    
    async def cancel(self) -> TerminalResponse:
        """Cancel the current operation."""
        if not self.busy:
            return TerminalResponse(
                success=True,
                status="no_operation",
                data={"message": "No operation to cancel"},
            )
        
        self.last_command = "cancel"
        self.busy = False
        self.total_operations += 1
        self.failed_operations += 1
        
        response = TerminalResponse(
            success=True,
            status="cancelled",
            data={"message": "Operation cancelled"},
        )
        
        self.last_response = response
        await self._trigger_event("cancelled", response)
        return response
    
    # ========================================================================
    # NFC OPERATIONS
    # ========================================================================
    
    async def read_nfc_tag(
        self,
        timeout: float = 30.0,
        **kwargs,
    ) -> TerminalResponse:
        """
        Simulate reading an NFC tag.
        
        This simulates a user tapping an NFC card/phone on the terminal.
        """
        if not self.connected:
            return TerminalResponse(
                success=False,
                status="error",
                error="Terminal not connected",
                error_code=TerminalError.CONNECTION_FAILED.value,
            )
        
        if self.busy:
            return TerminalResponse(
                success=False,
                status="error",
                error="Terminal is busy",
                error_code=TerminalError.TERMINAL_BUSY.value,
            )
        
        # Check if terminal supports NFC
        if "nfc" not in self.capabilities and "contactless" not in self.capabilities:
            return TerminalResponse(
                success=False,
                status="error",
                error="Terminal does not support NFC",
                error_code=TerminalError.UNSUPPORTED_CARD.value,
            )
        
        self.last_command = "read_nfc_tag"
        self.busy = True
        
        # Simulate NFC tap delay (faster than chip)
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Generate NFC tag data
        tag_id = f"nfc_{secrets.token_hex(6)}"
        
        # Random card brand
        brands = ["visa", "mastercard", "amex", "discover"]
        brand = random.choice(brands)
        
        nfc_data = {
            "tag_id": tag_id,
            "type": "nfc",
            "card": {
                "brand": brand,
                "last4": secrets.token_hex(2).upper(),
                "exp_month": random.randint(1, 12),
                "exp_year": random.randint(2024, 2030),
            },
            "payment_method_id": f"pm_{secrets.token_hex(12)}",
            "timestamp": int(time.time()),
        }
        
        # Add any additional kwargs to NFC data
        nfc_data.update(kwargs)
        
        self.busy = False
        self.total_operations += 1
        self.successful_operations += 1
        
        response = TerminalResponse(
            success=True,
            status="nfc_read",
            data=nfc_data,
        )
        
        self.last_response = response
        await self._trigger_event("nfc_read", response)
        return response
    
    async def process_nfc_payment(
        self,
        amount: int,
        currency: str = "usd",
        **kwargs,
    ) -> TerminalResponse:
        """
        Simulate NFC payment processing.
        
        This combines reading an NFC tag and processing a payment.
        """
        # First read the NFC tag
        nfc_response = await self.read_nfc_tag(**kwargs)
        
        if not nfc_response.success:
            return nfc_response
        
        # Then process payment with the card from NFC
        payment_response = await self.process_payment(
            amount=amount,
            currency=currency,
            **kwargs,
        )
        
        if payment_response.success:
            # Combine data
            combined_data = {
                **nfc_response.data,
                **payment_response.data,
            }
            
            return TerminalResponse(
                success=True,
                status="nfc_payment_success",
                data=combined_data,
            )
        else:
            return payment_response
    
    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================
    
    def on(self, event: str, handler: Callable[[TerminalResponse], Awaitable[None]]):
        """Register an event handler."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    def off(self, event: str, handler: Callable[[TerminalResponse], Awaitable[None]]):
        """Unregister an event handler."""
        if event in self._event_handlers:
            if handler in self._event_handlers[event]:
                self._event_handlers[event].remove(handler)
    
    async def _trigger_event(self, event: str, response: TerminalResponse):
        """Trigger all handlers for an event."""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                await handler(response)
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get terminal statistics."""
        return {
            "terminal_id": self.terminal_id,
            "device_type": self.device_type.value,
            "label": self.label,
            "status": self.status.value,
            "connected": self.connected,
            "busy": self.busy,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.successful_operations / self.total_operations if self.total_operations > 0 else 0,
            "capabilities": self.capabilities,
        }
    
    def reset(self):
        """Reset terminal state."""
        self.status = TerminalStatus.OFFLINE
        self.connected = False
        self.busy = False
        self.total_operations = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.last_command = None
        self.last_response = None
        self.last_card = None


# ============================================================================
# TERMINAL FACTORY
# ============================================================================

class TerminalFactory:
    """Factory for creating terminal mocks."""
    
    @staticmethod
    def create(
        device_type: TerminalType = TerminalType.VERIFONE_P400,
        label: str = "Test Terminal",
        location_id: Optional[str] = None,
    ) -> TerminalMock:
        """Create a terminal mock."""
        return TerminalMock(
            device_type=device_type,
            label=label,
            location_id=location_id,
        )
    
    @staticmethod
    def create_verifone_p400(label: str = "Verifone P400") -> TerminalMock:
        """Create a Verifone P400 terminal mock."""
        return TerminalMock(
            device_type=TerminalType.VERIFONE_P400,
            label=label,
        )
    
    @staticmethod
    def create_bbpos_chipper(label: str = "BBPOS Chipper") -> TerminalMock:
        """Create a BBPOS Chipper terminal mock."""
        return TerminalMock(
            device_type=TerminalType.BBPOS_CHIPPER,
            label=label,
        )


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    async def main():
        # Create terminal
        terminal = TerminalFactory.create_verifone_p400()
        
        print("=" * 60)
        print("STRIPE TERMINAL MOCK (Verifone P400)")
        print("=" * 60)
        
        # Connect
        print("\n1. Connecting to terminal...")
        connect_resp = await terminal.connect()
        print(f"   Status: {connect_resp.status}")
        print(f"   Terminal: {connect_resp.data['terminal_id']}")
        
        # Read card
        print("\n2. Reading card...")
        card_resp = await terminal.read_card()
        print(f"   Status: {card_resp.status}")
        print(f"   Card: {card_resp.data['card']['brand'].upper()} ****{card_resp.data['card']['last4']}")
        
        # Process payment
        print("\n3. Processing payment ($50.00)...")
        payment_resp = await terminal.process_payment(amount=5000, currency="usd")
        print(f"   Status: {payment_resp.status}")
        if payment_resp.success:
            print(f"   Payment Intent: {payment_resp.data['payment_intent_id']}")
        else:
            print(f"   Error: {payment_resp.error}")
        
        # NFC tap
        print("\n4. NFC Tap simulation...")
        nfc_resp = await terminal.read_nfc_tag()
        print(f"   Status: {nfc_resp.status}")
        print(f"   Tag: {nfc_resp.data['tag_id']}")
        print(f"   Card: {nfc_resp.data['card']['brand'].upper()}")
        
        # NFC payment
        print("\n5. NFC Payment ($25.00)...")
        nfc_payment_resp = await terminal.process_nfc_payment(amount=2500, currency="usd")
        print(f"   Status: {nfc_payment_resp.status}")
        if nfc_payment_resp.success:
            print(f"   Amount: ${nfc_payment_resp.data['amount'] / 100:.2f}")
            print(f"   Payment Intent: {nfc_payment_resp.data['payment_intent_id']}")
        
        # Disconnect
        print("\n6. Disconnecting...")
        disconnect_resp = await terminal.disconnect()
        print(f"   Status: {disconnect_resp.status}")
        
        # Statistics
        print("\n7. Terminal Statistics:")
        stats = terminal.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n" + "=" * 60)
        print("TERMINAL MOCK READY FOR INTEGRATION")
        print("=" * 60)
    
    asyncio.run(main())
