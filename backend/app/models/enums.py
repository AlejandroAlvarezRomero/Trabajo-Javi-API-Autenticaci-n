"""Enumeraciones compartidas: roles, estados de partida y rangos."""
from __future__ import annotations

from enum import Enum


class GlobalRole(str, Enum):
    """Roles globales de la plataforma (RBAC nivel 1 y 3)."""

    ADMIN = "ADMIN"      # Administrador Global
    PLAYER = "PLAYER"    # Jugador (cliente estándar)


class GroupRole(str, Enum):
    """Roles dentro de un grupo privado (RBAC nivel 2 y 3)."""

    MANAGER = "MANAGER"  # Gestor de Grupo / Game Master
    MEMBER = "MEMBER"    # Jugador


class MatchStatus(str, Enum):
    """Ciclo de vida de una partida registrada."""

    PENDING = "PENDING"      # A la espera de confirmación del resto de jugadores
    CONFIRMED = "CONFIRMED"  # Todos confirmaron: afecta a estadísticas y ELO
    REJECTED = "REJECTED"    # Algún jugador rechazó el resultado
    CANCELLED = "CANCELLED"  # Anulada por un Gestor de Grupo o Admin


class NotificationType(str, Enum):
    MATCH_CONFIRMATION = "MATCH_CONFIRMATION"    # "Confirma el resultado de X"
    MATCH_CONFIRMED = "MATCH_CONFIRMED"
    MATCH_REJECTED = "MATCH_REJECTED"
    GROUP_INVITE = "GROUP_INVITE"
    ACHIEVEMENT_UNLOCKED = "ACHIEVEMENT_UNLOCKED"
    SEASON_STARTED = "SEASON_STARTED"


class Rank(str, Enum):
    """Rangos por nivel de ELO (de menor a mayor)."""

    HIERRO = "HIERRO"
    BRONCE = "BRONCE"
    PLATA = "PLATA"
    ORO = "ORO"
    PLATINO = "PLATINO"
    DIAMANTE = "DIAMANTE"
