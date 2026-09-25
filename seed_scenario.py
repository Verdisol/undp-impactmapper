"""
seed_scenario.py — Evaluation scenario generator for GeoReport-DR.

Generates synthetic disaster reports around a real city to reproduce a
disaster scenario for dissertation evaluation.

Usage:
    python seed_scenario.py --n 200 --hours 24 --city beira
"""

import asyncio
import asyncpg
import os
import random
import uuid
import argparse
from datetime import datetime, timedelta

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

# Case study cities (lat, lng, name, crisis_nature)
CITIES = {
    "beira":   (-19.8436, 34.8389, "Beira, Mozambique",    "flood"),       # Cyclone Idai 2019
    "turkey":  (37.0000,  37.0000, "Kahramanmaraş, Turkey", "earthquake"), # 2023 Turkey-Syria
    "haiti":   (18.5392, -72.3288, "Port-au-Prince, Haiti", "earthquake"), # 2010 Haiti
    "harare":  (-17.8252, 31.0335, "Harare, Zimbabwe",     "flood"),       # Zimbabwe floods
    "california": (38.5000, -122.5000, "Sonoma, California", "wildfire"),  # Kincade Fire 2019
}

REPORT_TYPES = ["damage", "need", "hazard", "status"]
TYPE_WEIGHTS = [4, 3, 2, 1]
SEVERITIES = ["low", "medium", "high", "critical"]
SEV_WEIGHTS = [2, 4, 3, 1]

BUILDINGS = ["City Hall", "Central Hospital", "Primary School",
             "Market Plaza", "Community Centre", "Water Treatment Plant",
             "Bridge 4B", "Power Substation", "Bus Terminal",
             "Residential Block A", "Church of St. Mary", ""]

NOTES_TEMPLATES = [
    "Roof partially collapsed, family of {n} trapped on second floor.",
    "Water level rising, need evacuation assistance for {n} people.",
    "Road blocked by debris, {n} metres impassable.",
    "Fire visible from the east side, spreading toward residential area.",
    "Power line down, sparks visible, {n} households affected.",
    "Shelter operating at {n}% capacity, need supplies.",
    "No water supply for {n} days, residents requesting assistance.",
    "Structural crack in main wall, building unstable.",
]


async def seed(n_reports: int, hours: int, city_key: str, seed: int = 42):
    random.seed(seed)
    lat0, lng0, city_name, crisis = CITIES[city_key]
    conn = await asyncpg.connect(DATABASE_URL)

    users = ["seed_reporter_1", "seed_reporter_2", "seed_reporter_3",
             "seed_reporter_4", "seed_reporter_5"]

    try:
        now = datetime.now()
        for i in range(n_reports):
            # Spatial distribution: denser near center (Gaussian jitter)
            lat = lat0 + random.gauss(0, 0.02)
            lng = lng0 + random.gauss(0, 0.02)

            rtype = random.choices(REPORT_TYPES, weights=TYPE_WEIGHTS)[0]
            sev = random.choices(SEVERITIES, weights=SEV_WEIGHTS)[0]
            status = random.choices(
                ["pending", "verified", "assigned", "resolved"],
                weights=[5, 3, 2, 2]
            )[0]
            minutes_ago = random.randint(0, hours * 60)
            ts = (now - timedelta(minutes=minutes_ago)).isoformat()

            verified_at = None
            if status != "pending":
                verified_at = (now - timedelta(
                    minutes=minutes_ago - random.randint(2, 60))).isoformat()

            damage_level = {
                "damage": random.choice(["minimal", "partial", "complete"]),
                "need": "minimal",
                "hazard": "partial",
                "status": "minimal",
            }[rtype]

            infra = {
                "damage": random.choice(["residential", "commercial",
                                         "government", "utility", "transport"]),
                "need": "community",
                "hazard": "utility",
                "status": "community",
            }[rtype]

            notes = random.choice(NOTES_TEMPLATES).format(n=random.randint(2, 50))
            gps_acc = random.uniform(3, 25) if rtype == "damage" else None

            await conn.execute("""
                INSERT INTO reports (
                    report_uuid, report_type, severity, verification_status,
                    verified_at, report_source, gps_accuracy_m,
                    building_id, building_name, damage_level,
                    lat, lng, geom, location_text, infrastructure_type,
                    crisis_nature, debris, notes, username, timestamp,
                    is_current, synced
                ) VALUES (
                    $1, $2, $3, $4, $5, 'web', $6,
                    $7, $8, $9,
                    $10, $11,
                    ST_SetSRID(ST_MakePoint($11, $10), 4326),
                    $12, $13, $14, $15, $16, $17, $18, 1, 1
                )
            """,
                str(uuid.uuid4())[:8], rtype, sev, status, verified_at, gps_acc,
                f"bld_{i}", random.choice(BUILDINGS), damage_level,
                lat, lng, f"{city_name} area {i}",
                infra, crisis, "no", notes,
                random.choice(users), ts
            )

            if (i + 1) % 50 == 0:
                print(f"  Inserted {i + 1}/{n_reports} reports...")

        print(f"✅ Seeded {n_reports} reports around {city_name} ({crisis}).")
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200,
                        help="Number of reports to generate")
    parser.add_argument("--hours", type=int, default=24,
                        help="Spread reports over the last N hours")
    parser.add_argument("--city", type=str, default="beira",
                        choices=list(CITIES.keys()),
                        help="Case study city")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    asyncio.run(seed(args.n, args.hours, args.city, args.seed))
