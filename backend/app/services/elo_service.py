"""Puntuación ELO estilo FIDE para partidas multijugador (free-for-all).

El ganador gana puntos en función de la diferencia con cada rival:
ganar contra jugadores con más ELO otorga más puntos. El total repartido
se divide entre el número de rivales para que el sistema sea conservador
en mesas grandes (4-6 jugadores).

Requisitos de negocio cubiertos:
  - Ganar contra más ELO → más puntos.
  - Rangos: Hierro, Bronce, Plata, Oro, Platino, Diamante.
  - Las variaciones se aplican SOLO al confirmar la partida."""
from __future__ import annotations

from collections.abc import Mapping

from app.models.enums import Rank

K_FACTOR = 32          # Factor de crecimiento clásico de FIDE
BASE_RATING = 1200     # ELO inicial de cada temporada

# Umbral mínimo de ELO para cada rango (de mayor a menor)
RANK_THRESHOLDS: tuple[tuple[int, Rank], ...] = (
    (2000, Rank.DIAMANTE),
    (1800, Rank.PLATINO),
    (1600, Rank.ORO),
    (1400, Rank.PLATA),
    (1200, Rank.BRONCE),
    (0, Rank.HIERRO),
)


def expected_score(rating_a: float, rating_b: float) -> float:
    """Probabilidad de que A gane a B según la diferencia de ELO."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def compute_updates(
    ratings: Mapping[int, float],
    winner_id: int,
    k: int = K_FACTOR,
) -> dict[int, int]:
    """Devuelve {user_id: variación ELO} para una partida con un ganador.

    Args:
        ratings: ELO actual de cada participante {user_id: elo}.
        winner_id: user_id del ganador (debe estar en ratings).
    """
    if winner_id not in ratings:
        raise ValueError("El ganador debe estar entre los participantes")
    if len(ratings) < 2:
        return {user_id: 0 for user_id in ratings}

    n_opponents = len(ratings) - 1
    deltas: dict[int, float] = {user_id: 0.0 for user_id in ratings}
    winner_rating = ratings[winner_id]

    for opponent_id, opponent_rating in ratings.items():
        if opponent_id == winner_id:
            continue
        # Expectativa del ganador frente a este rival concreto
        exp_winner = expected_score(winner_rating, opponent_rating)
        # Repartimos K entre los rivales para no inflar tablas grandes
        deltas[winner_id] += k * (1.0 - exp_winner) / n_opponents
        deltas[opponent_id] += k * (0.0 - (1.0 - exp_winner)) / n_opponents

    return {user_id: int(round(delta)) for user_id, delta in deltas.items()}


def rank_for(rating: int) -> Rank:
    """Clasifica un valor de ELO en su rango."""
    for minimum, rank in RANK_THRESHOLDS:
        if rating >= minimum:
            return rank
    return Rank.HIERRO


def soft_reset(rating: int, base: int = BASE_RATING, factor: float = 0.5) -> int:
    """Soft reset de temporada: regresión hacia la media.

    Ejemplo (factor 0.5): 1600 -> 1400, 1200 -> 1200, 1000 -> 1100.
    Así se conserva cierta jerarquía sin arrastrar ventajas eternas."""
    return int(round(base + (rating - base) * factor))
