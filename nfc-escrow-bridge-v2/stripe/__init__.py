"""
Stripe Integration Layer for NFC Escrow Bridge
================================================
Universal bridge between NFC/Escrow and Stripe Terminal

This package provides:
- Payment simulation (simulate/)
- Transaction modeling (model/)
- Risk evaluation (evaluate/)
- Testing framework (test/)
- Request framing (frame/)

Author: Tyrone J Power Ω
Fold Entry: FE-OGUF-P1
Version: 2.0.0
"""

from .simulate import PaymentSimulator, TerminalMock
from .model import StripeTransaction, EscrowTransaction, TransactionModeler
from .evaluate import RiskEvaluator, FraudDetector
from .test import run_tests
from .frame import StripeFrameBuilder, WebhookHandler
from .client import StripeClient

__version__ = "2.0.0"
__all__ = [
    "PaymentSimulator",
    "TerminalMock",
    "StripeTransaction",
    "EscrowTransaction",
    "TransactionModeler",
    "RiskEvaluator",
    "FraudDetector",
    "run_tests",
    "StripeFrameBuilder",
    "WebhookHandler",
    "StripeClient",
]
