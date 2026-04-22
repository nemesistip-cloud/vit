"""Export endpoints — prediction history CSV/PDF and audit log CSV."""

import csv
import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Prediction, Match, AuditLog
from app.api.deps import get_current_user
from app.auth.dependencies import get_current_admin
from app.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exports", tags=["Exports"])


def _csv_stream(headers: list[str], rows: list[list]) -> StreamingResponse:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )


@router.get("/predictions/csv")
async def export_predictions_csv(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download personal prediction history as CSV."""
    preds = await db.execute(
        select(Prediction, Match)
        .join(Match, Prediction.match_id == Match.id, isouter=True)
        .where(Prediction.user_id == current_user.id)
        .order_by(Prediction.timestamp.desc())
        .limit(5000)
    )
    rows_raw = preds.all()

    headers = [
        "Prediction ID", "Match", "League", "Kickoff",
        "Bet Side", "Home Prob %", "Draw Prob %", "Away Prob %",
        "Over 2.5 Prob %", "BTTS Prob %",
        "Entry Odds", "Edge %", "Confidence %", "EV",
        "Recommended Stake", "Timestamp",
    ]

    rows = []
    for pred, match in rows_raw:
        match_name = f"{match.home_team} vs {match.away_team}" if match else "Unknown"
        rows.append([
            pred.id,
            match_name,
            match.league if match else "",
            match.kickoff_time.strftime("%Y-%m-%d %H:%M") if match and match.kickoff_time else "",
            pred.bet_side or "",
            round((pred.home_prob or 0) * 100, 1),
            round((pred.draw_prob or 0) * 100, 1),
            round((pred.away_prob or 0) * 100, 1),
            round((pred.over_25_prob or 0) * 100, 1),
            round((pred.btts_prob or 0) * 100, 1),
            pred.entry_odds or "",
            round((pred.vig_free_edge or 0) * 100, 2),
            round((pred.confidence or 0) * 100, 1),
            round(pred.final_ev or 0, 4),
            round(pred.recommended_stake or 0, 4),
            pred.timestamp.strftime("%Y-%m-%d %H:%M:%S") if pred.timestamp else "",
        ])

    response = _csv_stream(headers, rows)
    response.headers["Content-Disposition"] = "attachment; filename=predictions.csv"
    return response


@router.get("/predictions/pdf")
async def export_predictions_pdf(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download personal prediction history as PDF (falls back to CSV if PDF lib unavailable)."""
    try:
        from fpdf import FPDF

        preds = await db.execute(
            select(Prediction, Match)
            .join(Match, Prediction.match_id == Match.id, isouter=True)
            .where(Prediction.user_id == current_user.id)
            .order_by(Prediction.timestamp.desc())
            .limit(200)
        )
        rows_raw = preds.all()

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "VIT Network — Prediction History", ln=True, align="C")
        pdf.set_font("Helvetica", size=9)
        pdf.cell(0, 6, f"User: {current_user.username}   Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC", ln=True, align="C")
        pdf.ln(4)

        col_w = [50, 20, 20, 20, 20, 20, 25]
        headers = ["Match", "Side", "Odds", "Edge%", "Conf%", "EV", "Date"]
        pdf.set_font("Helvetica", "B", 8)
        for h, w in zip(headers, col_w):
            pdf.cell(w, 7, h, border=1)
        pdf.ln()

        pdf.set_font("Helvetica", size=7)
        for pred, match in rows_raw:
            match_name = (f"{match.home_team[:12]} v {match.away_team[:10]}" if match else "Unknown")
            pdf.cell(col_w[0], 6, match_name, border=1)
            pdf.cell(col_w[1], 6, (pred.bet_side or "")[:6], border=1)
            pdf.cell(col_w[2], 6, str(round(pred.entry_odds or 0, 2)), border=1)
            pdf.cell(col_w[3], 6, str(round((pred.vig_free_edge or 0) * 100, 1)), border=1)
            pdf.cell(col_w[4], 6, str(round((pred.confidence or 0) * 100, 0)), border=1)
            pdf.cell(col_w[5], 6, str(round(pred.final_ev or 0, 3)), border=1)
            ts = pred.timestamp.strftime("%m/%d %H:%M") if pred.timestamp else ""
            pdf.cell(col_w[6], 6, ts, border=1)
            pdf.ln()

        pdf_bytes = pdf.output()
        return StreamingResponse(
            iter([bytes(pdf_bytes)]),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=predictions.pdf"},
        )

    except ImportError:
        return await export_predictions_csv(current_user=current_user, db=db)


@router.get("/audit/csv")
async def export_audit_csv(
    limit: int = Query(1000, le=10000),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Admin: download audit log as CSV."""
    logs = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    records = logs.scalars().all()

    headers = ["ID", "Action", "Actor", "Resource", "Resource ID", "Status", "Created At"]
    rows = [
        [
            r.id,
            r.action,
            r.actor,
            r.resource or "",
            r.resource_id or "",
            r.status or "",
            r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
        ]
        for r in records
    ]

    response = _csv_stream(headers, rows)
    response.headers["Content-Disposition"] = "attachment; filename=audit_log.csv"
    return response
