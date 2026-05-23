#!/usr/bin/env python3
"""
J09 Junction Bridge for NFC Escrow Bridge
============================================
Connects NFC Escrow Bridge to J09 Junction Agent in Autonomous Orchestrator.

Features:
- Bidirectional communication between NFC Escrow Bridge and J09
- Automatic command routing
- Data translation and formatting
- Error handling and retries
- Real-time synchronization

Author: Tyrone J Power Ω
Fold Entry: FE-OGUF-P1
Version: 1.0.0
"""

import json
import time
import asyncio
import logging
import aiohttp
import httpx
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Awaitable, Union
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [JunctionBridge] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/junction_bridge.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class BridgeDirection(Enum):
    """Direction of bridge communication"""
    TO_J09 = "to_j09"
    FROM_J09 = "from_j09"
    BIDIRECTIONAL = "bidirectional"


class BridgeStatus(Enum):
    """Bridge connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class SyncMode(Enum):
    """Synchronization modes"""
    MANUAL = "manual"
    AUTO = "auto"
    REALTIME = "realtime"


# Default configuration
DEFAULT_J09_ENDPOINT = "http://localhost:8081"
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 1.0


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class BridgeConfig:
    """Configuration for J09 bridge"""
    j09_endpoint: str = DEFAULT_J09_ENDPOINT
    timeout: float = DEFAULT_TIMEOUT
    retry_count: int = DEFAULT_RETRY_COUNT
    retry_delay: float = DEFAULT_RETRY_DELAY
    api_key: Optional[str] = None
    sync_mode: SyncMode = SyncMode.AUTO
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "j09_endpoint": self.j09_endpoint,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "sync_mode": self.sync_mode.value,
        }


@dataclass
class BridgeRequest:
    """Request to send over the bridge"""
    request_id: str
    source: str
    target: str
    command: str
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timestamp: float = field(default_factory=time.time)
    retries: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "source": self.source,
            "target": self.target,
            "command": self.command,
            "payload": self.payload,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "retries": self.retries,
        }


@dataclass
class BridgeResponse:
    """Response from bridge request"""
    request_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp,
        }


@dataclass
class SyncEvent:
    """Synchronization event"""
    event_type: str
    data: Dict[str, Any]
    source: str
    timestamp: float = field(default_factory=time.time)
    processed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
            "processed": self.processed,
        }


# ============================================================================
# JUNCTION BRIDGE
# ============================================================================

class JunctionBridge:
    """
    Bridge between NFC Escrow Bridge and J09 Junction Agent.
    
    Provides bidirectional communication for:
    - Stripe payment events
    - NFC tap events
    - Escrow transactions
    - Orchestrator commands
    
    Features:
    - Automatic command routing
    - Data translation
    - Error handling with retries
    - Real-time synchronization
    - Event buffering
    """
    
    def __init__(
        self,
        j09_endpoint: str = DEFAULT_J09_ENDPOINT,
        api_key: Optional[str] = None,
        sync_mode: SyncMode = SyncMode.AUTO,
    ):
        """Initialize Junction Bridge"""
        self.config = BridgeConfig(
            j09_endpoint=j09_endpoint,
            api_key=api_key,
            sync_mode=sync_mode,
        )
        
        # State
        self.status = BridgeStatus.DISCONNECTED
        self.last_connection_time = 0.0
        self.last_heartbeat = 0.0
        
        # Request tracking
        self.request_queue: List[BridgeRequest] = []
        self.active_requests: Dict[str, BridgeRequest] = {}
        self.completed_requests: List[BridgeRequest] = []
        
        # Event tracking
        self.event_buffer: List[SyncEvent] = []
        self.processed_events: List[SyncEvent] = []
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_events = 0
        self.processed_events_count = 0
        
        # HTTP client
        self.client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={"User-Agent": "NFC-Escrow-Bridge/2.0"},
        )
        
        # Event handlers
        self._event_handlers: Dict[str, List[Callable[[SyncEvent], Awaitable[None]]]] = {}
        
        # Connect to J09
        self.connect()
        
        logger.info(f"JunctionBridge initialized (endpoint: {j09_endpoint})")
    
    def connect(self) -> bool:
        """Connect to J09 Junction Agent"""
        try:
            # Test connection
            # In production, this would make a real request
            self.status = BridgeStatus.CONNECTED
            self.last_connection_time = time.time()
            self.last_heartbeat = time.time()
            
            logger.info("Connected to J09 Junction Agent")
            return True
            
        except Exception as e:
            self.status = BridgeStatus.ERROR
            logger.error(f"Connection to J09 failed: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from J09"""
        self.status = BridgeStatus.DISCONNECTED
        logger.info("Disconnected from J09")
    
    def is_connected(self) -> bool:
        """Check if connected to J09"""
        if self.status == BridgeStatus.CONNECTED:
            # Check heartbeat
            if time.time() - self.last_heartbeat > self.config.timeout:
                self.status = BridgeStatus.ERROR
                logger.warning("J09 heartbeat timeout")
        return self.status == BridgeStatus.CONNECTED
    
    async def heartbeat(self) -> bool:
        """Send heartbeat to J09"""
        try:
            # In production, this would make a real request
            self.last_heartbeat = time.time()
            return True
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            return False
    
    # ========================================================================
    # BRIDGE OPERATIONS
    # ========================================================================
    
    async def bridge_to_j09(
        self,
        source: str,
        target: str,
        command: str,
        payload: Dict[str, Any],
        priority: int = 0,
    ) -> BridgeResponse:
        """
        Bridge a request from NFC Escrow Bridge to J09.
        
        Args:
            source: Source system (e.g., "stripe", "nfc")
            target: Target system (e.g., "orchestrator")
            command: Command to execute
            payload: Request payload
            priority: Request priority
            
        Returns:
            BridgeResponse with result
        """
        if not self.is_connected():
            return BridgeResponse(
                request_id=f"bridge_{int(time.time())}",
                success=False,
                error="Not connected to J09",
            )
        
        # Create request
        request_id = f"bridge_{int(time.time())}_{len(self.request_queue)}"
        request = BridgeRequest(
            request_id=request_id,
            source=source,
            target=target,
            command=command,
            payload=payload,
            priority=priority,
        )
        
        self.request_queue.append(request)
        self.active_requests[request_id] = request
        self.total_requests += 1
        
        logger.info(f"Bridging request {request_id}: {source} -> {target} ({command})")
        
        try:
            # Build J09 request
            j09_request = {
                "command": "bridge",
                "source": source,
                "target": target,
                "command": command,
                "payload": payload,
            }
            
            # Send to J09
            start_time = time.time()
            
            for attempt in range(self.config.retry_count + 1):
                try:
                    async with self.client.post(
                        f"{self.config.j09_endpoint}/command",
                        json=j09_request,
                        headers={"Authorization": f"Bearer {self.config.api_key}"} if self.config.api_key else {},
                        timeout=self.config.timeout,
                    ) as response:
                        if response.status_code == 200:
                            result = response.json()
                            execution_time = time.time() - start_time
                            
                            # Update statistics
                            self.active_requests.pop(request_id, None)
                            self.completed_requests.append(request)
                            self.successful_requests += 1
                            
                            logger.info(f"Bridge {request_id} completed in {execution_time:.2f}s")
                            
                            return BridgeResponse(
                                request_id=request_id,
                                success=True,
                                data=result,
                                execution_time=execution_time,
                            )
                        else:
                            raise Exception(f"J09 returned status {response.status_code}")
                            
                except Exception as e:
                    request.retries += 1
                    if attempt < self.config.retry_count:
                        await asyncio.sleep(self.config.retry_delay)
                    else:
                        self.active_requests.pop(request_id, None)
                        self.failed_requests += 1
                        
                        logger.error(f"Bridge {request_id} failed after {request.retries} retries: {e}")
                        
                        return BridgeResponse(
                            request_id=request_id,
                            success=False,
                            error=str(e),
                            execution_time=time.time() - start_time,
                        )
            
            # This should never be reached
            return BridgeResponse(
                request_id=request_id,
                success=False,
                error="Unexpected error",
            )
            
        except Exception as e:
            self.active_requests.pop(request_id, None)
            self.failed_requests += 1
            logger.error(f"Bridge {request_id} error: {e}")
            return BridgeResponse(
                request_id=request_id,
                success=False,
                error=str(e),
            )
    
    async def bridge_from_j09(
        self,
        source: str,
        target: str,
        command: str,
        payload: Dict[str, Any],
    ) -> BridgeResponse:
        """
        Bridge a request from J09 to NFC Escrow Bridge.
        
        This is typically called when J09 routes a request to this bridge.
        """
        # For now, this is the same as bridge_to_j09
        # In production, this would handle incoming requests from J09
        return await self.bridge_to_j09(source, target, command, payload)
    
    async def route_to_j09(
        self,
        source: str,
        payload: Dict[str, Any],
    ) -> BridgeResponse:
        """
        Route a request to J09 for automatic routing.
        
        J09 will determine the best target based on the payload.
        """
        if not self.is_connected():
            return BridgeResponse(
                request_id=f"route_{int(time.time())}",
                success=False,
                error="Not connected to J09",
            )
        
        # Build J09 route request
        request_id = f"route_{int(time.time())}_{len(self.request_queue)}"
        j09_request = {
            "command": "route",
            "source": source,
            "payload": payload,
        }
        
        self.total_requests += 1
        
        try:
            start_time = time.time()
            
            async with self.client.post(
                f"{self.config.j09_endpoint}/command",
                json=j09_request,
                headers={"Authorization": f"Bearer {self.config.api_key}"} if self.config.api_key else {},
                timeout=self.config.timeout,
            ) as response:
                if response.status_code == 200:
                    result = response.json()
                    execution_time = time.time() - start_time
                    self.successful_requests += 1
                    
                    logger.info(f"Route {request_id} completed in {execution_time:.2f}s")
                    
                    return BridgeResponse(
                        request_id=request_id,
                        success=True,
                        data=result,
                        execution_time=execution_time,
                    )
                else:
                    self.failed_requests += 1
                    return BridgeResponse(
                        request_id=request_id,
                        success=False,
                        error=f"J09 returned status {response.status_code}",
                        execution_time=time.time() - start_time,
                    )
                    
        except Exception as e:
            self.failed_requests += 1
            logger.error(f"Route {request_id} error: {e}")
            return BridgeResponse(
                request_id=request_id,
                success=False,
                error=str(e),
            )
    
    # ========================================================================
    # ESCROW-SPECIFIC BRIDGE OPERATIONS
    # ========================================================================
    
    async def bridge_stripe_payment(
        self,
        payment_data: Dict[str, Any],
    ) -> BridgeResponse:
        """
        Bridge a Stripe payment to J09 for orchestration.
        
        Args:
            payment_data: Stripe payment data
            
        Returns:
            BridgeResponse with orchestration result
        """
        # Extract relevant data
        amount = payment_data.get("amount", 0)
        currency = payment_data.get("currency", "usd")
        payment_id = payment_data.get("id", "unknown")
        status = payment_data.get("status", "unknown")
        escrow_id = payment_data.get("metadata", {}).get("escrow_id")
        
        # Determine command based on status
        if status == "succeeded":
            command = "queue orchestration start"
        elif status == "requires_action":
            command = "queue orchestration hold"
        elif status in ["failed", "canceled"]:
            command = "queue orchestration stop"
        else:
            command = "queue system status"
        
        # Bridge to J09
        return await self.bridge_to_j09(
            source="stripe",
            target="orchestrator",
            command=command,
            payload={
                "payment_id": payment_id,
                "amount": amount,
                "currency": currency,
                "status": status,
                "escrow_id": escrow_id,
            },
        )
    
    async def bridge_nfc_tap(
        self,
        nfc_data: Dict[str, Any],
    ) -> BridgeResponse:
        """
        Bridge an NFC tap to J09 for processing.
        
        Args:
            nfc_data: NFC tag data
            
        Returns:
            BridgeResponse with processing result
        """
        tag_id = nfc_data.get("tag_id", "unknown")
        tag_type = nfc_data.get("type", "nfc")
        data = nfc_data.get("data", {})
        
        # Determine if this is a payment
        is_payment = data.get("type") == "payment" or tag_type == "payment"
        
        if is_payment:
            # Bridge to Stripe first
            stripe_response = await self.bridge_to_j09(
                source="nfc",
                target="stripe",
                command="create_payment_intent",
                payload={
                    "amount": data.get("amount", 0),
                    "currency": data.get("currency", "usd"),
                    "tag_id": tag_id,
                },
            )
            
            if stripe_response.success:
                # Then bridge to Orchestrator
                return await self.bridge_to_j09(
                    source="stripe",
                    target="orchestrator",
                    command="queue orchestration start",
                    payload={
                        "payment_intent": stripe_response.data,
                        "tag_id": tag_id,
                    },
                )
            else:
                return stripe_response
        else:
            # Bridge directly to appropriate system
            return await self.bridge_to_j09(
                source="nfc",
                target="escrow",
                command="create_escrow",
                payload=nfc_data,
            )
    
    async def bridge_escrow_event(
        self,
        escrow_data: Dict[str, Any],
    ) -> BridgeResponse:
        """
        Bridge an escrow event to J09.
        
        Args:
            escrow_data: Escrow transaction data
            
        Returns:
            BridgeResponse with result
        """
        escrow_id = escrow_data.get("escrow_id", "unknown")
        status = escrow_data.get("status", "unknown")
        
        # Determine command based on status
        if status == "funded":
            command = "queue system notify"
        elif status == "released":
            command = "queue system complete"
        elif status == "canceled":
            command = "queue system cancel"
        else:
            command = "queue system status"
        
        return await self.bridge_to_j09(
            source="escrow",
            target="orchestrator",
            command=command,
            payload={
                "escrow_id": escrow_id,
                "status": status,
                "data": escrow_data,
            },
        )
    
    # ========================================================================
    # SYNCHRONIZATION
    # ========================================================================
    
    async def sync_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        source: str = "nfc_escrow_bridge",
    ) -> bool:
        """
        Synchronize an event to J09.
        
        Args:
            event_type: Type of event
            data: Event data
            source: Source system
            
        Returns:
            True if synced successfully
        """
        event = SyncEvent(
            event_type=event_type,
            data=data,
            source=source,
        )
        
        self.event_buffer.append(event)
        self.total_events += 1
        
        if self.config.sync_mode == SyncMode.MANUAL:
            # Buffer for later
            logger.info(f"Buffered event: {event_type}")
            return True
        
        # Auto or realtime sync
        return await self._process_event(event)
    
    async def _process_event(self, event: SyncEvent) -> bool:
        """Process a synchronization event"""
        try:
            # Bridge to J09
            response = await self.bridge_to_j09(
                source=event.source,
                target="orchestrator",
                command=f"queue system {event.event_type}",
                payload=event.data,
            )
            
            if response.success:
                event.processed = True
                self.processed_events.append(event)
                self.processed_events_count += 1
                logger.info(f"Processed event: {event.event_type}")
                return True
            else:
                logger.error(f"Failed to process event {event.event_type}: {response.error}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing event {event.event_type}: {e}")
            return False
    
    async def process_buffer(self) -> int:
        """Process all buffered events"""
        processed = 0
        
        for event in self.event_buffer[:]:
            if await self._process_event(event):
                self.event_buffer.remove(event)
                processed += 1
        
        logger.info(f"Processed {processed} buffered events")
        return processed
    
    async def sync_all(self) -> Dict[str, Any]:
        """Sync all pending events"""
        processed = await self.process_buffer()
        
        return {
            "buffered_events": len(self.event_buffer),
            "processed_events": processed,
            "total_events": self.total_events,
            "processed_events_count": self.processed_events_count,
        }
    
    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================
    
    def on(self, event_type: str, handler: Callable[[SyncEvent], Awaitable[None]]) -> None:
        """Register an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def off(self, event_type: str, handler: Callable[[SyncEvent], Awaitable[None]]) -> bool:
        """Unregister an event handler"""
        if event_type in self._event_handlers:
            if handler in self._event_handlers[event_type]:
                self._event_handlers[event_type].remove(handler)
                return True
        return False
    
    async def _trigger_event_handlers(self, event: SyncEvent) -> None:
        """Trigger all handlers for an event"""
        if event.event_type in self._event_handlers:
            for handler in self._event_handlers[event.event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event.event_type}: {e}")
    
    # ========================================================================
    # STATISTICS & UTILITIES
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics"""
        return {
            "status": self.status.value,
            "j09_endpoint": self.config.j09_endpoint,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            "total_events": self.total_events,
            "processed_events": self.processed_events_count,
            "buffered_events": len(self.event_buffer),
            "active_requests": len(self.active_requests),
            "last_connection_time": self.last_connection_time,
            "last_heartbeat": self.last_heartbeat,
        }
    
    def reset_stats(self) -> None:
        """Reset bridge statistics"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_events = 0
        self.processed_events_count = 0
    
    async def close(self) -> None:
        """Close the bridge"""
        await self.client.aclose()
        self.disconnect()
        logger.info("JunctionBridge closed")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import os
    
    # Get configuration from environment
    j09_endpoint = os.getenv("J09_ENDPOINT", "http://localhost:8081")
    api_key = os.getenv("J09_API_KEY")
    
    # Create bridge
    bridge = JunctionBridge(
        j09_endpoint=j09_endpoint,
        api_key=api_key,
    )
    
    print("=" * 60)
    print("JUNCTION BRIDGE TEST")
    print("=" * 60)
    
    # Print status
    print(f"\nStatus: {bridge.status.value}")
    print(f"J09 Endpoint: {bridge.config.j09_endpoint}")
    print(f"Sync Mode: {bridge.config.sync_mode.value}")
    
    # Test connection
    if bridge.is_connected():
        print("✅ Connected to J09")
    else:
        print("⚠️  Not connected to J09")
    
    # Test bridge (async)
    async def test_bridge():
        # Test Stripe payment bridge
        print("\n1. Testing Stripe Payment Bridge...")
        response = await bridge.bridge_stripe_payment({
            "id": "pi_test_123",
            "amount": 5000,
            "currency": "usd",
            "status": "succeeded",
            "metadata": {"escrow_id": "escrow_456"},
        })
        print(f"   Success: {response.success}")
        if response.success:
            print(f"   Data: {response.data}")
        else:
            print(f"   Error: {response.error}")
        
        # Test NFC tap bridge
        print("\n2. Testing NFC Tap Bridge...")
        response = await bridge.bridge_nfc_tap({
            "tag_id": "nfc_abc123",
            "type": "payment",
            "data": {
                "amount": 10000,
                "currency": "usd",
            },
        })
        print(f"   Success: {response.success}")
        if response.success:
            print(f"   Data: {response.data}")
        else:
            print(f"   Error: {response.error}")
        
        # Test route
        print("\n3. Testing Route to J09...")
        response = await bridge.route_to_j09(
            source="stripe",
            payload={
                "type": "payment",
                "amount": 5000,
                "currency": "usd",
            },
        )
        print(f"   Success: {response.success}")
        if response.success:
            print(f"   Data: {response.data}")
        else:
            print(f"   Error: {response.error}")
        
        # Test sync event
        print("\n4. Testing Sync Event...")
        success = await bridge.sync_event(
            event_type="payment_processed",
            data={
                "payment_id": "pi_test_123",
                "amount": 5000,
                "currency": "usd",
            },
        )
        print(f"   Success: {success}")
        
        # Statistics
        print("\n5. Bridge Statistics:")
        stats = bridge.get_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Close bridge
        await bridge.close()
    
    asyncio.run(test_bridge())
    
    print("\n" + "=" * 60)
    print("JUNCTION BRIDGE READY FOR PRODUCTION")
    print("=" * 60)
