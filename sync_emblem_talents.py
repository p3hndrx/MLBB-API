#!/usr/bin/env python3
"""
Refresh v1/emblem-meta-final.json and write a new v1/talent-meta-final.json
to reflect MLBB's current emblem + talent system.

Unlike sync_official_heroes.py, there's no official Moonton API for this data
(per this repo's own README: emblem data is "mostly derived MANUALLY"). The
old emblem-meta-final.json nested 2-3 placeholder talents per emblem, matching
a pre-rework structure where talents were emblem-specific. The current system
is different: talents are a single universal pool of 26 (8 tier1, 8 tier2,
10 tier3) selectable with any of the 7 emblem sets. This script replaces the
stale per-emblem talent block with that pool, sourced + verified against
mlbb.tools (2026-10-23). Emblem sets' own innate `modifiers` are left as-is
(unverified against a current source — flagged as a known gap, not touched).

Also downloads icon assets (7 emblem + 26 talent images, all confirmed
reachable at https://mlbb.tools/emblems/... during research) into
MLBB-BuildShare/http/img/{emblems,talents}/, mirroring the existing
download_missing_items.py pattern in that repo.

Usage:
    python sync_emblem_talents.py            # dry run: print summary, no writes
    python sync_emblem_talents.py --write    # write JSON files + download icons
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import requests

EMBLEM_FILE = Path("v1/emblem-meta-final.json")
TALENT_FILE = Path("v1/talent-meta-final.json")
ICON_BASE = "https://mlbb.tools/emblems"
EMBLEM_ICON_DIR = Path("/var/www/sites/mlbb.site/MLBB-BuildShare/http/img/emblems")
TALENT_ICON_DIR = Path("/var/www/sites/mlbb.site/MLBB-BuildShare/http/img/talents")

# Emblem set id/slug -> matches existing 7 entries in emblem-meta-final.json by emblem_role.
EMBLEM_ICON_SLUGS = {
    "common": "basic-common",
    "tank": "custom-tank",
    "assassin": "custom-assassin",
    "mage": "custom-mage",
    "fighter": "custom-fighter",
    "support": "custom-support",
    "marksman": "custom-marksman",
}

# Verified against mlbb.tools/emblems on 2026-10-23: 26 universal talents,
# selectable with any emblem set (not emblem-restricted, unlike the old system).
TALENTS = {
    "tier1": [
        {"id": "agility", "name": "Agility", "description": "+4% Movement Speed"},
        {"id": "fatal", "name": "Fatal", "description": "+5% Crit Chance, +5% Crit Damage"},
        {"id": "firmness", "name": "Firmness", "description": "+8 Physical & Magic Defense"},
        {"id": "inspire-talent", "name": "Inspire", "description": "+5% CDR, +2 Mana Regen"},
        {"id": "rupture", "name": "Rupture", "description": "+5 Adaptive Penetration"},
        {"id": "swift", "name": "Swift", "description": "+10% Attack Speed"},
        {"id": "thrill", "name": "Thrill", "description": "+16 Adaptive Attack"},
        {"id": "vitality", "name": "Vitality", "description": "+225 max HP"},
    ],
    "tier2": [
        {"id": "bargain-hunter", "name": "Bargain Hunter", "description": "Equipment costs 95% of base price", "cooldown": None},
        {"id": "festival-of-blood", "name": "Festival of Blood", "description": "+6% Spell Vamp. +0.5%/kill (max 12 stacks)", "cooldown": None},
        {"id": "master-assassin", "name": "Master Assassin", "description": "+7% damage when only 1 enemy hero nearby", "cooldown": None},
        {"id": "pull-yourself-together", "name": "Pull Yourself Together", "description": "-12% spell/item active CD. -1%/kill (max 8 stacks)", "cooldown": None},
        {"id": "seasoned-hunter", "name": "Seasoned Hunter", "description": "+15% damage to Lord/Turtle (halved vs creeps)", "cooldown": None},
        {"id": "tenacity", "name": "Tenacity", "description": "+5% Damage Reduction when HP < 50%", "cooldown": None},
        {"id": "weapon-master", "name": "Weapon Master", "description": "+8% to equipment/emblem/talent/skill attack", "cooldown": None},
        {"id": "wilderness-blessing", "name": "Wilderness Blessing", "description": "+10% move speed in jungle/river (halved in hero combat)", "cooldown": None},
    ],
    "tier3": [
        {"id": "brave-smite", "name": "Brave Smite", "description": "Skill damage to hero: recover 5% Max HP", "cooldown": 6},
        {"id": "concussive-blast", "name": "Concussive Blast", "description": "Next basic attack: 100 (+7% Total HP) magic damage to nearby enemies", "cooldown": 15},
        {"id": "focusing-mark", "name": "Focusing Mark", "description": "After damaging hero: allies deal +6% damage, +10% move speed, 3s", "cooldown": 4},
        {"id": "impure-rage", "name": "Impure Rage", "description": "Skills deal 4% target max HP + restore 2% Mana. Max 120 vs non-heroes.", "cooldown": 5},
        {"id": "killing-spree", "name": "Killing Spree", "description": "Damage to heroes <30% HP: recover 15% Lost HP + 20% move speed. Reset on kill.", "cooldown": 30},
        {"id": "lethal-ignition", "name": "Lethal Ignition", "description": "3 hits dealing >7% max HP in 5s: scorch for 162-750 Adaptive Damage", "cooldown": 15},
        {"id": "quantum-charge", "name": "Quantum Charge", "description": "Basic attacks: +30% move speed 1.5s, restore 75-180 HP", "cooldown": 10},
        {"id": "temporal-reign", "name": "Temporal Reign", "description": "Next ult reduces other skills' CD by 1.5x for 4s (+2s on kill/assist)", "cooldown": 20},
        {"id": "war-cry", "name": "War Cry", "description": "After 3 hits on enemy hero, +8% all damage for 6s", "cooldown": 6},
        {"id": "weakness-finder", "name": "Weakness Finder", "description": "Basic attacks: -50% slow, -30% attack speed, 1s", "cooldown": 10},
    ],
}


def build_talent_file() -> dict:
    out = {"title": "talent-meta-final", "revdate": date.today().isoformat(),
           "source": "https://mlbb.tools/emblems (manually verified)", "data": {}}
    for tier, talents in TALENTS.items():
        out["data"][tier] = [
            {**t, "icon": f"/talents/{t['id']}.webp"} for t in talents
        ]
    return out


def update_emblem_file() -> dict:
    with EMBLEM_FILE.open() as f:
        doc = json.load(f)
    for entry in doc["data"]:
        role = entry["emblem_role"]
        slug = EMBLEM_ICON_SLUGS.get(role)
        if slug:
            entry["icon"] = f"/emblems/{slug}.webp"
        # Drop the stale per-emblem placeholder talent block; talents are now
        # a universal pool (see talent-meta-final.json), not per-emblem.
        entry.pop("data", None)
    doc["revdate"] = date.today().isoformat()
    return doc


def download_icons(dry_run: bool):
    EMBLEM_ICON_DIR.mkdir(parents=True, exist_ok=True)
    TALENT_ICON_DIR.mkdir(parents=True, exist_ok=True)

    for role, slug in EMBLEM_ICON_SLUGS.items():
        dest = EMBLEM_ICON_DIR / f"{slug}.webp"
        _download(f"{ICON_BASE}/{slug}.webp", dest, dry_run)

    for tier, talents in TALENTS.items():
        for t in talents:
            dest = TALENT_ICON_DIR / f"{t['id']}.webp"
            _download(f"{ICON_BASE}/talents/{t['id']}.webp", dest, dry_run)


def _download(url: str, dest: Path, dry_run: bool):
    if dest.exists():
        print(f"  skip (exists): {dest.name}")
        return
    if dry_run:
        print(f"  would download: {url} -> {dest}")
        return
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"  downloaded: {dest.name} ({len(resp.content)} bytes)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write JSON files and download icons (default: dry run)")
    args = parser.parse_args()

    talent_doc = build_talent_file()
    emblem_doc = update_emblem_file()

    total_talents = sum(len(v) for v in talent_doc["data"].values())
    print(f"Talents: {total_talents} ({', '.join(f'{k}={len(v)}' for k, v in talent_doc['data'].items())})")
    print(f"Emblem sets: {len(emblem_doc['data'])}")

    print("\nIcons:")
    download_icons(dry_run=not args.write)

    if not args.write:
        print("\nDry run — no files written. Re-run with --write to apply.")
        return

    TALENT_FILE.write_text(json.dumps(talent_doc, indent=2))
    EMBLEM_FILE.write_text(json.dumps(emblem_doc, indent=2))
    print(f"\nWrote {TALENT_FILE} and {EMBLEM_FILE}")


if __name__ == "__main__":
    main()
