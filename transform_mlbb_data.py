#!/usr/bin/env python3
"""
MLBB Data Transformation Script
Transforms mlbb.io API data to MLBB-API schema format

Usage:
    python3 transform_mlbb_data.py
"""

import json
from datetime import datetime
from typing import Dict, List, Any


def load_json(filepath: str) -> Dict:
    """Load JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(filepath: str, data: Dict) -> None:
    """Save JSON file with pretty formatting"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"✓ Saved: {filepath}")


def transform_items(mlbb_items: List[Dict]) -> Dict:
    """
    Transform mlbb.io items to MLBB-API schema

    mlbb.io schema has flat structure with all stats at root level
    MLBB-API schema has nested modifiers, passives, etc.
    """
    transformed = {
        "title": "item-schema",
        "revdate": datetime.now().strftime("%Y%m%d"),
        "patch": "Current 2025",
        "author": "p3hndrx",
        "source": "https://github.com/p3hndrx/MLBB-API",
        "data": []
    }

    # Category mapping
    category_prefix = {
        "Attack": "a",
        "Magic": "m",
        "Defense": "d",
        "Movement": "mo",
        "Attack & Magic": "am"
    }

    # Sort by category for consistent IDs
    sorted_items = sorted(mlbb_items, key=lambda x: (x['category'], x['name']))

    category_counters = {}

    for item in sorted_items:
        # Skip removed items
        if item.get('removed', 0) == 1:
            continue

        category = item['category']
        prefix = category_prefix.get(category, 'x')

        # Generate ID
        if prefix not in category_counters:
            category_counters[prefix] = 1
        else:
            category_counters[prefix] += 1

        item_id = f"{prefix}{category_counters[prefix]:03d}"

        # Build modifiers object
        modifiers = {}
        if item['physical_attack'] > 0:
            modifiers['physical_attack'] = str(item['physical_attack'])
        if item['magic_power'] > 0:
            modifiers['magic_power'] = str(item['magic_power'])
        if item['hp'] > 0:
            modifiers['hp'] = str(item['hp'])
        if item['physical_defense'] > 0:
            modifiers['physical_defense'] = str(item['physical_defense'])
        if item['magic_defense'] > 0:
            modifiers['magic_defense'] = str(item['magic_defense'])
        if item['movement_speed'] > 0:
            modifiers['movement_speed'] = f"{item['movement_speed']}%"
        if item['attack_speed'] > 0:
            modifiers['attack_speed'] = f"{item['attack_speed']}%"
        if item['cooldown_reduction'] > 0:
            modifiers['cd_reduction'] = f"{item['cooldown_reduction']}%"
        if item['lifesteal'] > 0:
            modifiers['physical_lifesteal'] = f"{item['lifesteal']}%"
        if item['spell_vamp'] > 0:
            modifiers['spell_vamp'] = f"{item['spell_vamp']}%"
        if item['penetration'] > 0:
            modifiers['penetration'] = str(item['penetration'])

        # Parse passive effects
        unique_passives = []
        if item['passive_name'] and item['passive_name'] != '':
            # Split multiple passives if they exist
            passive_descriptions = item['passive_description'].split('Unique Passive - ')

            for desc in passive_descriptions:
                if not desc.strip():
                    continue

                # Extract passive name and description
                parts = desc.split(':', 1)
                if len(parts) == 2:
                    passive_name = parts[0].strip()
                    passive_desc = parts[1].strip()

                    unique_passives.append({
                        "unique_passive_name": passive_name,
                        "description": passive_desc,
                        "modifiers": []
                    })

        # If no passives found, add null entries
        if not unique_passives:
            unique_passives = [
                {
                    "unique_passive_name": "null",
                    "description": "null",
                    "modifiers": []
                }
            ]

        # Build recipe components (we don't have this data from mlbb.io)
        build_path = []
        if item.get('recipe_components'):
            for component in item['recipe_components'].split(','):
                if component.strip():
                    build_path.append({"item_name": component.strip()})

        transformed_item = {
            "item_name": item['name'],
            "id": item_id,
            "icon": item['image_path'].split('/')[-1] if item.get('image_path') else f"{item['name'].lower().replace(' ', '-')}.png",
            "item_tier": "3",  # mlbb.io doesn't specify tier, assuming tier 3 for most
            "item_category": category,
            "data": [
                {
                    "cost": str(item['price_total']),
                    "summary": item['tags'].split(',')[0].title() if item.get('tags') else "",
                    "modifiers": [modifiers] if modifiers else [{}],
                    "active": [
                        {
                            "active_name": "null",
                            "description": "null",
                            "modifiers": []
                        }
                    ],
                    "passive": [
                        {
                            "passive_name": "null",
                            "description": "null",
                            "modifiers": []
                        }
                    ],
                    "unique_passive": unique_passives,
                    "build_path": build_path
                }
            ]
        }

        transformed['data'].append(transformed_item)

    return transformed


def transform_heroes(mlbb_heroes: List[Dict]) -> Dict:
    """
    Transform mlbb.io heroes to MLBB-API schema

    Basic info only - detailed skills will be merged separately
    """
    transformed = {
        "title": "hero-schema",
        "revdate": datetime.now().strftime("%Y%m%d"),
        "author": "p3hndrx",
        "source": "https://github.com/p3hndrx/MLBB-API",
        "data": []
    }

    # Add null hero entry first
    transformed['data'].append({
        "hero_name": "None",
        "mlid": "",
        "uid": "null",
        "id": "",
        "hero_icon": "null.png",
        "discordmoji": "<:null:852659015532150825>",
        "portrait": "",
        "release_year": "",
        "laning": [""],
        "class": "",
        "skills": []
    })

    # Sort heroes by ID for consistency
    sorted_heroes = sorted(mlbb_heroes, key=lambda x: x['id'])

    for hero in sorted_heroes:
        # Generate UID (lowercase, no spaces)
        uid = hero['hero_name'].lower().replace(' ', '-').replace("'", '')

        # Determine laning
        lane = hero.get('lane', '')
        if isinstance(lane, list):
            laning = lane
        elif lane:
            laning = [lane.lower()]
        else:
            laning = [""]

        # Determine class (role)
        role = hero.get('role', '')
        if isinstance(role, list):
            hero_class = ', '.join(role)
        elif role:
            hero_class = role
        else:
            hero_class = ""

        transformed_hero = {
            "hero_name": hero['hero_name'],
            "mlid": str(hero['id']),
            "uid": uid,
            "id": f"h{hero['id']:03d}",
            "hero_icon": f"{uid}.png",
            "discordmoji": "",  # We don't have this data
            "portrait": hero.get('img_src', ''),
            "release_year": "",  # We don't have this data
            "laning": laning,
            "class": hero_class,
            "skills": []  # Will be populated in phase 2
        }

        transformed['data'].append(transformed_hero)

    return transformed


def transform_emblems(main_emblems: List[Dict], ability_emblems: List[Dict]) -> Dict:
    """
    Transform mlbb.io emblems to MLBB-API schema

    New 2025 emblem system: 7 main emblems + 26 ability talents
    """
    transformed = {
        "title": "emblem-meta-final",
        "revdate": datetime.now().strftime("%Y%m%d"),
        "author": "p3hndrx",
        "source": "https://github.com/p3hndrx/MLBB-API",
        "data": []
    }

    # Process each main emblem
    for idx, emblem in enumerate(main_emblems, 1):
        emblem_name = emblem['name']

        # Parse attributes
        modifiers = {}
        for attr in emblem.get('attributes', []):
            # Parse format like "HP +275.00" or "Adaptive Attack +22.00"
            parts = attr.rsplit('+', 1)
            if len(parts) == 2:
                stat_name = parts[0].strip().lower().replace(' ', '_')
                stat_value = parts[1].strip()
                modifiers[stat_name] = stat_value

        # Find matching ability talents for this emblem
        # Abilities are stored separately, we'll add them as tier3 talents
        emblem_abilities = [a for a in ability_emblems if emblem_name.lower() in a.get('tags', '').lower()]

        tier3_talents = []
        for ability in emblem_abilities[:3]:  # Limit to 3 talents per emblem
            tier3_talents.append({
                "name": ability.get('name', ''),
                "icon": f"/talents/{ability.get('name', '').lower().replace(' ', '-')}.png",
                "modifiers": [],
                "passive_ability": ability.get('description', '')
            })

        # If no abilities found, add placeholder
        if not tier3_talents:
            tier3_talents = [
                {
                    "name": "Talent 1",
                    "icon": "/talents/placeholder.png",
                    "modifiers": [],
                    "passive_ability": ""
                }
            ]

        transformed_emblem = {
            "emblem_name": emblem_name,
            "icon": f"/emblems/{emblem_name.lower()}.png",
            "emblem_role": emblem_name.lower(),
            "id": f"{idx:03d}",
            "modifiers": [modifiers],
            "data": [
                {
                    "tier1": [],  # mlbb.io doesn't provide tier1/tier2 breakdown
                    "tier2": [],
                    "tier3": tier3_talents
                }
            ]
        }

        transformed['data'].append(transformed_emblem)

    return transformed


def main():
    """Main transformation workflow"""
    print("=" * 60)
    print("MLBB Data Transformation Script")
    print("=" * 60)

    # Load source data
    print("\n[1/6] Loading source data...")
    items_data = load_json('/tmp/mlbb-items-raw.json')
    heroes_data = load_json('/tmp/mlbb-heroes-raw.json')
    emblems_main = load_json('/tmp/mlbb-emblems-main.json')
    emblems_abilities = load_json('/tmp/mlbb-emblems-abilities.json')

    print(f"  - Items: {len(items_data['data'])} loaded")
    print(f"  - Heroes: {len(heroes_data['data'])} loaded")
    print(f"  - Main Emblems: {len(emblems_main['data'])} loaded")
    print(f"  - Emblem Abilities: {len(emblems_abilities['data'])} loaded")

    # Transform items
    print("\n[2/6] Transforming items...")
    transformed_items = transform_items(items_data['data'])
    print(f"  - Transformed {len(transformed_items['data'])} items")

    # Transform heroes
    print("\n[3/6] Transforming heroes...")
    transformed_heroes = transform_heroes(heroes_data['data'])
    print(f"  - Transformed {len(transformed_heroes['data'])} heroes (including null entry)")

    # Transform emblems
    print("\n[4/6] Transforming emblems...")
    transformed_emblems = transform_emblems(emblems_main['data'], emblems_abilities['data'])
    print(f"  - Transformed {len(transformed_emblems['data'])} emblems")

    # Save transformed data
    print("\n[5/6] Saving transformed data...")
    save_json('/var/www/sites/mlbb.site/MLBB-API/v1/item-meta-final.json', transformed_items)
    save_json('/var/www/sites/mlbb.site/MLBB-API/v1/hero-meta-final.json', transformed_heroes)
    save_json('/var/www/sites/mlbb.site/MLBB-API/v1/emblem-meta-final.json', transformed_emblems)

    print("\n[6/6] Transformation complete!")
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Items:   {len(transformed_items['data'])} items")
    print(f"  Heroes:  {len(transformed_heroes['data']) - 1} heroes (+ null)")
    print(f"  Emblems: {len(transformed_emblems['data'])} emblems")
    print("=" * 60)

    print("\nNext steps:")
    print("  1. Review the generated files in v1/")
    print("  2. Run hero detail enrichment (Phase 2) to add skill data")
    print("  3. Commit changes to git")


if __name__ == "__main__":
    main()
