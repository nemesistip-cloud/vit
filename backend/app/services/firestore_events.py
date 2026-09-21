import logging
from sqlalchemy import event
from sqlalchemy.orm import Session
from app.db.models import Match, Prediction
from app.services.firestore_sync import sync_to_firestore, delete_from_firestore

logger = logging.getLogger(__name__)

def setup_firestore_events():
    """Register SQLAlchemy event listeners for Firestore synchronization."""

    @event.listens_for(Match, 'after_insert')
    def match_after_insert(mapper, connection, target):
        data = {
            "id": target.id,
            "home_team": target.home_team,
            "away_team": target.away_team,
            "league": target.league,
            "kickoff_time": target.kickoff_time.isoformat() if target.kickoff_time else None,
            "status": target.status,
            "home_goals": target.home_goals,
            "away_goals": target.away_goals,
            "actual_outcome": target.actual_outcome,
            "sport": target.sport,
            "updated_at": target.updated_at.isoformat() if target.updated_at else None,
        }
        sync_to_firestore("matches", str(target.id), data)

    @event.listens_for(Match, 'after_update')
    def match_after_update(mapper, connection, target):
        data = {
            "home_goals": target.home_goals,
            "away_goals": target.away_goals,
            "status": target.status,
            "actual_outcome": target.actual_outcome,
            "updated_at": target.updated_at.isoformat() if target.updated_at else None,
        }
        sync_to_firestore("matches", str(target.id), data)

    @event.listens_for(Match, 'after_delete')
    def match_after_delete(mapper, connection, target):
        delete_from_firestore("matches", str(target.id))

    @event.listens_for(Prediction, 'after_insert')
    def prediction_after_insert(mapper, connection, target):
        data = {
            "id": target.id,
            "match_id": target.match_id,
            "home_prob": target.home_prob,
            "draw_prob": target.draw_prob,
            "away_prob": target.away_prob,
            "confidence": target.confidence,
            "top_correct_score": target.top_correct_score,
            "top_cs_prob": target.top_cs_prob,
            "created_at": target.created_at.isoformat() if hasattr(target, 'created_at') and target.created_at else None,
        }
        sync_to_firestore("predictions", str(target.id), data)

    logger.info("Firestore SQLAlchemy event listeners registered")
