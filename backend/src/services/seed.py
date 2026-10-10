#!/usr/bin/env python3
"""
Idempotent seed data for NaturalDex.

Provides the daily-task pool (task_catalog) and a small guide-species catalogue
so the collection screen can show undiscovered silhouette slots. Seeding is
idempotent (upsert by stable key) and safe to call on every startup as well as
through the standalone seed script.
"""

from sqlalchemy import text

# --------------------------------------------------------------------------
# Daily-task pool (>= 20 tasks across Flora, Fauna and Fungi).
# --------------------------------------------------------------------------
TASK_CATALOG = [
    # Flora
    {"slug": "new-flora", "title": "Discover a new flora species", "category": "flora", "target_value": 1, "xp_value": 30, "icon": "leaf"},
    {"slug": "flora-three-views", "title": "Complete a three-view flora observation", "category": "flora", "target_value": 1, "xp_value": 20, "icon": "scan"},
    {"slug": "flora-flower", "title": "Photograph a flowering plant up close", "category": "flora", "target_value": 1, "xp_value": 15, "icon": "flower"},
    {"slug": "flora-tree", "title": "Record a tree or woody shrub", "category": "flora", "target_value": 1, "xp_value": 15, "icon": "tree-deciduous"},
    {"slug": "flora-revisit", "title": "Revisit a flora species in your collection", "category": "flora", "target_value": 1, "xp_value": 10, "icon": "refresh-cw"},
    {"slug": "flora-fern", "title": "Find and identify a fern", "category": "flora", "target_value": 1, "xp_value": 20, "icon": "sprout"},
    # Fauna
    {"slug": "new-fauna", "title": "Record a new fauna sighting", "category": "fauna", "target_value": 1, "xp_value": 30, "icon": "paw-print"},
    {"slug": "fauna-bird", "title": "Photograph a bird", "category": "fauna", "target_value": 1, "xp_value": 25, "icon": "bird"},
    {"slug": "fauna-insect", "title": "Observe and identify an insect", "category": "fauna", "target_value": 1, "xp_value": 20, "icon": "bug"},
    {"slug": "fauna-mammal", "title": "Capture a mammal sighting", "category": "fauna", "target_value": 1, "xp_value": 30, "icon": "rabbit"},
    {"slug": "fauna-revisit", "title": "Revisit a fauna species in your collection", "category": "fauna", "target_value": 1, "xp_value": 10, "icon": "refresh-cw"},
    {"slug": "fauna-community", "title": "Record a social or group animal behavior", "category": "fauna", "target_value": 1, "xp_value": 25, "icon": "users"},
    # Fungi
    {"slug": "new-fungi", "title": "Find a new fungus species", "category": "fungi", "target_value": 1, "xp_value": 30, "icon": "mushroom"},
    {"slug": "fungi-cap", "title": "Photograph a mushroom cap in detail", "category": "fungi", "target_value": 1, "xp_value": 20, "icon": "mushroom"},
    {"slug": "fungi-revisit", "title": "Revisit a fungi species in your collection", "category": "fungi", "target_value": 1, "xp_value": 10, "icon": "refresh-cw"},
    {"slug": "fungi-where", "title": "Note the habitat where you found a fungus", "category": "fungi", "target_value": 1, "xp_value": 15, "icon": "map-pin"},
    # Exploration / any category
    {"slug": "three-views-any", "title": "Complete any three-view discovery", "category": "all", "target_value": 1, "xp_value": 20, "icon": "scan"},
    {"slug": "discover-two", "title": "Make two discoveries today", "category": "all", "target_value": 2, "xp_value": 40, "icon": "target"},
    {"slug": "collection-photo", "title": "Grow your collection with a new species", "category": "all", "target_value": 1, "xp_value": 25, "icon": "bookmark-plus"},
    {"slug": "morning-log", "title": "Log a field observation before noon", "category": "all", "target_value": 1, "xp_value": 15, "icon": "sun"},
    {"slug": "close-view", "title": "Capture a clear close-up detail view", "category": "all", "target_value": 1, "xp_value": 15, "icon": "zoom-in"},
    {"slug": "outdoor-habitat", "title": "Include habitat context in a discovery", "category": "all", "target_value": 1, "xp_value": 15, "icon": "mountain"},
    {"slug": "five-day-streak", "title": "Keep a multi-day observation streak alive", "category": "all", "target_value": 1, "xp_value": 20, "icon": "flame"},
    {"slug": "conservation", "title": "Identify something new to you", "category": "all", "target_value": 1, "xp_value": 25, "icon": "sparkles"},
]

# --------------------------------------------------------------------------
# Guide species catalogue (undiscovered silhouette slots).
# --------------------------------------------------------------------------
GUIDE_SPECIES = [
    {"canonical_key": "oak", "common_name": "Oak", "scientific_name": "Quercus spp.", "category": "flora", "rarity": "Common", "description": "Broad-leaved trees with distinctive lobed leaves and acorns.", "icon": "tree-deciduous"},
    {"canonical_key": "dandelion", "common_name": "Dandelion", "scientific_name": "Taraxacum officinale", "category": "flora", "rarity": "Common", "description": "Edible wildflower with a bright yellow composite head.", "icon": "flower"},
    {"canonical_key": "fern", "common_name": "Fern", "scientific_name": "Polypodiopsida", "category": "flora", "rarity": "Uncommon", "description": "Leafy, non-flowering plants reproducing by spores.", "icon": "sprout"},
    {"canonical_key": "raven", "common_name": "Raven", "scientific_name": "Corvus corax", "category": "fauna", "rarity": "Uncommon", "description": "Large glossy-black bird with a deep croaking call.", "icon": "bird"},
    {"canonical_key": "red-squirrel", "common_name": "Red Squirrel", "scientific_name": "Sciurus vulgaris", "category": "fauna", "rarity": "Rare", "description": "Small agile rodent with a rust-red coat and bushy tail.", "icon": "rabbit"},
    {"canonical_key": "honey-bee", "common_name": "Honey Bee", "scientific_name": "Apis mellifera", "category": "fauna", "rarity": "Common", "description": "Social bee that collects nectar and pollinates flowers.", "icon": "bug"},
    {"canonical_key": "fly-agaric", "common_name": "Fly Agaric", "scientific_name": "Amanita muscaria", "category": "fungi", "rarity": "Uncommon", "description": "Bright red toadstool with white spots.", "icon": "mushroom"},
    {"canonical_key": "oyster-mushroom", "common_name": "Oyster Mushroom", "scientific_name": "Pleurotus ostreatus", "category": "fungi", "rarity": "Common", "description": "Fan-shaped mushroom growing on wood in shelves.", "icon": "mushroom"},
    {"canonical_key": "chanterelle", "common_name": "Chanterelle", "scientific_name": "Cantharellus cibarius", "category": "fungi", "rarity": "Rare", "description": "Golden-yellow mushroom with a wavy, vase-like cap.", "icon": "mushroom"},
]


def seed_task_catalog(service):
    """Idempotently upsert the daily-task pool by slug."""
    from db.models import BaseService

    db_service = service if isinstance(service, BaseService) else BaseService(service)
    try:
        for item in TASK_CATALOG:
            db_service.execute(
                "INSERT OR IGNORE INTO task_catalog "
                "(slug, title, category, target_value, xp_value, icon, active, created_at, updated_at) "
                "VALUES (:slug, :title, :category, :target_value, :xp_value, :icon, 1, :now, :now)",
                {**item, "now": _now()},
            )
            # Refresh metadata on existing rows so seed edits propagate.
            db_service.execute(
                "UPDATE task_catalog SET title = :title, category = :category, "
                "target_value = :target_value, xp_value = :xp_value, icon = :icon, "
                "active = 1, updated_at = :now WHERE slug = :slug",
                {**item, "now": _now()},
            )
        db_service.commit()
    except Exception:
        db_service.rollback()
        raise
    return len(TASK_CATALOG)


def seed_guide_species(service):
    """Idempotently upsert the guide species catalogue by canonical_key."""
    from sqlalchemy import text

    from db.models import BaseService

    db_service = service if isinstance(service, BaseService) else BaseService(service)
    try:
        for item in GUIDE_SPECIES:
            db_service.execute(
                "INSERT OR IGNORE INTO species "
                "(canonical_key, common_name, scientific_name, category, rarity, "
                "description, hint, created_at, updated_at) "
                "VALUES (:canonical_key, :common_name, :scientific_name, :category, "
                ":rarity, :description, :description, :now, :now)",
                {**item, "now": _now()},
            )
        db_service.commit()
    except Exception:
        db_service.rollback()
        raise
    return len(GUIDE_SPECIES)


def seed_all(service):
    """Run every seed idempotently; returns {'tasks': n, 'guide_species': m}."""
    return {
        "tasks": seed_task_catalog(service),
        "guide_species": seed_guide_species(service),
    }


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)