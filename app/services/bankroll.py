# app/services/bankroll.py
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.models import BankrollState

logger = logging.getLogger(__name__)


@dataclass
class Bankroll:
    """Bankroll state tracker"""
    initial_balance: float = 10000.0
    current_balance: float = 10000.0
    peak_balance: float = 10000.0
    total_staked: float = 0.0
    total_profit: float = 0.0
    total_bets: int = 0
    winning_bets: int = 0
    losing_bets: int = 0
    
    @property
    def roi(self) -> float:
        """Return on investment"""
        if self.total_staked == 0:
            return 0.0
        return self.total_profit / self.total_staked
    
    @property
    def win_rate(self) -> float:
        """Win rate percentage"""
        if self.total_bets == 0:
            return 0.0
        return self.winning_bets / self.total_bets
    
    @property
    def drawdown(self) -> float:
        """Current drawdown from peak"""
        if self.peak_balance == 0:
            return 0.0
        return (self.peak_balance - self.current_balance) / self.peak_balance
    
    @property
    def kelly_fraction(self) -> float:
        """Current Kelly fraction based on performance"""
        if self.total_bets < 50:
            return 0.02  # Conservative for small sample
        
        # Simplified Kelly calculation
        win_prob = self.win_rate
        avg_odds = 2.0  # Would need actual tracking
        b = avg_odds - 1
        kelly = (b * win_prob - (1 - win_prob)) / b
        return max(0.01, min(kelly, 0.10))
    
    def update_bet(self, stake: float, odds: float, won: bool):
        """Update bankroll after bet"""
        self.total_bets += 1
        self.total_staked += stake
        
        if won:
            profit = stake * (odds - 1)
            self.winning_bets += 1
        else:
            profit = -stake
            self.losing_bets += 1
        
        self.current_balance += profit
        self.total_profit += profit
        
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        logger.info(f"Bankroll update: balance={self.current_balance:.2f}, "
                   f"drawdown={self.drawdown:.2%}, roi={self.roi:.2%}")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "initial_balance": self.initial_balance,
            "current_balance": self.current_balance,
            "peak_balance": self.peak_balance,
            "total_staked": self.total_staked,
            "total_profit": self.total_profit,
            "total_bets": self.total_bets,
            "winning_bets": self.winning_bets,
            "losing_bets": self.losing_bets,
            "roi": self.roi,
            "win_rate": self.win_rate,
            "drawdown": self.drawdown,
            "kelly_fraction": self.kelly_fraction
        }


class BankrollManager:
    """Manage bankroll across the system"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bankroll = Bankroll()
    
    async def load_state(self):
        """Load bankroll state from database"""
        result = await self.db.execute(select(BankrollState).order_by(BankrollState.id.desc()).limit(1))
        state = result.scalar_one_or_none()
        
        if state:
            self.bankroll.initial_balance = state.initial_balance
            self.bankroll.current_balance = state.current_balance
            self.bankroll.peak_balance = state.peak_balance
            self.bankroll.total_staked = state.total_staked
            self.bankroll.total_profit = state.total_profit
            self.bankroll.total_bets = state.total_bets
            self.bankroll.winning_bets = state.winning_bets
            self.bankroll.losing_bets = state.losing_bets
    
    async def save_state(self):
        """Save bankroll state to database"""
        state = BankrollState(
            initial_balance=self.bankroll.initial_balance,
            current_balance=self.bankroll.current_balance,
            peak_balance=self.bankroll.peak_balance,
            total_staked=self.bankroll.total_staked,
            total_profit=self.bankroll.total_profit,
            total_bets=self.bankroll.total_bets,
            winning_bets=self.bankroll.winning_bets,
            losing_bets=self.bankroll.losing_bets,
            updated_at=datetime.now(timezone.utc)
        )
        self.db.add(state)
        await self.db.commit()
    
    def calculate_stake(self, edge: float, confidence: float) -> float:
        """Calculate recommended stake based on bankroll and edge"""
        if edge < 0.02:  # Minimum edge threshold
            return 0.0
        
        if self.bankroll.drawdown > 0.15:  # Drawdown protection
            return 0.0
        
        # Kelly-based stake with bankroll consideration
        kelly = self.bankroll.kelly_fraction
        stake_percentage = kelly * (edge / 0.05)  # Scale by edge
        stake_percentage = min(stake_percentage, 0.05)  # Cap at 5%
        
        return stake_percentage * self.bankroll.current_balance