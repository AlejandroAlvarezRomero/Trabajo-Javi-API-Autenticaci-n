"""Catálogo de juegos del grupo con integración BoardGameGeek."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_group_role
from app.db.seed import seed_popular_games
from app.db.session import get_db
from app.models import Game, GroupMembership, Match, User
from app.models.enums import GroupRole
from app.schemas.game import BGGSearchResultOut, GameCreate, GameOut
from app.services import bgg_service
from app.services.bgg_service import BGGNotFoundError, BGGUnavailableError

router = APIRouter(prefix="/groups/{group_id}/games", tags=["Catálogo de juegos"])


@router.get("", response_model=list[GameOut], summary="Catálogo del grupo")
def list_games(
    group_id: int,
    db: Session = Depends(get_db),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> list[Game]:
    return list(
        db.scalars(
            select(Game).where(Game.group_id == group_id).order_by(Game.name.asc())
        ).all()
    )


@router.get(
    "/search",
    response_model=list[BGGSearchResultOut],
    summary="Buscar un juego en BoardGameGeek",
)
def search_bgg(
    group_id: int,
    query: str = Query(min_length=2, max_length=100),
    db: Session = Depends(get_db),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> list[BGGSearchResultOut]:
    try:
        results = bgg_service.search_games(query)
    except BGGNotFoundError:
        return []
    except BGGUnavailableError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return [BGGSearchResultOut(**r.__dict__) for r in results]


@router.post(
    "",
    response_model=GameOut,
    status_code=status.HTTP_201_CREATED,
    summary="Añadir juego al catálogo (Gestor) rellenando datos desde BGG",
)
def add_game(
    group_id: int,
    payload: GameCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _manager: GroupMembership = Depends(require_group_role(GroupRole.MANAGER)),
) -> Game:
    existing = db.scalar(
        select(Game.id).where(
            Game.group_id == group_id, Game.bgg_id == payload.bgg_id
        )
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ese juego ya está en el catálogo del grupo"
        )

    try:
        meta = bgg_service.fetch_game(payload.bgg_id)
    except BGGNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "El juego no existe en BoardGameGeek"
        ) from exc
    except BGGUnavailableError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    game = Game(
        group_id=group_id,
        bgg_id=meta.bgg_id,
        name=meta.name,
        description=meta.description,
        image_url=meta.image_url,
        thumbnail_url=meta.thumbnail_url,
        min_players=meta.min_players,
        max_players=meta.max_players,
        avg_playtime_minutes=meta.avg_playtime_minutes,
        year_published=meta.year_published,
        bgg_ranking=meta.bgg_ranking,
        bgg_rating=meta.bgg_rating,
        added_by_id=user.id,
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


@router.delete(
    "/{game_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Quitar juego del catálogo (Gestor)",
)
def remove_game(
    group_id: int,
    game_id: int,
    db: Session = Depends(get_db),
    _manager: GroupMembership = Depends(require_group_role(GroupRole.MANAGER)),
) -> None:
    game = db.get(Game, game_id)
    if game is None or game.group_id != group_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Juego no encontrado")
    used = db.scalar(select(Match.id).where(Match.game_id == game_id))
    if used is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede eliminar un juego con partidas registradas",
        )
    db.delete(game)
    db.commit()


@router.post(
    "/seed-popular",
    response_model=list[GameOut],
    status_code=status.HTTP_201_CREATED,
    summary="Precargar juegos populares en el catálogo del grupo (Gestor)",
)
def seed_popular_group_games(
    group_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _manager: GroupMembership = Depends(require_group_role(GroupRole.MANAGER)),
) -> list[Game]:
    return seed_popular_games(db, group_id=group_id, added_by_id=user.id)

