#!/usr/bin/env python3
"""
Collection API.

Lists the user's collection cards (with undiscovered guide species shown as
silhouette slots) and serves stable card detail by public ID. Card reads enforce
ownership: a card belonging to another user is answered with 404.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import get_current_user
from db.models import BaseService
from db.session import get_db
from services import cards

router = APIRouter(prefix="/api/collection", tags=["Collection"])

VALID_CATEGORIES = {"flora", "fauna", "fungi"}


def _user_id(user):
    data = dict(user._asdict()) if hasattr(user, "_asdict") else dict(user)
    return data["id"]


def _species_dict(r) -> dict:
    d = dict(r._asdict()) if hasattr(r, "_asdict") else dict(r)
    return {
        "id": d["id"],
        "canonical_key": d["canonical_key"],
        "common_name": d["common_name"],
        "scientific_name": d["scientific_name"],
        "category": d["category"],
        "rarity": d["rarity"],
        "description": d["description"],
        "hint": d["hint"],
        "card_image_key": d["card_image_key"],
    }


@router.get("")
def get_collection(
    category: str = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    uid = _user_id(user)
    service = BaseService(db)
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="Invalid category filter.")

    # Discovered cards joined with species metadata.
    cards_rows = service.fetchall(
        """
        SELECT ucc.public_id, ucc.count, ucc.first_discovered_at, ucc.last_discovered_at,
               s.*
        FROM user_collection_cards ucc
        JOIN species s ON s.id = ucc.species_id
        WHERE ucc.user_id = :uid
        """,
        {"uid": uid},
    )
    seen_species = set()
    result = []
    for row in cards_rows:
        r = dict(row._asdict())
        seen_species.add(r["id"])
        if category and r["category"] != category:
            continue
        result.append(
            {
                "public_id": r["public_id"],
                "discovered": True,
                "count": r["count"],
                "first_discovered_at": str(r["first_discovered_at"]) if r["first_discovered_at"] else None,
                "last_discovered_at": str(r["last_discovered_at"]) if r["last_discovered_at"] else None,
                "cardUrl": cards.card_url(r["public_id"]),
                "species": _species_dict(r),
            }
        )

    # Undiscovered guide slots (silhouettes) not yet collected by this user.
    if category:
        guide = service.fetchall(
            "SELECT * FROM species WHERE category = :cat ORDER BY common_name", {"cat": category}
        )
    else:
        guide = service.fetchall("SELECT * FROM species ORDER BY category, common_name")
    for g in guide:
        gd = dict(g._asdict()) if hasattr(g, "_asdict") else dict(g)
        if gd["id"] in seen_species:
            continue
        result.append(
            {
                "public_id": None,
                "discovered": False,
                "count": 0,
                "first_discovered_at": None,
                "last_discovered_at": None,
                "cardUrl": None,
                "species": _species_dict(gd),
            }
        )

    return {"cards": result, "total": len(result)}


@router.get("/card-{public_id}")
def get_card(public_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Return one card for the authenticated user. Non-owned cards are 404."""
    uid = _user_id(user)
    service = BaseService(db)
    card = service.fetchone(
        "SELECT * FROM user_collection_cards WHERE public_id = :pid AND user_id = :uid",
        {"pid": public_id, "uid": uid},
    )
    if card is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "CARD_NOT_FOUND", "message": "Card not found."},
        )
    detail = cards.card_detail(service, card)
    # observation count equals card count for accepted discoveries.
    return {"card": detail}


@router.get("/{public_id}")
def get_card_alt(public_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Alternate card route matching FastAPI's path convention."""
    return get_card(public_id, db, user)