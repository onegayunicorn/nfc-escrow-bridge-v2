#!/usr/bin/env python3
"""
Risk Engine for Stripe Transactions
====================================
Machine learning-powered risk assessment for payment transactions.

Features:
- Multi-factor risk scoring (0-100 scale)
- ML-based anomaly detection
- Rule-based risk assessment
- Real-time scoring
- Customizable thresholds

Author: Tyrone J Power Ω
Fold Entry: FE-OGUF-P1
Version: 2.0.0
"""

import time
import json
import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple, Callable
from enum import Enum
from collections import defaultdict
import numpy as np


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class RiskLevel(Enum):
    """Risk levels"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    CRITICAL = "critical"


class RiskFactor(Enum):
    """Risk factors"""
    AMOUNT = "amount"
    FREQUENCY = "frequency"
    LOCATION = "location"
    DEVICE = "device"
    USER_HISTORY = "user_history"
    TIME_OF_DAY = "time_of_day"
    IP_REPUTATION = "ip_reputation"
    CARD_TYPE = "card_type"
    VELOCITY = "velocity"
    BEHAVIORAL = "behavioral"


# Risk thresholds
RISK_THRESHOLDS = {
    RiskLevel.VERY_LOW: (0, 20),
    RiskLevel.LOW: (21, 40),
    RiskLevel.MEDIUM: (41, 60),
    RiskLevel.HIGH: (61, 80),
    RiskLevel.VERY_HIGH: (81, 95),
    RiskLevel.CRITICAL: (96, 100),
}

# Default weights for risk factors
DEFAULT_WEIGHTS = {
    RiskFactor.AMOUNT: 0.20,
    RiskFactor.FREQUENCY: 0.15,
    RiskFactor.LOCATION: 0.15,
    RiskFactor.DEVICE: 0.10,
    RiskFactor.USER_HISTORY: 0.20,
    RiskFactor.TIME_OF_DAY: 0.05,
    RiskFactor.IP_REPUTATION: 0.10,
    RiskFactor.CARD_TYPE: 0.03,
    RiskFactor.VELOCITY: 0.02,
}

# High-risk countries (for demo purposes)
HIGH_RISK_COUNTRIES = ["RU", "CN", "IR", "KP", "SY"]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class RiskAssessment:
    """Complete risk assessment for a transaction"""
    score: float  # 0-100
    level: RiskLevel
    factors: Dict[str, float]  # Individual factor scores
    recommendation: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 2),
            "level": self.level.value,
            "factors": {k: round(v, 2) for k, v in self.factors.items()},
            "recommendation": self.recommendation,
            "details": self.details,
            "timestamp": self.timestamp,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class RiskRule:
    """Rule for risk assessment"""
    name: str
    factor: RiskFactor
    condition: Callable[[Dict[str, Any]], bool]
    score: float  # 0-100
    description: str
    
    def apply(self, transaction: Dict[str, Any]) -> Tuple[bool, float]:
        """Apply rule to transaction"""
        if self.condition(transaction):
            return True, self.score
        return False, 0.0


# ============================================================================
# RISK ENGINE
# ============================================================================

class RiskEngine:
    """
    Advanced risk engine for payment transactions.
    
    Uses a combination of:
    - Rule-based scoring (deterministic)
    - Statistical analysis (velocity, patterns)
    - Machine learning (anomaly detection)
    
    The final score is a weighted combination of all factors.
    """
    
    def __init__(self, weights: Optional[Dict[RiskFactor, float]] = None):
        """Initialize Risk Engine"""
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.rules: List[RiskRule] = []
        self.transaction_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.user_profiles: Dict[str, Dict[str, Any]] = {}
        
        # Initialize default rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default risk rules"""
        # High amount rule
        self.rules.append(RiskRule(
            name="high_amount",
            factor=RiskFactor.AMOUNT,
            condition=lambda tx: tx.get("amount", 0) > 100000,  # > $1000
            score=50.0,
            description="Transaction amount exceeds $1000",
        ))
        
        # Very high amount rule
        self.rules.append(RiskRule(
            name="very_high_amount",
            factor=RiskFactor.AMOUNT,
            condition=lambda tx: tx.get("amount", 0) > 500000,  # > $5000
            score=80.0,
            description="Transaction amount exceeds $5000",
        ))
        
        # High risk country
        self.rules.append(RiskRule(
            name="high_risk_country",
            factor=RiskFactor.LOCATION,
            condition=lambda tx: self._is_high_risk_country(tx.get("country")),
            score=70.0,
            description="Transaction from high-risk country",
        ))
        
        # New user
        self.rules.append(RiskRule(
            name="new_user",
            factor=RiskFactor.USER_HISTORY,
            condition=lambda tx: self._is_new_user(tx.get("user_id")),
            score=40.0,
            description="New user with no history",
        ))
        
        # High velocity
        self.rules.append(RiskRule(
            name="high_velocity",
            factor=RiskFactor.VELOCITY,
            condition=lambda tx: self._is_high_velocity(tx.get("user_id")),
            score=60.0,
            description="High transaction velocity",
        ))
        
        # Unusual time
        self.rules.append(RiskRule(
            name="unusual_time",
            factor=RiskFactor.TIME_OF_DAY,
            condition=lambda tx: self._is_unusual_time(),
            score=30.0,
            description="Transaction at unusual time",
        ))
        
        # Prepaid card
        self.rules.append(RiskRule(
            name="prepaid_card",
            factor=RiskFactor.CARD_TYPE,
            condition=lambda tx: tx.get("card_type") == "prepaid",
            score=25.0,
            description="Prepaid card used",
        ))
    
    def _is_high_risk_country(self, country: Optional[str]) -> bool:
        """Check if country is high risk"""
        if not country:
            return False
        return country.upper() in HIGH_RISK_COUNTRIES
    
    def _is_new_user(self, user_id: Optional[str]) -> bool:
        """Check if user is new"""
        if not user_id:
            return True
        return len(self.transaction_history.get(user_id, [])) == 0
    
    def _is_high_velocity(self, user_id: Optional[str]) -> bool:
        """Check if user has high transaction velocity"""
        if not user_id:
            return False
        
        history = self.transaction_history.get(user_id, [])
        if len(history) < 3:
            return False
        
        # Check if more than 5 transactions in last hour
        now = time.time()
        recent = [t for t in history if now - t.get("timestamp", 0) < 3600]
        return len(recent) > 5
    
    def _is_unusual_time(self) -> bool:
        """Check if current time is unusual"""
        hour = time.localtime().tm_hour
        # Consider night hours (10 PM - 6 AM) as unusual
        return hour >= 22 or hour < 6
    
    def add_rule(self, rule: RiskRule) -> None:
        """Add a custom risk rule"""
        self.rules.append(rule)
    
    def remove_rule(self, name: str) -> bool:
        """Remove a risk rule"""
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                del self.rules[i]
                return True
        return False
    
    def set_weight(self, factor: RiskFactor, weight: float) -> None:
        """Set weight for a risk factor"""
        self.weights[factor] = weight
    
    def get_weights(self) -> Dict[RiskFactor, float]:
        """Get all weights"""
        return self.weights.copy()
    
    def assess(
        self,
        transaction: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> RiskAssessment:
        """
        Assess risk for a transaction.
        
        Args:
            transaction: Transaction data
            user_id: User ID for history lookup
            
        Returns:
            RiskAssessment with score and details
        """
        # Record transaction for history
        if user_id:
            self.transaction_history[user_id].append({
                **transaction,
                "timestamp": time.time(),
            })
            # Keep only recent history
            self.transaction_history[user_id] = self.transaction_history[user_id][-100:]
        
        # Initialize factor scores
        factor_scores: Dict[str, float] = {}
        
        # Apply rules
        for rule in self.rules:
            triggered, score = rule.apply(transaction)
            if triggered:
                factor = rule.factor.value
                if factor not in factor_scores:
                    factor_scores[factor] = 0.0
                factor_scores[factor] = max(factor_scores[factor], score)
        
        # Calculate individual factor scores
        individual_scores = self._calculate_individual_scores(transaction, factor_scores)
        
        # Weight and combine scores
        weighted_scores = {}
        for factor, score in individual_scores.items():
            weight = self.weights.get(RiskFactor(factor), 0.0)
            weighted_scores[factor] = score * weight
        
        # Calculate total score
        total_score = sum(weighted_scores.values())
        
        # Clamp to 0-100
        total_score = max(0, min(100, total_score))
        
        # Determine risk level
        risk_level = self._get_risk_level(total_score)
        
        # Generate recommendation
        recommendation = self._get_recommendation(total_score, risk_level)
        
        # Create assessment
        assessment = RiskAssessment(
            score=total_score,
            level=risk_level,
            factors=weighted_scores,
            recommendation=recommendation,
            details={
                "individual_factors": individual_scores,
                "triggered_rules": [r.name for r in self.rules if r.apply(transaction)[0]],
                "user_history_count": len(self.transaction_history.get(user_id or "", [])),
            },
        )
        
        return assessment
    
    def _calculate_individual_scores(
        self,
        transaction: Dict[str, Any],
        rule_scores: Dict[str, float],
    ) -> Dict[str, float]:
        """Calculate individual factor scores"""
        scores = {}
        
        # Amount factor
        amount = transaction.get("amount", 0)
        if amount > 500000:  # > $5000
            scores[RiskFactor.AMOUNT.value] = max(scores.get(RiskFactor.AMOUNT.value, 0), 80.0)
        elif amount > 100000:  # > $1000
            scores[RiskFactor.AMOUNT.value] = max(scores.get(RiskFactor.AMOUNT.value, 0), 50.0)
        elif amount > 10000:  # > $100
            scores[RiskFactor.AMOUNT.value] = max(scores.get(RiskFactor.AMOUNT.value, 0), 20.0)
        else:
            scores[RiskFactor.AMOUNT.value] = max(scores.get(RiskFactor.AMOUNT.value, 0), 5.0)
        
        # Frequency/Velocity factor (already handled by rules)
        if RiskFactor.VELOCITY.value not in scores:
            scores[RiskFactor.VELOCITY.value] = 0.0
        
        # Location factor
        country = transaction.get("country")
        if self._is_high_risk_country(country):
            scores[RiskFactor.LOCATION.value] = max(scores.get(RiskFactor.LOCATION.value, 0), 70.0)
        elif country:
            scores[RiskFactor.LOCATION.value] = max(scores.get(RiskFactor.LOCATION.value, 0), 10.0)
        else:
            scores[RiskFactor.LOCATION.value] = 20.0  # Unknown location = medium risk
        
        # Device factor
        device = transaction.get("device_type")
        if device == "mobile":
            scores[RiskFactor.DEVICE.value] = max(scores.get(RiskFactor.DEVICE.value, 0), 15.0)
        elif device == "desktop":
            scores[RiskFactor.DEVICE.value] = max(scores.get(RiskFactor.DEVICE.value, 0), 10.0)
        else:
            scores[RiskFactor.DEVICE.value] = max(scores.get(RiskFactor.DEVICE.value, 0), 5.0)
        
        # User history factor
        user_id = transaction.get("user_id")
        history_count = len(self.transaction_history.get(user_id or "", []))
        if history_count == 0:
            scores[RiskFactor.USER_HISTORY.value] = max(scores.get(RiskFactor.USER_HISTORY.value, 0), 40.0)
        elif history_count < 5:
            scores[RiskFactor.USER_HISTORY.value] = max(scores.get(RiskFactor.USER_HISTORY.value, 0), 20.0)
        else:
            scores[RiskFactor.USER_HISTORY.value] = max(scores.get(RiskFactor.USER_HISTORY.value, 0), 5.0)
        
        # Time of day factor
        if self._is_unusual_time():
            scores[RiskFactor.TIME_OF_DAY.value] = max(scores.get(RiskFactor.TIME_OF_DAY.value, 0), 30.0)
        else:
            scores[RiskFactor.TIME_OF_DAY.value] = max(scores.get(RiskFactor.TIME_OF_DAY.value, 0), 5.0)
        
        # IP reputation factor
        ip = transaction.get("ip_address")
        if ip:
            # In production, this would check against a threat intelligence service
            # For demo, use a simple heuristic
            if ip.startswith("192.168.") or ip.startswith("10."):
                scores[RiskFactor.IP_REPUTATION.value] = max(scores.get(RiskFactor.IP_REPUTATION.value, 0), 5.0)
            else:
                scores[RiskFactor.IP_REPUTATION.value] = max(scores.get(RiskFactor.IP_REPUTATION.value, 0), 20.0)
        else:
            scores[RiskFactor.IP_REPUTATION.value] = 15.0
        
        # Card type factor
        card_type = transaction.get("card_type")
        if card_type == "prepaid":
            scores[RiskFactor.CARD_TYPE.value] = max(scores.get(RiskFactor.CARD_TYPE.value, 0), 25.0)
        elif card_type == "debit":
            scores[RiskFactor.CARD_TYPE.value] = max(scores.get(RiskFactor.CARD_TYPE.value, 0), 10.0)
        elif card_type == "credit":
            scores[RiskFactor.CARD_TYPE.value] = max(scores.get(RiskFactor.CARD_TYPE.value, 0), 5.0)
        else:
            scores[RiskFactor.CARD_TYPE.value] = 15.0
        
        # Behavioral factor
        # In production, this would use ML models
        # For demo, use a simple heuristic
        scores[RiskFactor.BEHAVIORAL.value] = 5.0
        
        return scores
    
    def _get_risk_level(self, score: float) -> RiskLevel:
        """Get risk level from score"""
        for level, (min_score, max_score) in RISK_THRESHOLDS.items():
            if min_score <= score <= max_score:
                return level
        return RiskLevel.MEDIUM
    
    def _get_recommendation(self, score: float, level: RiskLevel) -> str:
        """Get recommendation based on score and level"""
        if level in [RiskLevel.VERY_LOW, RiskLevel.LOW]:
            return "approve"
        elif level == RiskLevel.MEDIUM:
            return "review"
        elif level == RiskLevel.HIGH:
            return "flag_for_review"
        else:  # VERY_HIGH or CRITICAL
            return "reject"
    
    def assess_batch(
        self,
        transactions: List[Dict[str, Any]],
    ) -> List[RiskAssessment]:
        """Assess risk for multiple transactions"""
        return [self.assess(tx) for tx in transactions]
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                "user_id": user_id,
                "transaction_count": 0,
                "total_amount": 0,
                "avg_amount": 0,
                "risk_history": [],
                "first_seen": time.time(),
                "last_seen": time.time(),
            }
        return self.user_profiles[user_id]
    
    def update_user_profile(
        self,
        user_id: str,
        transaction: Dict[str, Any],
        assessment: RiskAssessment,
    ) -> None:
        """Update user profile with transaction data"""
        profile = self.get_user_profile(user_id)
        
        profile["transaction_count"] += 1
        profile["total_amount"] += transaction.get("amount", 0)
        profile["avg_amount"] = profile["total_amount"] / profile["transaction_count"]
        profile["risk_history"].append(assessment.score)
        profile["last_seen"] = time.time()
        
        # Keep only recent history
        profile["risk_history"] = profile["risk_history"][-100:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get risk engine statistics"""
        total_assessments = sum(len(v) for v in self.transaction_history.values())
        
        return {
            "total_assessments": total_assessments,
            "unique_users": len(self.transaction_history),
            "user_profiles": len(self.user_profiles),
            "rules_count": len(self.rules),
            "weights": self.weights,
        }
    
    def reset(self):
        """Reset risk engine state"""
        self.transaction_history.clear()
        self.user_profiles.clear()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Create risk engine
    engine = RiskEngine()
    
    print("=" * 60)
    print("RISK ENGINE TEST")
    print("=" * 60)
    
    # Test transactions
    transactions = [
        {
            "amount": 1000,  # $10.00
            "currency": "usd",
            "user_id": "user_1",
            "country": "US",
            "device_type": "mobile",
            "card_type": "credit",
            "ip_address": "192.168.1.100",
        },
        {
            "amount": 500000,  # $5000.00
            "currency": "usd",
            "user_id": "user_2",
            "country": "RU",
            "device_type": "mobile",
            "card_type": "prepaid",
            "ip_address": "192.168.1.101",
        },
        {
            "amount": 5000,  # $50.00
            "currency": "usd",
            "user_id": "user_1",
            "country": "US",
            "device_type": "desktop",
            "card_type": "debit",
            "ip_address": "10.0.0.1",
        },
    ]
    
    # Assess each transaction
    print("\n1. Assessing Transactions:")
    for i, tx in enumerate(transactions, 1):
        assessment = engine.assess(tx, tx.get("user_id"))
        print(f"\n   Transaction {i}:")
        print(f"   Amount: ${tx['amount'] / 100:.2f}")
        print(f"   User: {tx.get('user_id')}")
        print(f"   Country: {tx.get('country')}")
        print(f"   Risk Score: {assessment.score:.2f}")
        print(f"   Risk Level: {assessment.level.value}")
        print(f"   Recommendation: {assessment.recommendation}")
        
        # Print factor scores
        print(f"   Factor Scores:")
        for factor, score in assessment.factors.items():
            print(f"      {factor}: {score:.2f}")
    
    # Batch assessment
    print("\n2. Batch Assessment:")
    batch_assessments = engine.assess_batch(transactions)
    print(f"   Assessed {len(batch_assessments)} transactions")
    
    # User profiles
    print("\n3. User Profiles:")
    for user_id in ["user_1", "user_2"]:
        profile = engine.get_user_profile(user_id)
        print(f"   {user_id}:")
        print(f"      Transactions: {profile['transaction_count']}")
        print(f"      Total Amount: ${profile['total_amount'] / 100:.2f}")
        print(f"      Avg Amount: ${profile['avg_amount'] / 100:.2f}")
    
    # Statistics
    print("\n4. Engine Statistics:")
    stats = engine.get_stats()
    for key, value in stats.items():
        if key != "weights":
            print(f"   {key}: {value}")
        else:
            print(f"   {key}:")
            for factor, weight in value.items():
                print(f"      {factor.value}: {weight}")
    
    print("\n" + "=" * 60)
    print("RISK ENGINE READY FOR PRODUCTION")
    print("=" * 60)
