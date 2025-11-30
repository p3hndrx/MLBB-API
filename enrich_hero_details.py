#!/usr/bin/env python3
"""
MLBB Hero Detail Enrichment Script (Phase 2)
Enriches hero data with detailed skill information from mlbb.io

This script merges the detailed hero data (skills, counters, synergies, etc.)
from mlbb.io/api/hero/detail/{heroName} into the MLBB-API schema

Usage:
    python3 enrich_hero_details.py [--har-file PATH] [--fetch-api] [--delay SECONDS]

Options:
    --har-file PATH      Extract hero details from HAR file (default: /root/MLBB-Observability/mlbb.io.har)
    --fetch-api          Fetch hero details from mlbb.io API for all heroes
    --delay SECONDS      Delay between API requests (default: 0.5)
"""

import json
import sys
import argparse
import time
import requests
from typing import Dict, List, Any, Optional


def load_json(filepath: str) -> Dict:
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filepath: str, data: Dict) -> None:
    """Save JSON file with pretty formatting"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"✓ Saved: {filepath}")


def fetch_hero_detail_from_api(hero_name: str, delay: float = 0.5) -> Optional[Dict]:
    """
    Fetch hero detail from mlbb.io API

    Args:
        hero_name: Hero name (e.g., "Kagura", "Angela")
        delay: Delay in seconds before request (rate limiting)

    Returns:
        Hero detail data or None if failed
    """
    # Format hero name for URL (handle spaces and special characters)
    url_name = hero_name.replace(' ', '%20').replace("'", '')
    url = f"https://mlbb.io/api/hero/detail/{url_name}"

    try:
        time.sleep(delay)
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data['data']
            else:
                print(f"  ✗ API error for {hero_name}: {data.get('message', 'Unknown error')}")
        else:
            print(f"  ✗ HTTP {response.status_code} for {hero_name}")

    except requests.exceptions.RequestException as e:
        print(f"  ✗ Request failed for {hero_name}: {e}")

    return None


def fetch_all_hero_details(heroes: List[str], delay: float = 0.5) -> Dict[str, Dict]:
    """
    Fetch hero details for all heroes from API

    Args:
        heroes: List of hero names
        delay: Delay between requests

    Returns:
        Dict mapping hero_name to detail data
    """
    hero_details = {}
    total = len(heroes)

    print(f"Fetching details for {total} heroes from mlbb.io API...")
    print("This may take several minutes...\n")

    for idx, hero_name in enumerate(heroes, 1):
        print(f"[{idx}/{total}] Fetching: {hero_name}...", end=' ')

        detail = fetch_hero_detail_from_api(hero_name, delay)
        if detail:
            hero_details[hero_name] = detail
            print("✓")
        else:
            print("✗ Failed")

    print(f"\n✓ Successfully fetched {len(hero_details)}/{total} heroes")
    return hero_details


def extract_hero_details_from_har(har_file: str) -> Dict[str, Dict]:
    """
    Extract hero detail data from HAR file

    Returns dict: {hero_name: hero_detail_data}
    """
    print(f"Loading HAR file: {har_file}")
    har_data = load_json(har_file)

    hero_details = {}

    for entry in har_data['log']['entries']:
        url = entry['request']['url']

        # Check if this is a hero detail request
        if '/api/hero/detail/' in url:
            hero_name = url.split('/api/hero/detail/')[-1].split('?')[0]

            # Extract response
            response_text = entry['response']['content'].get('text', '')
            if response_text:
                try:
                    response_data = json.loads(response_text)
                    if response_data.get('success'):
                        hero_details[hero_name] = response_data['data']
                        print(f"  ✓ Extracted: {hero_name}")
                except json.JSONDecodeError:
                    print(f"  ✗ Failed to parse: {hero_name}")

    print(f"\nExtracted {len(hero_details)} hero details from HAR")
    return hero_details


def transform_skill_data(skill: Dict) -> Dict:
    """
    Transform mlbb.io skill data to MLBB-API schema

    mlbb.io provides:
    - skill_key: "passive", "skill_1", "skill_2", "ultimate"
    - skill_name: display name
    - skill_type: type tags
    - skill_description: full description
    - skill_scaling: level-based stats
    - skill_effects: additional effects
    """
    skill_type_map = {
        'passive': 'passive',
        'skill_1': 'active',
        'skill_2': 'active',
        'ultimate': 'active'
    }

    skill_key = skill.get('skill_key', 'passive')
    skill_type = skill_type_map.get(skill_key, 'active')

    # Extract cooldown and mana cost
    cooldown = "null"
    manacost = "null"

    if skill.get('skill_scaling'):
        scaling = skill['skill_scaling']
        if 'cooldown' in scaling:
            cooldown = str(scaling['cooldown'])
        if 'mana_cost' in scaling:
            mana_costs = scaling['mana_cost']
            if isinstance(mana_costs, list) and mana_costs:
                # Format as "60 / 70 / 80 / 90 / 100 / 110"
                manacost = " / ".join(str(x) for x in mana_costs)

    transformed = {
        "skill_name": skill.get('skill_name', ''),
        "skill_icon": skill.get('skill_image_path', ''),
        "type": skill_type,
        "cooldown": cooldown,
        "manacost": manacost,
        "description": skill.get('skill_description', '')[:500]  # Truncate if too long
    }

    return transformed


def enrich_heroes(hero_meta: Dict, hero_details: Dict[str, Dict]) -> Dict:
    """
    Enrich hero metadata with detailed skill information

    Args:
        hero_meta: Current MLBB-API hero-meta-final.json
        hero_details: Dict of hero detail data from mlbb.io

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
        # mlbb.io uses exact names, try variations
        detail_data = None
        for name_variant in [hero_name, hero_name.replace('-', ' '), hero_name.replace(' ', '')]:
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
    parser = argparse.ArgumentParser(description='Enrich MLBB hero data with detailed skills')
    parser.add_argument('--har-file', default='/root/MLBB-Observability/mlbb.io.har',
                        help='Path to HAR file containing hero details')
    parser.add_argument('--fetch-api', action='store_true',
                        help='Fetch all hero details from mlbb.io API')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Delay between API requests in seconds (default: 0.5)')

    args = parser.parse_args()

    print("=" * 60)
    print("MLBB Hero Detail Enrichment Script (Phase 2)")
    print("=" * 60)

    # Load current hero metadata
    print("\n[1/4] Loading hero metadata...")
    hero_meta_path = '/var/www/sites/mlbb.site/MLBB-API/v1/hero-meta-final.json'
    hero_meta = load_json(hero_meta_path)
    print(f"  - Loaded {len(hero_meta['data'])} heroes")

    # Get list of hero names (skip null entry)
    hero_names = [h['hero_name'] for h in hero_meta['data'] if h['hero_name'] != 'None']

    # Extract or fetch hero details
    print("\n[2/4] Loading hero detail data...")
    if args.fetch_api:
        hero_details = fetch_all_hero_details(hero_names, args.delay)
    else:
        hero_details = extract_hero_details_from_har(args.har_file)

    if not hero_details:
        print("\n✗ No hero details found!")
        print("  Tip: Use --fetch-api to fetch from mlbb.io")
        sys.exit(1)

    # Enrich heroes with detail data
    print("\n[3/4] Enriching heroes with detail data...")
    enriched_meta = enrich_heroes(hero_meta, hero_details)

    # Save enriched data
    print("\n[4/4] Saving enriched data...")
    save_json(hero_meta_path, enriched_meta)

    print("\n" + "=" * 60)
    print("Hero enrichment complete!")
    print(f"Enriched {len([h for h in hero_meta['data'] if h.get('skills')])} heroes with skills")
    print("=" * 60)


if __name__ == "__main__":
    main()
