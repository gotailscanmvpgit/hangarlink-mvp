"""
airport_coords.py — Zero-config airport lat/lon lookup.

Strategy (in order):
  1. Try to load static/data/airports.csv  (bundled or downloaded manually)
  2. Fall back to downloading from OurAirports CDN at startup
  3. Fall back to HARDCODED_COORDS dict of ~300 common US/Canada airports
     so the app always works even offline.

Usage:
    from airport_coords import get_coords
    lat, lon, found = get_coords('KJFK')   # → (40.6398, -73.7789, True)
    lat, lon, found = get_coords('ZZZZ')   # → (43.6532, -79.3832, False)  ← Toronto default
"""

from __future__ import annotations
import csv
import io
import logging
import os
import time
from pathlib import Path
from typing import Optional, Tuple, Dict

logger = logging.getLogger(__name__)

# ── Fallback coordinates for when CSV is unavailable ─────────────────────────
# ~300 most common US/Canada airports — covers the vast majority of HangarLink listings
HARDCODED_COORDS: dict[str, tuple[float, float]] = {
    # ── Major US Hubs ─────────────────────────────────────────────────────────
    "KATL": (33.6407, -84.4277),   # Atlanta
    "KORD": (41.9742, -87.9073),   # Chicago O'Hare
    "KLAX": (33.9425, -118.4081),  # Los Angeles
    "KDFW": (32.8998, -97.0403),   # Dallas/Fort Worth
    "KDEN": (39.8561, -104.6737),  # Denver
    "KJFK": (40.6398, -73.7789),   # New York JFK
    "KLGA": (40.7772, -73.8726),   # New York LaGuardia
    "KEWR": (40.6925, -74.1687),   # Newark
    "KSFO": (37.6190, -122.3750),  # San Francisco
    "KSEA": (47.4502, -122.3088),  # Seattle
    "KMIA": (25.7959, -80.2870),   # Miami
    "KLAS": (36.0840, -115.1537),  # Las Vegas
    "KPHX": (33.4342, -112.0116),  # Phoenix
    "KIAH": (29.9902, -95.3368),   # Houston Intercontinental
    "KHOU": (29.6454, -95.2789),   # Houston Hobby
    "KMSP": (44.8848, -93.2223),   # Minneapolis
    "KBOS": (42.3656, -71.0096),   # Boston
    "KDTW": (42.2124, -83.3534),   # Detroit
    "KPHL": (39.8719, -75.2411),   # Philadelphia
    "KFLL": (26.0726, -80.1527),   # Fort Lauderdale
    "KMCO": (28.4294, -81.3089),   # Orlando
    "KBWI": (39.1754, -76.6682),   # Baltimore/Washington
    "KIAD": (38.9531, -77.4565),   # Washington Dulles
    "KDCA": (38.8521, -77.0377),   # Washington Reagan
    "KSLC": (40.7884, -111.9778),  # Salt Lake City
    "KPDX": (45.5887, -122.5975),  # Portland
    "KSAN": (32.7336, -117.1897),  # San Diego
    "KTPA": (27.9755, -82.5332),   # Tampa
    "KSTL": (38.7487, -90.3700),   # St. Louis
    "KCLE": (41.4117, -81.8498),   # Cleveland
    "KPIT": (40.4915, -80.2329),   # Pittsburgh
    "KCVG": (39.0488, -84.6678),   # Cincinnati
    "KIND": (39.7173, -86.2944),   # Indianapolis
    "KCMH": (39.9980, -82.8919),   # Columbus
    "KMEM": (35.0424, -89.9767),   # Memphis
    "KNEW": (29.9934, -90.2581),   # New Orleans
    "MCIA": (29.9934, -90.2581),   # placeholder
    "KSAT": (29.5337, -98.4698),   # San Antonio
    "KAUS": (30.1975, -97.6664),   # Austin
    "KDAL": (32.8471, -96.8517),   # Dallas Love Field
    "KSJC": (37.3626, -121.9290),  # San Jose
    "KOAK": (37.7213, -122.2208),  # Oakland
    "KSNA": (33.6757, -117.8682),  # Orange County
    "KBUR": (34.2007, -118.3585),  # Burbank
    "KONT": (34.0560, -117.6012),  # Ontario CA
    "KSMF": (38.6954, -121.5908),  # Sacramento
    "KRNO": (39.4991, -119.7681),  # Reno
    "KPHF": (37.1319, -76.4930),   # Newport News
    "KRIC": (37.5052, -77.3197),   # Richmond
    "KNORFOLK": (36.8976, -76.0122), # Norfolk (using KORF)
    "KORF": (36.8976, -76.0122),   # Norfolk
    # ── GA hot spots ──────────────────────────────────────────────────────────
    "KVNY": (34.2098, -118.4900),  # Van Nuys
    "KPAO": (37.4611, -122.1150),  # Palo Alto
    "KHWD": (37.6589, -122.1217),  # Hayward
    "KCCR": (38.0085, -122.0557),  # Concord CA
    "KSQL": (37.5119, -122.2500),  # San Carlos
    "KSBD": (34.0954, -117.2350),  # San Bernardino
    "KHSP": (37.9513, -79.8334),   # Hot Springs VA
    "KFDK": (39.4176, -77.3743),   # Frederick MD
    "KGAI": (39.1683, -77.1660),   # Montgomery County MD
    "KDMN": (32.2623, -107.7213),  # Deming NM
    "KAEX": (31.3274, -92.5488),   # Alexandria LA
    "KFTW": (32.8199, -97.3623),   # Fort Worth Meacham
    "KAFW": (32.9876, -97.3188),   # Fort Worth Alliance
    "KEFD": (29.6073, -95.1588),   # Houston Ellington
    "KDVN": (41.6107, -90.5883),   # Davenport IA
    "KCID": (41.8842, -91.7108),   # Cedar Rapids
    "KDSM": (41.5340, -93.6631),   # Des Moines
    "KFAR": (46.9207, -96.8158),   # Fargo ND
    "KBIS": (46.7727, -100.7467),  # Bismarck ND
    "KGRB": (44.4851, -88.1296),   # Green Bay WI
    "KMSN": (43.1399, -89.3375),   # Madison WI
    "KMKE": (42.9472, -87.8966),   # Milwaukee
    "KGYY": (41.6163, -87.4128),   # Gary IN
    "KELP": (31.8072, -106.3776),  # El Paso
    "KABQ": (35.0402, -106.6090),  # Albuquerque
    "KTUS": (32.1161, -110.9410),  # Tucson
    "KFAT": (36.7762, -119.7181),  # Fresno
    "KBFL": (35.4337, -119.0568),  # Bakersfield
    "KSBA": (34.4262, -119.8404),  # Santa Barbara
    "KSMX": (34.8988, -120.4575),  # Santa Maria
    "KLGB": (33.8177, -118.1517),  # Long Beach
    "KTOA": (33.8033, -118.3395),  # Torrance
    "KPSP": (33.8297, -116.5067),  # Palm Springs
    "KTRK": (39.3196, -120.1396),  # Truckee
    "KSCK": (37.8942, -121.2385),  # Stockton
    "KMOD": (37.6258, -120.9544),  # Modesto
    "KWJF": (34.7411, -118.2193),  # Lancaster (General William J Fox)
    "KFUL": (33.8720, -117.9799),  # Fullerton
    # ── Alaska ────────────────────────────────────────────────────────────────
    "PANC": (61.1744, -149.9961),  # Anchorage
    "PAFA": (64.8154, -147.8561),  # Fairbanks
    "PAJN": (58.3550, -134.5763),  # Juneau
    "PADK": (51.8778, -176.6459),  # Adak
    # ── Hawaii ────────────────────────────────────────────────────────────────
    "PHNL": (21.3187, -157.9221),  # Honolulu
    "PHOG": (20.8986, -156.4305),  # Maui Kahului
    "PHKO": (19.7388, -156.0456),  # Kona
    # ── Canada ────────────────────────────────────────────────────────────────
    "CYYZ": (43.6772, -79.6306),   # Toronto Pearson
    "CYWG": (49.9100, -97.2399),   # Winnipeg
    "CYVR": (49.1939, -123.1844),  # Vancouver
    "CYUL": (45.4706, -73.7408),   # Montreal
    "CYYC": (51.1139, -114.0201),  # Calgary
    "CYEG": (53.3097, -113.5797),  # Edmonton
    "CYHZ": (44.8808, -63.5086),   # Halifax
    "CYOW": (45.3225, -75.6692),   # Ottawa
    "CYVQ": (65.2816, -126.7982),  # Norman Wells
    "CYTZ": (43.6278, -79.3961),   # Toronto Billy Bishop (Island)
    "CYQB": (46.7911, -71.3933),   # Quebec City
    "CYJT": (48.5442, -58.5500),   # Stephenville NL
    "CYFC": (45.8789, -66.5372),   # Fredericton NB
    "CYCD": (49.0547, -123.8697),  # Nanaimo BC
    "CYYJ": (48.6469, -123.4258),  # Victoria BC
    "CYOK": (50.6813, -104.0883),  # Broadview SK
    "CYQR": (50.4320, -104.6658),  # Regina SK
    "CYSM": (59.1833, -105.8417),  # Fort Smith NT
    "CYEV": (68.3042, -133.4831),  # Inuvik NT
    "CYED": (53.6753, -113.4644),  # Edmonton Villeneuve
    "CYWL": (52.1833, -122.0542),  # Williams Lake BC
    "CYXE": (52.1708, -106.6994),  # Saskatoon
    "CYZF": (62.4628, -114.4403),  # Yellowknife
    "CYXS": (53.8894, -122.6797),  # Prince George BC
    "CZGF": (49.0156, -122.7396),  # Abbotsford BC (regional)
    "CYXX": (49.0256, -122.3611),  # Abbotsford BC
    "CYVK": (50.1442, -110.7428),  # Brooks Airfield AB
    # ── Mexico (border airports) ──────────────────────────────────────────────
    "MMTJ": (32.5411, -116.9701),  # Tijuana
    "MMUN": (21.0365, -86.8771),   # Cancun
    "MMMX": (19.4363, -99.0721),   # Mexico City
    # ── Florida Snowbird Corridor ─────────────────────────────────────────────
    "KFMY": (26.5866, -81.8633),   # Page Field, Fort Myers FL
    "KPBI": (26.6832, -80.0956),   # Palm Beach International FL
    "KFXE": (26.1973, -80.1707),   # Fort Lauderdale Executive FL
    "KSPG": (27.7651, -82.6268),   # Albert Whitted, St Petersburg FL
    "KVNC": (27.0716, -82.4403),   # Venice Airport FL
    "KSEF": (27.3966, -81.3423),   # Sebring Regional FL
    "KLAL": (27.9889, -82.0186),   # Lakeland Linder (Sun 'n Fun) FL
    "KBCT": (26.3785, -80.1077),   # Boca Raton Airport FL
    "KOPF": (25.9073, -80.2783),   # Opa-locka Executive FL
    "KDAB": (29.1799, -81.0581),   # Daytona Beach FL
    "KSFB": (28.7776, -81.2375),   # Sanford Orlando FL
    "KOCF": (29.1726, -82.2242),   # Ocala FL
    "KGIF": (27.9006, -81.7534),   # Winter Haven FL
    "KEYW": (24.5561, -81.7595),   # Key West FL
    # ── Florida FAA LIDs (private / airpark) ─────────────────────────────────
    "60J":  (30.3866, -82.9374),   # Riverbend Airpark, FL
    "5FD5": (27.4831, -80.7217),   # Aero Acres Airpark, Okeechobee FL
    "39FD": (29.2697, -82.0917),   # Ancient Oaks Airstrip, Ocala FL
    "FA08": (28.0936, -81.4673),   # Rafter T Ranch, FL
    "X14":  (30.7003, -81.6581),   # Yulee Airport (Nassau Co.) FL
    "FD60": (30.2789, -82.6847),   # White Springs, FL
    "2FD3": (27.9833, -81.5322),   # Lakeview Airstrip, FL
    "FD29": (27.0561, -82.2064),   # Englewood Airstrip, FL
    # ── Ontario, Canada (regional / private) ─────────────────────────────────
    "CYHM": (43.1736, -79.9350),   # Hamilton John C. Munro, ON
    "CYKF": (43.4608, -80.3786),   # Waterloo Region, ON
    "CYKZ": (43.8628, -79.3703),   # Toronto Buttonville, ON
    "CYPQ": (44.2300, -78.3633),   # Peterborough, ON
    "CYOO": (43.9228, -78.8950),   # Oshawa, ON
    "CYLS": (44.7481, -76.3331),   # Perth / Lanark, ON
    "CYGK": (44.2253, -76.5967),   # Kingston Norman Rogers, ON
    "CYSN": (43.1917, -79.0567),   # Niagara District, ON
    "CZON": (44.9814, -74.4989),   # Cornwall, ON
    "CYBF": (44.5442, -79.9156),   # Collingwood (Blue Mtn), ON
    "CYHS": (44.8419, -79.2931),   # Muskoka, ON
    "CYFD": (44.3017, -79.0183),   # Borden / Barrie, ON
    # ── Popular GA (US) ──────────────────────────────────────────────────────
    "KOSH": (43.9844, -88.5570),   # Oshkosh Wittman (EAA AirVenture)
    "2NY":  (42.1400, -74.6300),   # Private, NY Catskill area
    "7NY4": (43.0311, -76.1597),   # Cato-Meridian, NY
    "3NY4": (42.5806, -76.7697),   # Ovid Airpark, NY
    "CA-0516": (49.0500, -122.3000), # Private strip, Fraser Valley BC
    "KANE": (45.1450, -93.2114),   # Anoka County, MN
}

# Default fallback when identifier not found (Toronto downtown)
DEFAULT_LAT = 43.6532
DEFAULT_LON = -79.3832

# ── Human-readable names for datalist suggestions ─────────────────────────────
KNOWN_AIRPORTS: dict[str, str] = {
    # Canada
    "CYTZ": "CYTZ — Billy Bishop, Toronto Island",
    "CYHM": "CYHM — Hamilton John C. Munro, ON",
    "CYYZ": "CYYZ — Toronto Pearson International",
    "CYOW": "CYOW — Ottawa Macdonald-Cartier",
    "CYVR": "CYVR — Vancouver International",
    "CYYC": "CYYC — Calgary International",
    "CYEG": "CYEG — Edmonton International",
    "CYKF": "CYKF — Waterloo Region, ON",
    "CYKZ": "CYKZ — Toronto Buttonville, ON",
    "CYOO": "CYOO — Oshawa Airport, ON",
    "CYSN": "CYSN — Niagara District, ON",
    "CYBF": "CYBF — Collingwood / Blue Mountain, ON",
    "CYHS": "CYHS — Muskoka Airport, ON",
    # USA — Florida Snowbird
    "KFMY": "KFMY — Page Field, Fort Myers FL",
    "KPBI": "KPBI — Palm Beach International FL",
    "KFXE": "KFXE — Fort Lauderdale Executive FL",
    "KLAL": "KLAL — Lakeland Linder (Sun 'n Fun) FL",
    "KSPG": "KSPG — Albert Whitted, St Petersburg FL",
    "KVNC": "KVNC — Venice Airport FL",
    "KSEF": "KSEF — Sebring Regional FL",
    "KMIA": "KMIA — Miami International FL",
    "KEYW": "KEYW — Key West International FL",
    "KDAB": "KDAB — Daytona Beach International FL",
    "KSFB": "KSFB — Orlando Sanford FL",
    # FAA LIDs (private/airpark)
    "60J":  "60J — Riverbend Airpark, FL (private)",
    "5FD5": "5FD5 — Aero Acres Airpark, Okeechobee FL",
    "39FD": "39FD — Ancient Oaks Airstrip, Ocala FL",
    "X14":  "X14 — Yulee Airport, Nassau Co. FL",
    # USA — Convention
    "KOSH": "KOSH — Oshkosh Wittman (EAA AirVenture) WI",
    # USA — General
    "KJFK": "KJFK — New York JFK",
    "KLAX": "KLAX — Los Angeles International",
    "KORD": "KORD — Chicago O'Hare",
    "KDEN": "KDEN — Denver International",
    "KSEA": "KSEA — Seattle-Tacoma International",
    "KBOS": "KBOS — Boston Logan",
    "2NY":  "2NY — Private strip, Catskills NY",
    "CA-0516": "CA-0516 — Private strip, Fraser Valley BC",
}

# ── In-memory cache ───────────────────────────────────────────────────────────
# _COORDS_CACHE storage format: {ICAO: (lat, lon, iso_region)}
_COORDS_CACHE: dict[str, tuple[float, float, str]] = {}
_CACHE_LOADED = False

CSV_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
CSV_LOCAL_PATH = Path(__file__).parent / "static" / "data" / "airports.csv"


def _load_csv_stream(stream: io.TextIOBase) -> dict[str, tuple[float, float, str]]:
    """Parse airports.csv and return {ICAO: (lat, lon, iso_region)} dict."""
    result: dict[str, tuple[float, float, str]] = {}
    reader = csv.DictReader(stream)
    for row in reader:
        # 'ident' is the primary key (FAA local code for US, ICAO for international)
        # 'icao_code' is the 4-letter ICAO code — prefer it when present
        icao = (row.get("icao_code") or "").strip().upper()
        ident = (row.get("ident") or "").strip().upper()
        iso_region = (row.get("iso_region") or "").strip().upper()
        
        # Clean iso_region (e.g. US-FL -> FL, CA-ON -> ON)
        state = iso_region.split("-")[-1] if "-" in iso_region else iso_region
        
        try:
            lat = float(row["latitude_deg"])
            lon = float(row["longitude_deg"])
        except (ValueError, KeyError):
            continue
        if icao:
            result[icao] = (lat, lon, state)
        if ident and ident not in result:
            result[ident] = (lat, lon, state)
    return result


def _load_from_file(path: Path) -> Optional[dict[str, tuple[float, float, str]]]:
    """Try to load from local CSV file."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            data = _load_csv_stream(f)
        logger.info(f"[AIRPORT-COORDS] loaded {len(data):,} airports from {path}")
        return data
    except Exception as exc:
        logger.warning(f"[AIRPORT-COORDS] could not read local CSV {path}: {exc}")
        return None


def _load_from_url(url: str) -> Optional[dict[str, tuple[float, float, str]]]:
    """Try to download CSV from OurAirports CDN."""
    import urllib.request
    try:
        logger.info(f"[AIRPORT-COORDS] downloading from {url} …")
        t0 = time.time()
        with urllib.request.urlopen(url, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
        elapsed = time.time() - t0
        data = _load_csv_stream(io.StringIO(raw))
        logger.info(f"[AIRPORT-COORDS] downloaded {len(data):,} airports in {elapsed:.1f}s")
        # Cache to disk for next startup
        CSV_LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        CSV_LOCAL_PATH.write_text(raw, encoding="utf-8")
        logger.info(f"[AIRPORT-COORDS] saved to {CSV_LOCAL_PATH} for future startups")
        return data
    except Exception as exc:
        logger.warning(f"[AIRPORT-COORDS] download failed: {exc}")
        return None


def load_airport_coords() -> None:
    """
    Load airport coordinates into the in-memory cache.
    Called once at app startup. Safe to call multiple times (no-op after first load).
    """
    global _COORDS_CACHE, _CACHE_LOADED
    if _CACHE_LOADED:
        return

    # 1. Try local file first (fast, no network)
    data = _load_from_file(CSV_LOCAL_PATH) if CSV_LOCAL_PATH.exists() else None

    # 2. Download if local file missing
    if data is None:
        data = _load_from_url(CSV_URL)

    # 3. Merge in hardcoded fallbacks (state is unknown 'US' or 'CA' for hardcoded)
    if data is None:
        logger.warning("[AIRPORT-COORDS] using hardcoded fallback for ~300 airports only")
        data = {}

    for k, v in HARDCODED_COORDS.items():
        if k not in data:
            # Guess country code from initial letter if state unknown
            country = "US" if k.startswith("K") else ("CA" if k.startswith("C") else "ZZ")
            data[k] = (v[0], v[1], country)
            
    _COORDS_CACHE = data
    _CACHE_LOADED = True
    logger.warning(f"[AIRPORT-COORDS] ready — {len(_COORDS_CACHE):,} airports indexed")


def get_coords(icao: str) -> Tuple[float, float, str, bool]:
    """
    Look up (lat, lon, state) for an ICAO code.

    Returns:
        (lat, lon, state, found) — if not found, returns Toronto default and found=False.

    Example:
        lat, lon, state, found = get_coords('KJFK')  # → (40.6398, -73.7789, 'NY', True)
        lat, lon, state, found = get_coords('ZZZZ')  # → (43.6532, -79.3832, 'ON', False)
    """
    if not _CACHE_LOADED:
        load_airport_coords()

    key = (icao or "").strip().upper()
    data = _COORDS_CACHE.get(key)
    if data:
        return data[0], data[1], data[2], True
    return DEFAULT_LAT, DEFAULT_LON, "ON", False
