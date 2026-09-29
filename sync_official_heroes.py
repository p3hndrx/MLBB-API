#!/usr/bin/env python3
"""
Sync v1/hero-meta-final.json with the official Moonton GMS API
(the data source behind mobilelegends.com hero pages).

- Adds heroes that are missing locally (full entry).
- Refreshes class, laning, speciality and skills for every hero.
- Adds official attributes, lore and curated relations as extra fields.
- Keeps hand-maintained fields: hero_icon, discordmoji, portrait, uid,
  release_year, and the counters/synergies lists (which hold 10 heroes each;
  the official relations only list 2-4).

Usage:
    python sync_official_heroes.py              # dry run: print what would change
    python sync_official_heroes.py --write      # update v1/hero-meta-final.json

New heroes need a Discord emoji and release year; pass them on the command line:
    python sync_official_heroes.py --write --emoji 133=<:hirara:1554601826068860938> --year 133=2026
"""
import argparse
import json
import re
import sys
import time
from datetime import date

import requests

HERO_FILE = "v1/hero-meta-final.json"
SOURCE_URL = "https://api.gms.moontontech.com/api/gms/source/2669606/2756564"
# The API's firewall rejects the default python-requests User-Agent.
HEADERS = {
    "Content-Type": "application/json;charset=UTF-8",
    "x-lang": "en",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
}
LANES = {
    "exp lane": "exp lane",
    "jungling": "jungle",
    "mid lane": "mid lane",
    "gold lane": "gold lane",
    "roaming": "roam",
}


def fetch_official_heroes() -> dict:
    """Return {hero_id: record data} for every hero in the official database."""
    heroes, page = {}, 1
    while True:
        body = {"pageSize": 20, "pageIndex": page, "filters": [], "sorts": [], "object": []}
        resp = requests.post(SOURCE_URL, headers=HEADERS, json=body, timeout=60)
        resp.raise_for_status()
        data = resp.json()["data"]
        for rec in data["records"]:
            heroes[rec["data"]["hero_id"]] = rec["data"]
        if not data["records"] or len(heroes) >= data["total"]:
            return heroes
        page += 1
        time.sleep(0.3)


def strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def parse_cd_cost(value: str) -> tuple:
    cd = re.search(r"CD:\s*([\d.]+)", value or "")
    cost = re.search(r"Mana Cost:\s*([\d.]+)", value or "")
    return (f"{float(cd.group(1)):.1f}" if cd else "null",
            cost.group(1) if cost else "null")


def build_skills(hero: dict) -> list:
    """Flatten all skill lists (forms/weapons), dropping repeats of the same skill."""
    skills, seen = [], set()
    for skill_list in hero.get("heroskilllist", []):
        for s in skill_list.get("skilllist", []):
            if s["skillid"] in seen:
                continue
            seen.add(s["skillid"])
            cooldown, manacost = parse_cd_cost(s.get("skillcd&cost", ""))
            skills.append({
                "skill_name": s["skillname"].strip(),
                "skill_icon": s.get("skillicon", ""),
                "type": "passive" if not skills else "active",
                "cooldown": cooldown,
                "manacost": manacost,
                "description": strip_html(s.get("skilldesc", "")),
                "tags": [t["tagname"] for t in s.get("skilltag", []) if t.get("tagname")],
            })
    return skills


def build_relations(record: dict) -> dict:
    rel = record.get("relation") or {}

    def ids(key):
        return [i for i in rel.get(key, {}).get("target_hero_id", []) if i]

    return {
        "synergy": {"heroids": ids("assist"), "description": rel.get("assist", {}).get("desc", "")},
        "strong_against": {"heroids": ids("strong"), "description": rel.get("strong", {}).get("desc", "")},
        "weak_against": {"heroids": ids("weak"), "description": rel.get("weak", {}).get("desc", "")},
    }


def official_fields(record: dict) -> dict:
    hero = record["hero"]["data"]
    durability, offense, control, difficulty = (int(x) for x in hero["abilityshow"])
    lanes = [LANES[l.lower()] for l in hero.get("roadsortlabel", []) if l]
    return {
        "class": ", ".join(c for c in hero.get("sortlabel", []) if c),
        "laning": [", ".join(lanes)],
        "speciality": [s for s in hero.get("speciality", []) if s],
        "skills": build_skills(hero),
        "attributes": {
            "durability": durability,
            "offense": offense,
            "control_effects": control,
            "difficulty": difficulty,
        },
        "lore": hero.get("story", ""),
        "relations": build_relations(record),
    }


def same_set(a: str, b: str) -> bool:
    """True if two comma-separated lists hold the same items in any order."""
    split = lambda s: {x.strip().lower() for x in (s or "").split(",") if x.strip()}
    return split(a) == split(b)


def new_hero_entry(hero_id: int, record: dict, names: dict, emoji: str, year: str) -> dict:
    hero = record["hero"]["data"]
    uid = re.sub(r"[^a-z0-9]", "", hero["name"].lower())
    fields = official_fields(record)
    rel = fields["relations"]
    return {
        "hero_name": hero["name"],
        "mlid": str(hero_id),
        "uid": uid,
        "id": f"h{hero_id}",
        "hero_icon": f"{uid}.png",
        "discordmoji": emoji,
        "portrait": hero.get("head", ""),
        "release_year": year,
        "laning": fields["laning"],
        "class": fields["class"],
        "skills": fields["skills"],
        "speciality": fields["speciality"],
        # Same meaning as the existing lists: counters = heroes that counter this hero.
        "counters": [{"heroid": i, "heroname": names.get(i, "")} for i in rel["weak_against"]["heroids"]],
        "synergies": [{"heroid": i, "heroname": names.get(i, "")} for i in rel["synergy"]["heroids"]],
        "attributes": fields["attributes"],
        "lore": fields["lore"],
        "relations": rel,
    }


def parse_overrides(pairs: list) -> dict:
    out = {}
    for pair in pairs or []:
        hero_id, value = pair.split("=", 1)
        out[int(hero_id)] = value
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--write", action="store_true", help="write changes to the hero file")
    p.add_argument("--emoji", action="append", metavar="ID=EMOJI", help="Discord emoji for a new hero")
    p.add_argument("--year", action="append", metavar="ID=YEAR", help="release year for a hero")
    args = p.parse_args()
    emojis, years = parse_overrides(args.emoji), parse_overrides(args.year)

    with open(HERO_FILE, encoding="utf-8") as f:
        meta = json.load(f)
    official = fetch_official_heroes()
    names = {hid: rec["hero"]["data"]["name"] for hid, rec in official.items()}
    print(f"Official heroes: {len(official)} | local heroes: {sum(1 for h in meta['data'] if h['mlid'])}")

    local_ids = set()
    for hero in meta["data"]:
        if not hero["mlid"]:
            continue  # "None" placeholder entry
        hid = int(hero["mlid"])
        local_ids.add(hid)
        record = official.get(hid)
        if not record:
            print(f"  ! {hero['hero_name']} (mlid {hid}) not in official data; left unchanged")
            continue
        fields = official_fields(record)
        # Keep the local ordering when only the order differs.
        if same_set(hero.get("class"), fields["class"]):
            fields["class"] = hero["class"]
        if same_set((hero.get("laning") or [""])[0], fields["laning"][0]):
            fields["laning"] = hero["laning"]
        if set(hero.get("speciality") or []) == set(fields["speciality"]):
            fields["speciality"] = hero["speciality"]
        changed = [k for k in ("class", "laning", "speciality") if hero.get(k) != fields[k]]
        if [s["skill_name"] for s in hero.get("skills", [])] != [s["skill_name"] for s in fields["skills"]]:
            changed.append("skills")
        if changed:
            print(f"  ~ {hero['hero_name']}: {', '.join(changed)}")
        hero.update(fields)
        if hid in years:
            hero["release_year"] = years[hid]

    for hid in sorted(set(official) - local_ids):
        entry = new_hero_entry(hid, official[hid], names, emojis.get(hid, ""), years.get(hid, ""))
        meta["data"].append(entry)
        print(f"  + {entry['hero_name']} (mlid {hid}): {entry['class']} / {entry['laning'][0]}, "
              f"{len(entry['skills'])} skills")

    meta["revdate"] = date.today().strftime("%Y%m%d")
    if not args.write:
        print("\nDry run. Re-run with --write to save.")
        return
    with open(HERO_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)
        f.write("\n")
    print(f"\nWrote {HERO_FILE} ({len(meta['data'])} entries, revdate {meta['revdate']})")


if __name__ == "__main__":
    sys.exit(main())
