"""Motor de logros: evalúa insignias tras cada partida CONFIRMED.

Las reglas viven en `Achievement.condition` (JSON), p.ej.:
  {"type": "first_win_with_game"}
  {"type": "win_streak", "streak": 5}
  {"type": "games_played", "threshold": 10}
Se desbloquean una sola vez por usuario (y grupo, si el logro es de grupo)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Achievement, Match, MatchParticipant, Notification, UserAchievement
from app.models.enums import MatchStatus, NotificationType
from app.services.event_service import publish_user_event


def _unlock(db: Session, code: str, user_id: int, group_id: int | None) -> None:
    achievement = db.scalar(select(Achievement).where(Achievement.code == code))
    if achievement is None:
        return  # semilla ausente: no fallar la partida por un logro

    already = db.scalar(
        select(UserAchievement.id).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement.id,
            UserAchievement.group_id == group_id,
        )
    )
    if already is not None:
        return

    db.add(
        UserAchievement(
            user_id=user_id,
            achievement_id=achievement.id,
            group_id=group_id,
        )
    )
    db.add(
        Notification(
            user_id=user_id,
            type=NotificationType.ACHIEVEMENT_UNLOCKED.value,
            title=f"Insignia desbloqueada: {achievement.name}",
            body=achievement.description,
            link=f"/achievements/{achievement.code}",
        )
    )
    publish_user_event(
        user_id,
        {
            "type": NotificationType.ACHIEVEMENT_UNLOCKED.value,
            "title": f"Insignia desbloqueada: {achievement.name}",
            "body": achievement.description,
            "link": f"/achievements/{achievement.code}",
        },
    )


def _confirmed_games(db: Session, user_id: int, group_id: int) -> int:
    return (
        db.scalar(
            select(func.count(MatchParticipant.id))
            .join(Match, Match.id == MatchParticipant.match_id)
            .where(
                MatchParticipant.user_id == user_id,
                Match.group_id == group_id,
                Match.status == MatchStatus.CONFIRMED.value,
            )
        )
        or 0
    )


def _wins_with_game(db: Session, user_id: int, group_id: int, game_id: int) -> int:
    return (
        db.scalar(
            select(func.count(Match.id)).where(
                Match.group_id == group_id,
                Match.game_id == game_id,
                Match.winner_id == user_id,
                Match.status == MatchStatus.CONFIRMED.value,
            )
        )
        or 0
    )


def _current_win_streak(db: Session, user_id: int, group_id: int) -> int:
    """Racha de victorias confirmadas más recientes del usuario en el grupo."""
    matches = db.scalars(
        select(Match)
        .join(MatchParticipant, MatchParticipant.match_id == Match.id)
        .where(
            MatchParticipant.user_id == user_id,
            Match.group_id == group_id,
            Match.status == MatchStatus.CONFIRMED.value,
        )
        .order_by(Match.verified_at.desc(), Match.id.desc())
        .limit(50)
    ).all()
    streak = 0
    for match in matches:
        if match.winner_id == user_id:
            streak += 1
        else:
            break
    return streak


def evaluate(db: Session, match: Match) -> None:
    """Evalúa los logros de cada participante tras confirmar la partida.
    No hace commit: lo gestiona el llamante (match_service._apply_results)."""
    if match.status != MatchStatus.CONFIRMED.value:
        return

    for participant in match.participants:
        user_id = participant.user_id

        # Partidas jugadas en el grupo
        total_games = _confirmed_games(db, user_id, match.group_id)
        for threshold in (10, 50):
            if total_games >= threshold:
                _unlock(db, f"GAMES_{threshold}", user_id, match.group_id)

        if user_id != match.winner_id:
            continue

        # Primera sangre: primera victoria con ese juego
        if _wins_with_game(db, user_id, match.group_id, match.game_id) <= 1:
            _unlock(db, "FIRST_BLOOD", user_id, match.group_id)

        # Racha de victorias
        streak = _current_win_streak(db, user_id, match.group_id)
        if streak >= 5:
            _unlock(db, "WIN_STREAK_5", user_id, match.group_id)
