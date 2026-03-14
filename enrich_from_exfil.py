#!/usr/bin/env python3
"""
Enrich MLBB-API heroes with data from MLBB-Exfil scraped JSON files

This script reads the pre-scraped hero detail JSON files from the MLBB-Exfil
repository and enriches the MLBB-API hero-meta-final.json with:
- Skills (passive + active abilities)
- Speciality
- Counters
- Synergies

Usage:
    python3 enrich_from_exfil.py
"""

import json
import os
from pathlib import Path
from typing import Dict, List


def load_json(filepath: str) -> Dict:
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filepath: str, data: Dict) -> None:
    """Save JSON file with pretty formatting"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"✓ Saved: {filepath}")


def transform_skill_data(skill: Dict) -> Dict:
    """Transform mlbb.io skill data to MLBB-API schema"""
    skill_type_map = {
        'passive': 'passive',
        'skill_1': 'active',
        'skill_2': 'active',
        'ultimate': 'active'
    }

    skill_key = skill.get('skill_key', 'passive')
    skill_type = skill_type_map.get(skill_key, 'active')

    cooldown = "null"
    manacost = "null"

    if skill.get('skill_scaling'):
        scaling = skill['skill_scaling']
        if 'cooldown' in scaling:
            cooldown = str(scaling['cooldown'])
        if 'mana_cost' in scaling:
            mana_costs = scaling['mana_cost']
            if isinstance(mana_costs, list) and mana_costs:
                manacost = " / ".join(str(x) for x in mana_costs)

    return {
        "skill_name": skill.get('skill_name', ''),
        "skill_icon": skill.get('skill_image_path', ''),
        "type": skill_type,
        "cooldown": cooldown,
        "manacost": manacost,
        "description": skill.get('skill_description', '')[:500]
    }


def load_exfil_hero_data(exfil_dir: str) -> Dict[str, Dict]:
    """
    Load all hero detail JSON files from MLBB-Exfil output directory

    Args:
        exfil_dir: Path to MLBB-Exfil/output directory

    Returns:
        Dict mapping hero_name to hero detail data
    """
    hero_data = {}
    output_dir = Path(exfil_dir)

    if not output_dir.exists():
        print(f"✗ Directory not found: {exfil_dir}")
        return hero_data

    json_files = list(output_dir.glob("*.json"))
    print(f"Found {len(json_files)} hero JSON files")

    for json_file in json_files:
        try:
            data = load_json(str(json_file))
            if data.get('success') and 'data' in data:
                hero_name = data['data']['hero_name']
                hero_data[hero_name] = data['data']

                # Also store by filename (without extension) for edge cases like Chang'e
                filename_key = json_file.stem  # 'chang-e' from 'chang-e.json'
                if filename_key != hero_name.lower().replace(' ', '-').replace("'", '-'):
                    hero_data[filename_key] = data['data']

                print(f"  ✓ Loaded: {hero_name}")
        except Exception as e:
            print(f"  ✗ Failed to load {json_file.name}: {e}")

    return hero_data


def enrich_heroes(hero_meta: Dict, hero_details: Dict[str, Dict]) -> Dict:
    """
    Enrich hero metadata with detailed information

    Args:
        hero_meta: Current MLBB-API hero-meta-final.json
        hero_details: Dict of hero detail data from MLBB-Exfil

    Returns:
        Enriched hero metadata
    """
    enriched_count = 0
    skipped_count = 0

    for hero in hero_meta['data']:
        hero_name = hero['hero_name']

        # Skip null entry
        if hero_name == "None":
            continue

        # Try to find matching detail data
        # Try various name formats to handle apostrophes, hyphens, spaces
        detail_data = None
        name_variants = [
            hero_name,
            hero_name.replace('-', ' '),
            hero_name.replace(' ', ''),
            hero_name.replace("'", ''),      # Remove apostrophe
            hero_name.replace("'", '-'),     # Apostrophe to hyphen (Chang'e -> Chang-e)
            hero_name.replace(' ', '-'),     # Space to hyphen
        ]

        for name_variant in name_variants:
            if name_variant in hero_details:
                detail_data = hero_details[name_variant]
                break

        if not detail_data:
            print(f"  ⚠ No detail data for: {hero_name}")
            skipped_count += 1
            continue

        # Enrich skills
        if 'skills' in detail_data and detail_data['skills']:
            hero['skills'] = []
            for skill in detail_data['skills']:
                transformed_skill = transform_skill_data(skill)
                hero['skills'].append(transformed_skill)

        # Add speciality
        if 'speciality' in detail_data and detail_data['speciality']:
            hero['speciality'] = detail_data['speciality']

        # Add counters (simplified to heroid and heroname)
        if 'counters' in detail_data and detail_data['counters']:
            hero['counters'] = []
            for counter in detail_data['counters']:
                hero['counters'].append({
                    "heroid": counter.get('id'),
                    "heroname": counter.get('hero_name')
                })

        # Add synergies (simplified to heroid and heroname)
        if 'synergies' in detail_data and detail_data['synergies']:
            hero['synergies'] = []
            for synergy in detail_data['synergies']:
                hero['synergies'].append({
                    "heroid": synergy.get('id'),
                    "heroname": synergy.get('hero_name')
                })

        enriched_count += 1

    print(f"\n✓ Enriched {enriched_count} heroes")
    print(f"⚠ Skipped {skipped_count} heroes (no detail data)")

    return hero_meta


def main():
    """Main enrichment workflow"""
    print("=" * 60)
    print("MLBB Hero Enrichment from MLBB-Exfil")
    print("=" * 60)

    # Paths
    exfil_output_dir = "/root/MLBB-Exfil/output"
    hero_meta_path = "/var/www/sites/mlbb.site/MLBB-API/v1/hero-meta-final.json"

    # Load current hero metadata
    print("\n[1/4] Loading hero metadata...")
    hero_meta = load_json(hero_meta_path)
    print(f"  - Loaded {len(hero_meta['data'])} heroes")

    # Load MLBB-Exfil hero detail data
    print("\n[2/4] Loading MLBB-Exfil hero data...")
    hero_details = load_exfil_hero_data(exfil_output_dir)

    if not hero_details:
        print("\n✗ No hero details found!")
        print(f"  Make sure MLBB-Exfil is cloned to: {exfil_output_dir}")
        return 1

    # Enrich heroes with detail data
    print("\n[3/4] Enriching heroes with detail data...")
    enriched_meta = enrich_heroes(hero_meta, hero_details)

    # Save enriched data
    print("\n[4/4] Saving enriched data...")
    save_json(hero_meta_path, enriched_meta)

    print("\n" + "=" * 60)
    print("Hero enrichment complete!")
    enriched_heroes = [h for h in hero_meta['data'] if h.get('skills')]
    print(f"✓ Enriched {len(enriched_heroes)} heroes with complete data")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
