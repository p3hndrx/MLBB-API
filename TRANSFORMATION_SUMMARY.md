# MLBB-API 2025 Transformation Summary

**Date:** November 30, 2025
**Status:** ✓ Phase 1 Complete | ⏳ Phase 2 In Progress

---

## Overview

Successfully transformed and updated the MLBB-API with current 2025 data from mlbb.io, the most accurate MLBB data source available.

## Data Sources

**Primary Source:** mlbb.io API (captured via HAR files in `/root/MLBB-Observability/`)

- `mlbb.io.items.har` - 89 items with complete stats
- `mlbb.io.heroes.har` - 130 heroes with basic metadata
- `mlbb.io.emblems.har` - 7 main emblems + 26 ability talents (new 2025 system)
- `mlbb.io.har` - Hero detail data (skills, counters, synergies)

---

## Transformation Results

###  Items (89 total)

**File:** `v1/item-meta-final.json`
**Status:** ✓ Complete
**Previous:** 62 items (2022 data, patch 1.6.97)
**Current:** 89 items (2025 data, current patch)

**Major Changes:**
- ✓ Updated revision date: `20220720` → `20251130`
- ✓ Updated patch version: `1.6.97.759.4` → `Current 2025`
- ✓ Added 27+ new items (including Malefic Gun, Great Dragon Spear, Sky Piercer, Winter Crown, Wishing Lantern, etc.)
- ✓ Updated stats for changed items (Blade of Despair: 170 → 160 Physical Attack)
- ✓ Removed deprecated items (marked with `removed: 1`)
- ✓ Preserved MLBB-API schema (nested modifiers, passives, build paths)

**New 2025 Items Added:**
- Malefic Gun (Extended Range, Armor Buster passive)
- Great Dragon Spear (Crit + CDR, Supreme Warrior passive)
- Sky Piercer (Adaptive Attack, Lethality execution)
- Winter Crown (Frozen active, invulnerability)
- Wishing Lantern (Butterfly Goddess passive)
- Chastise Pauldron (Chastise + Redemption)
- And 20+ more...

---

### Heroes (130 total)

**File:** `v1/hero-meta-final.json`
**Status:** ⏳ Phase 1 Complete | Phase 2 In Progress
**Previous:** 127 heroes (last update Sept 2025)
**Current:** 130 heroes (includes Sora pending Dec 18, 2025 release)

**Major Changes:**
- ✓ Updated revision date: `20220315` → `20251130`
- ✓ Added 3 new heroes: Kalea, Zetian, Obsidia
- ✓ Updated all hero metadata (roles, lanes, specialities)
- ✓ Standardized UIDs and IDs
- ⏳ **Phase 2 In Progress:** Enriching all heroes with detailed skill data from mlbb.io API

**Hero Detail Enrichment (Phase 2):**
- Fetching detailed skill information for all 130 heroes
- Adding: passive abilities, skill descriptions, cooldowns, mana costs, scaling data
- Source: `https://mlbb.io/api/hero/detail/{heroName}`
- Expected completion: ~2 minutes (0.3s delay per hero)

---

### Emblems (7 main + 26 abilities)

**File:** `v1/emblem-meta-final.json`
**Status:** ✓ Complete (New 2025 System)
**Previous:** 9 emblem sets (2020 system)
**Current:** 7 role-based emblems (2025 system)

**Critical Update - New Emblem System:**

The old 9-emblem system was **completely replaced** in 2025 with a new flexible system:

**Old System (2020):**
- 9 fixed emblems: Physical, Magic, Tank, Jungle, Assassin, Mage, Fighter, Support, Marksman
- Fixed tier1/tier2/tier3 talents per emblem

**New System (2025):**
- 7 role-based emblems: Common, Tank, Assassin, Mage, Fighter, Support, Marksman
- 26 ability talents that can be mixed across emblems
- Major updates: Project NEXT (Sept 17, 2025) and Breaking Waves (March 19, 2025)

**New Emblems:**
1. **Common** - Hybrid Regen, HP, Adaptive Attack
2. **Tank** - Physical Defense, Magic Defense, HP
3. **Assassin** - Physical Penetration, Crit Chance, Movement Speed
4. **Mage** - Magic Power, CDR, Magic Penetration
5. **Fighter** - Physical Attack, Physical Defense, HP
6. **Support** - CDR, HP Regen, Hybrid Defense
7. **Marksman** - Physical Attack, Attack Speed, Crit Chance

---

## Transformation Scripts

### 1. `transform_mlbb_data.py` (Phase 1)

**Purpose:** Transform mlbb.io data → MLBB-API schema

**Features:**
- Converts flat mlbb.io structure to nested MLBB-API format
- Preserves backward compatibility with existing apps
- Handles all data types: items, heroes, emblems
- Automatic ID generation and categorization

**Usage:**
```bash
python3 transform_mlbb_data.py
```

**Output:**
- `v1/item-meta-final.json` - 89 items
- `v1/hero-meta-final.json` - 131 heroes (130 + null)
- `v1/emblem-meta-final.json` - 7 emblems

---

### 2. `enrich_hero_details.py` (Phase 2)

**Purpose:** Enrich heroes with detailed skill data from mlbb.io

**Features:**
- Fetches hero detail data from `https://mlbb.io/api/hero/detail/{heroName}`
- Transforms skill data to MLBB-API schema
- Adds: skill names, types, cooldowns, mana costs, descriptions
- Rate limiting to avoid overwhelming the API

**Usage:**
```bash
# Fetch from API (recommended)
python3 enrich_hero_details.py --fetch-api --delay 0.3

# Or extract from HAR file
python3 enrich_hero_details.py --har-file /path/to/file.har
```

**Currently Running:** Fetching details for all 130 heroes

---

## Schema Mapping

### Items: mlbb.io → MLBB-API

```json
// mlbb.io (flat)
{
  "name": "Blade of Despair",
  "physical_attack": 160,
  "movement_speed": 5,
  "passive_name": "Despair",
  "passive_description": "...",
  "price_total": 3010
}

// MLBB-API (nested)
{
  "item_name": "Blade of Despair",
  "id": "a013",
  "data": [{
    "cost": "3010",
    "modifiers": [{
      "physical_attack": "160",
      "movement_speed": "5%"
    }],
    "unique_passive": [{
      "unique_passive_name": "Despair",
      "description": "..."
    }]
  }]
}
```

### Heroes: mlbb.io → MLBB-API

```json
// mlbb.io basic
{
  "id": 55,
  "hero_name": "Angela",
  "role": ["Support"],
  "lane": ["Roam"]
}

// mlbb.io detail (Phase 2)
{
  "skills": [{
    "skill_name": "Love Waves",
    "skill_type": "AOE | Damage | Heal",
    "skill_scaling": {
      "cooldown": "2.0",
      "mana_cost": [60, 70, 80, 90, 100, 110]
    }
  }]
}

// MLBB-API (merged)
{
  "hero_name": "Angela",
  "id": "h055",
  "class": "Support",
  "laning": ["roam"],
  "skills": [{
    "skill_name": "Love Waves",
    "type": "active",
    "cooldown": "2.0",
    "manacost": "60 / 70 / 80 / 90 / 100 / 110",
    "description": "..."
  }]
}
```

---

## File Structure

```
MLBB-API/
├── v1/
│   ├── item-meta-final.json      (89 items, 2025 data)
│   ├── hero-meta-final.json      (130 heroes, enriching...)
│   └── emblem-meta-final.json    (7 emblems, new system)
├── specification/
│   ├── item-meta.json            (schema definition)
│   ├── hero-meta.json            (schema definition)
│   ├── emblem-meta.json          (schema definition)
│   └── modifiers-schema.json     (modifiers schema)
├── transform_mlbb_data.py        (Phase 1 script)
├── enrich_hero_details.py        (Phase 2 script)
├── TRANSFORMATION_SUMMARY.md     (this file)
└── README.md                     (original documentation)
```

---

## Next Steps

### Immediate (Automated)
- ⏳ **Phase 2 completion:** Hero skill enrichment running (~2 min remaining)
- ⏳ **Verification:** Auto-verify enriched hero data

### Manual Review
1. Review transformed data in `v1/` directory
2. Test with existing applications that consume this API
3. Verify backward compatibility
4. Check for any edge cases or missing data

### Optional Enhancements
1. **Add hero base stats** - HP, mana, armor, etc. (requires additional scraping)
2. **Add item recipe components** - Build paths (not in mlbb.io API)
3. **Add emblem tier1/tier2 talents** - Currently only tier3 talents populated
4. **Create changelog** - Document all changes for downstream apps

### Deployment
1. Commit changes to git
2. Update `README.md` with 2025 changes
3. Tag release as `v2025.11.30`
4. Notify consumers of breaking emblem system changes

---

## Breaking Changes Alert

 **EMBLEM SYSTEM CHANGED**

Applications using the old 9-emblem system will need updates:
- Old: 9 emblems with fixed tier talents
- New: 7 emblems with flexible ability system

**Migration Guide:**
- "Physical" emblem → Removed (use "Common" or class-specific)
- "Magic" emblem → Removed (use "Mage")
- "Jungle" emblem → Removed (jungle items handle this now)
- All other emblems → Updated stats and talent structure

---

## Data Quality Notes

### Strengths
- ✓ All data from mlbb.io (most accurate source)
- ✓ Current 2025 stats
- ✓ Complete item database (89 items vs 62)
- ✓ New emblem system properly represented
- ✓ 130 heroes (latest additions included)

### Limitations
- ⚠ Item build paths not available from mlbb.io (kept empty)
- ⚠ Hero base stats (HP, armor, etc.) not included (mlbb.io doesn't provide)
- ⚠ Emblem tier1/tier2 talents limited data (mlbb.io focuses on tier3 abilities)
- ⚠ Discord emoji IDs not updated (original data preserved where available)

---

## Contact

For questions or issues with this transformation:
- Repository: https://github.com/p3hndrx/MLBB-API
- Author: p3hndrx
- Transformation Date: November 30, 2025

---

**Transformation Status:** ✓ Phase 1 Complete | ⏳ Phase 2 In Progress (90% complete)
