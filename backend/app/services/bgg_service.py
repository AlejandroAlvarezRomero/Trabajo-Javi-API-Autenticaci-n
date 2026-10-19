"""Integración con la API pública de BoardGameGeek (xmlapi2).

Endpoints usados:
  GET /search?query=...&type=boardgame   -> búsqueda de juegos
  GET /thing?id=X&stats=1                -> metadatos completos de un juego

BGG responde 202 (en cola) bajo carga; se reintenta antes de fallar."""
from __future__ import annotations

import html
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx

from app.core.config import settings

_MAX_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 1.5
_USER_AGENT = "BoardGameTracker/1.0 (FastAPI backend)"


class BGGError(Exception):
    """Error base de la integración con BGG."""


class BGGNotFoundError(BGGError):
    """El juego no existe en BoardGameGeek."""


class BGGUnavailableError(BGGError):
    """BGG no respondió (caído, en cola o con error 5xx)."""


@dataclass
class BGGGameMetadata:
    bgg_id: int
    name: str
    description: str | None = None
    image_url: str | None = None
    thumbnail_url: str | None = None
    min_players: int | None = None
    max_players: int | None = None
    avg_playtime_minutes: int | None = None
    year_published: int | None = None
    bgg_ranking: int | None = None
    bgg_rating: float | None = None


@dataclass
class BGGSearchItem:
    bgg_id: int
    name: str
    year_published: int | None = None


def _request(path: str, params: dict) -> ET.Element:
    """GET a BGG con reintentos ante el 202 (solicitud en cola)."""
    url = f"{settings.BGG_API_BASE}{path}"
    for attempt in range(_MAX_ATTEMPTS):
        try:
            with httpx.Client(
                timeout=15.0, headers={"User-Agent": _USER_AGENT}
            ) as client:
                response = client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise BGGUnavailableError("No se pudo contactar con BoardGameGeek") from exc

        if response.status_code == 202 and attempt < _MAX_ATTEMPTS - 1:
            time.sleep(_RETRY_DELAY_SECONDS)  # BGG encola peticiones bajo carga
            continue
        if response.status_code == 202:
            raise BGGUnavailableError("BoardGameGeek no respondió (solicitud en cola)")
        if response.status_code == 404:
            raise BGGNotFoundError("Recurso no encontrado en BoardGameGeek")
        if response.status_code >= 500:
            raise BGGUnavailableError(
                f"BoardGameGeek devolvió error {response.status_code}"
            )
        try:
            return ET.fromstring(response.content)
        except ET.ParseError as exc:
            raise BGGUnavailableError("Respuesta inválida de BoardGameGeek") from exc
    raise BGGUnavailableError("BoardGameGeek no respondió")


def _to_int(raw: str | None) -> int | None:
    try:
        return int(raw) if raw is not None else None
    except ValueError:
        return None


def _to_float(raw: str | None) -> float | None:
    try:
        return float(raw) if raw is not None else None
    except ValueError:
        return None


def _clean_description(raw: str | None) -> str | None:
    """BGG devuelve HTML en la descripción: se desescapa y se limpian las etiquetas."""
    if not raw:
        return None
    text = html.unescape(raw)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:2500] or None


def fetch_game(bgg_id: int) -> BGGGameMetadata:
    """Metadatos de un juego (portada, jugadores, duración, año, rank...)."""
    root = _request("/thing", {"id": bgg_id, "stats": 1})
    item = root.find("item")
    if item is None:
        raise BGGNotFoundError(f"No existe el juego con id {bgg_id}")

    name_el = item.find("name[@type='primary']")
    if name_el is None:
        name_el = item.find("name")
    name = (
        name_el.get("value")
        if name_el is not None
        else f"Juego BGG #{bgg_id}"
    )

    min_el = item.find("minplayers")
    max_el = item.find("maxplayers")
    playtime_el = item.find("playingtime")
    year_el = item.find("yearpublished")

    ranking: int | None = None
    rating: float | None = None
    stats = item.find("statistics")
    if stats is not None:
        rank_el = stats.find(".//rank[@type='boardgame']")
        if rank_el is not None:
            ranking = _to_int(rank_el.get("value"))
        average_el = stats.find("ratings/bayesaverage")
        if average_el is None:
            average_el = stats.find("bayesaverage")
        if average_el is not None:
            rating = _to_float(average_el.get("value"))

    # Nota: nunca usar `or` sobre un Element de XML (es falsy si no tiene hijos)
    return BGGGameMetadata(
        bgg_id=bgg_id,
        name=name,
        description=_clean_description(item.findtext("description")),
        image_url=item.findtext("image") or None,
        thumbnail_url=item.findtext("thumbnail") or None,
        min_players=_to_int(min_el.get("value")) if min_el is not None else None,
        max_players=_to_int(max_el.get("value")) if max_el is not None else None,
        avg_playtime_minutes=_to_int(playtime_el.get("value")) if playtime_el is not None else None,
        year_published=_to_int(year_el.get("value")) if year_el is not None else None,
        bgg_ranking=ranking,
        bgg_rating=rating,
    )


def search_games(query: str, limit: int = 10) -> list[BGGSearchItem]:
    """Búsqueda de juegos de mesa por texto en BGG."""
    root = _request("/search", {"query": query, "type": "boardgame"})
    results: list[BGGSearchItem] = []
    for item in root.findall("item"):
        if item.get("type") != "boardgame":
            continue
        names = item.findall("name")
        primary = next((n for n in names if n.get("primary") == "true"), None)
        name_el = primary if primary is not None else (names[0] if names else None)
        if name_el is None:
            continue
        results.append(
            BGGSearchItem(
                bgg_id=int(item.get("id", "0")),
                name=name_el.get("value", ""),
                year_published=_to_int(
                    (item.find("yearpublished").get("value")
                     if item.find("yearpublished") is not None else None)
                ),
            )
        )
        if len(results) >= limit:
            break
    return results
