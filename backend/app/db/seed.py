"""Seed inicial: roles globales y catálogo de logros/insignias."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Achievement, Game, Role
from app.models.enums import GlobalRole

GLOBAL_ROLES: dict[str, str] = {
    GlobalRole.ADMIN.value: "Acceso total a la plataforma, moderación de usuarios y mantenimiento del sistema.",
    GlobalRole.PLAYER.value: "Usuario estándar: unirse a grupos, registrar partidas y ver estadísticas.",
}

POPULAR_GAMES: list[dict[str, object]] = [
    {
        "bgg_id": 13,
        "name": "Catan",
        "description": "Los jugadores intentan ser la fuerza dominante en la isla de Catan construyendo asentamientos, ciudades y caminos.",
        "image_url": "https://cf.geekdo-images.com/W397RfmHGtOi3EHUrHtYuA__original/img/A-fVsJEPlv6T5twJ6nuhWcBn2XU=/0x0/filters:format(jpeg)/pic2419375.jpg",
        "thumbnail_url": "https://cf.geekdo-images.com/W397RfmHGtOi3EHUrHtYuA__thumb/img/gA5g_6n7GzD-3_Wf10R2uE6jQvY=/fit-in/200x150/filters:strip_icc()/pic2419375.jpg",
        "min_players": 3,
        "max_players": 4,
        "avg_playtime_minutes": 90,
        "year_published": 1995,
        "bgg_ranking": 500,
        "bgg_rating": 7.1,
    },
    {
        "bgg_id": 822,
        "name": "Carcassonne",
        "description": "Juego de colocación de losetas donde los jugadores desarrollan el área alrededor de Carcasona con caminos, ciudades y monasterios.",
        "image_url": "https://cf.geekdo-images.com/okM0dq_bEXnbyQTOvHZwRw__original/img/eO7_P4Q69g3W4mR8cEwW8_5Q8_g=/0x0/filters:format(jpeg)/pic6544250.png",
        "thumbnail_url": "https://cf.geekdo-images.com/okM0dq_bEXnbyQTOvHZwRw__thumb/img/hXyC9j_Xb2Jt2xM6n3W_6n7GzD4=/fit-in/200x150/filters:strip_icc()/pic6544250.png",
        "min_players": 2,
        "max_players": 5,
        "avg_playtime_minutes": 45,
        "year_published": 2000,
        "bgg_ranking": 220,
        "bgg_rating": 7.4,
    },
    {
        "bgg_id": 30549,
        "name": "Pandemic",
        "description": "Tu equipo de especialistas en el control de enfermedades debe colaborar para investigar curas a cuatro plagas mortales.",
        "image_url": "https://cf.geekdo-images.com/S3ybV1LAp-AS4mIsVqUbRg__original/img/I-k2Y9k8v7Z0b_E1h4_g6L7nQeA=/0x0/filters:format(jpeg)/pic1534148.jpg",
        "thumbnail_url": "https://cf.geekdo-images.com/S3ybV1LAp-AS4mIsVqUbRg__thumb/img/K-qR9k8v7Z0b_E1h4_g6L7nQeA=/fit-in/200x150/filters:strip_icc()/pic1534148.jpg",
        "min_players": 2,
        "max_players": 4,
        "avg_playtime_minutes": 45,
        "year_published": 2008,
        "bgg_ranking": 140,
        "bgg_rating": 7.6,
    },
    {
        "bgg_id": 9209,
        "name": "Ticket to Ride",
        "description": "Aventura ferroviaria en la que los jugadores compiten por conectar diferentes ciudades a través de Norteamérica en tren.",
        "image_url": "https://cf.geekdo-images.com/ZWJg0dCgahB3KnMVxV8png__original/img/w2q2_6n7GzD-3_Wf10R2uE6jQvY=/0x0/filters:format(jpeg)/pic38668.jpg",
        "thumbnail_url": "https://cf.geekdo-images.com/ZWJg0dCgahB3KnMVxV8png__thumb/img/w2q2_6n7GzD-3_Wf10R2uE6jQvY=/fit-in/200x150/filters:strip_icc()/pic38668.jpg",
        "min_players": 2,
        "max_players": 5,
        "avg_playtime_minutes": 60,
        "year_published": 2004,
        "bgg_ranking": 230,
        "bgg_rating": 7.4,
    },
    {
        "bgg_id": 230802,
        "name": "Azul",
        "description": "Los jugadores compiten como artesanos colocando azulejos de cerámica estilo mozárabe para decorar el palacio real de Évora.",
        "image_url": "https://cf.geekdo-images.com/tz19Pf9gaAVkV50UeAEufA__original/img/Z-3q9k8v7Z0b_E1h4_g6L7nQeA=/0x0/filters:format(jpeg)/pic3718275.jpg",
        "thumbnail_url": "https://cf.geekdo-images.com/tz19Pf9gaAVkV50UeAEufA__thumb/img/Z-3q9k8v7Z0b_E1h4_g6L7nQeA=/fit-in/200x150/filters:strip_icc()/pic3718275.jpg",
        "min_players": 2,
        "max_players": 4,
        "avg_playtime_minutes": 45,
        "year_published": 2017,
        "bgg_ranking": 75,
        "bgg_rating": 7.8,
    },
    {
        "bgg_id": 167791,
        "name": "Terraforming Mars",
        "description": "Grandes corporaciones compiten para transformar Marte en un planeta habitable gestionando recursos y megaproyectos.",
        "image_url": "https://cf.geekdo-images.com/wg9oOLcsKvDesqGGjSS4Sw__original/img/f8Yq9k8v7Z0b_E1h4_g6L7nQeA=/0x0/filters:format(jpeg)/pic3536616.jpg",
        "thumbnail_url": "https://cf.geekdo-images.com/wg9oOLcsKvDesqGGjSS4Sw__thumb/img/f8Yq9k8v7Z0b_E1h4_g6L7nQeA=/fit-in/200x150/filters:strip_icc()/pic3536616.jpg",
        "min_players": 1,
        "max_players": 5,
        "avg_playtime_minutes": 120,
        "year_published": 2016,
        "bgg_ranking": 6,
        "bgg_rating": 8.4,
    },
    {
        "bgg_id": 68448,
        "name": "7 Wonders",
        "description": "Lidera una de las siete grandes ciudades del mundo antiguo y erige una maravilla arquitectónica que trascienda los tiempos.",
        "image_url": "https://cf.geekdo-images.com/35nVHQIs-SOcDTjdCJEMSg__original/img/B8zq9k8v7Z0b_E1h4_g6L7nQeA=/0x0/filters:format(jpeg)/pic860217.jpg",
        "thumbnail_url": "https://cf.geekdo-images.com/35nVHQIs-SOcDTjdCJEMSg__thumb/img/B8zq9k8v7Z0b_E1h4_g6L7nQeA=/fit-in/200x150/filters:strip_icc()/pic860217.jpg",
        "min_players": 2,
        "max_players": 7,
        "avg_playtime_minutes": 30,
        "year_published": 2010,
        "bgg_ranking": 95,
        "bgg_rating": 7.7,
    },
    {
        "bgg_id": 266192,
        "name": "Wingspan",
        "description": "Juego competitivo de aves y construcción de motores donde los jugadores atraen las mejores aves a sus reservas naturales.",
        "image_url": "https://cf.geekdo-images.com/yLZJ0mkZw46fColCallerw__original/img/yLZJ0mkZw46fColCallerw.jpg",
        "thumbnail_url": "https://cf.geekdo-images.com/yLZJ0mkZw46fColCallerw__thumb/img/yLZJ0mkZw46fColCallerw.jpg",
        "min_players": 1,
        "max_players": 5,
        "avg_playtime_minutes": 70,
        "year_published": 2019,
        "bgg_ranking": 25,
        "bgg_rating": 8.0,
    },
    {
        "bgg_id": 148228,
        "name": "Splendor",
        "description": "Comerciantes del Renacimiento adquieren minas de gemas, transporte y tiendas para ganar prestigio ante los nobles.",
        "image_url": "https://cf.geekdo-images.com/rwOMBatchDFas398h_original/pic1904079.jpg",
        "thumbnail_url": "https://cf.geekdo-images.com/rwOMBatchDFas398h_thumb/pic1904079.jpg",
        "min_players": 2,
        "max_players": 4,
        "avg_playtime_minutes": 30,
        "year_published": 2014,
        "bgg_ranking": 200,
        "bgg_rating": 7.4,
    },
    {
        "bgg_id": 169786,
        "name": "Scythe",
        "description": "Ambientado en una realidad alternativa de los años 1920, cada jugador representa a un líder intentando llevar a su facción a la prosperidad en Europa oriental.",
        "image_url": "https://cf.geekdo-images.com/7k_nOxpO9OGIjhLqAnYCgw__original/pic3163924.jpg",
        "thumbnail_url": "https://cf.geekdo-images.com/7k_nOxpO9OGIjhLqAnYCgw__thumb/pic3163924.jpg",
        "min_players": 1,
        "max_players": 5,
        "avg_playtime_minutes": 115,
        "year_published": 2016,
        "bgg_ranking": 16,
        "bgg_rating": 8.1,
    },
    {
        "bgg_id": 316554,
        "name": "Dune: Imperium",
        "description": "Estrategia y construcción de mazos ambientada en el universo de Dune. Lucha por el control de la especia en Arrakis.",
        "image_url": "https://cf.geekdo-images.com/PhjygpTFaa_UN4RrCnWq3g__original/pic5666597.jpg",
        "thumbnail_url": "https://cf.geekdo-images.com/PhjygpTFaa_UN4RrCnWq3g__thumb/pic5666597.jpg",
        "min_players": 1,
        "max_players": 4,
        "avg_playtime_minutes": 120,
        "year_published": 2020,
        "bgg_ranking": 7,
        "bgg_rating": 8.4,
    },
    {
        "bgg_id": 295947,
        "name": "Cascadia",
        "description": "Crea hábitats armoniosos en el noroeste del Pacífico seleccionando fichas de terreno y fauna para maximizar la puntuación.",
        "image_url": "https://cf.geekdo-images.com/cbA3bEeqXqI0Fq8W3w__original/pic5100691.jpg",
        "thumbnail_url": "https://cf.geekdo-images.com/cbA3bEeqXqI0Fq8W3w__thumb/pic5100691.jpg",
        "min_players": 1,
        "max_players": 4,
        "avg_playtime_minutes": 45,
        "year_published": 2021,
        "bgg_ranking": 35,
        "bgg_rating": 8.0,
    },
]

ACHIEVEMENTS: list[dict[str, object]] = [
    {
        "code": "FIRST_BLOOD",
        "name": "Primera Sangre",
        "description": "Gana tu primera partida con un juego que nunca habías ganado.",
        "condition": {"type": "first_win_with_game"},
    },
    {
        "code": "WIN_STREAK_5",
        "name": "Racha de Victorias",
        "description": "Consigue 5 victorias seguidas en el mismo grupo.",
        "condition": {"type": "win_streak", "streak": 5},
    },
    {
        "code": "GAMES_10",
        "name": "Veterano de Mesa",
        "description": "Juega 10 partidas verificadas en un grupo.",
        "condition": {"type": "games_played", "threshold": 10},
    },
    {
        "code": "GAMES_50",
        "name": "Leyenda del Grupo",
        "description": "Juega 50 partidas verificadas en un grupo.",
        "condition": {"type": "games_played", "threshold": 50},
    },
]


def seed_roles(db: Session) -> None:
    for name, description in GLOBAL_ROLES.items():
        exists = db.scalar(select(Role).where(Role.name == name))
        if exists is None:
            db.add(Role(name=name, description=description))
    db.commit()


def seed_achievements(db: Session) -> None:
    for item in ACHIEVEMENTS:
        exists = db.scalar(select(Achievement).where(Achievement.code == item["code"]))
        if exists is None:
            db.add(
                Achievement(
                    code=item["code"],  # type: ignore[arg-type]
                    name=item["name"],  # type: ignore[arg-type]
                    description=item["description"],  # type: ignore[arg-type]
                    condition=item["condition"],  # type: ignore[arg-type]
                )
            )
    db.commit()


def seed_popular_games(db: Session, group_id: int, added_by_id: int | None = None) -> list[Game]:
    """Precarga los juegos de mesa más populares en el catálogo de un grupo."""
    created = []
    for g in POPULAR_GAMES:
        exists = db.scalar(
            select(Game.id).where(Game.group_id == group_id, Game.bgg_id == g["bgg_id"])
        )
        if exists is None:
            game = Game(
                group_id=group_id,
                bgg_id=g["bgg_id"],  # type: ignore[arg-type]
                name=g["name"],  # type: ignore[arg-type]
                description=g["description"],  # type: ignore[arg-type]
                image_url=g["image_url"],  # type: ignore[arg-type]
                thumbnail_url=g["thumbnail_url"],  # type: ignore[arg-type]
                min_players=g["min_players"],  # type: ignore[arg-type]
                max_players=g["max_players"],  # type: ignore[arg-type]
                avg_playtime_minutes=g["avg_playtime_minutes"],  # type: ignore[arg-type]
                year_published=g["year_published"],  # type: ignore[arg-type]
                bgg_ranking=g["bgg_ranking"],  # type: ignore[arg-type]
                bgg_rating=g["bgg_rating"],  # type: ignore[arg-type]
                added_by_id=added_by_id,
            )
            db.add(game)
            created.append(game)
    db.commit()
    for game in created:
        db.refresh(game)
    return created

