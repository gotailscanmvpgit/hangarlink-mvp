"""
weather_service.py — Airport weather + Go/No-Go decision engine.

Uses OpenWeatherMap API to fetch current conditions at an airport's coordinates.
Returns a structured dict with temperature, wind, visibility, conditions,
and a Go/No-Go recommendation based on VFR pilot minimums.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# VFR Go/No-Go thresholds
WIND_CAUTION_KTS = 20      # Crosswind caution
WIND_NOGO_KTS = 30         # Dangerous for GA
VISIBILITY_MIN_MI = 3      # Below 3 SM = marginal VFR
GUST_NOGO_KTS = 35         # Gusts above 35 kts
STORM_KEYWORDS = {'thunderstorm', 'tornado', 'squall', 'hurricane', 'tropical storm'}
ADVERSE_KEYWORDS = {'rain', 'snow', 'sleet', 'freezing', 'ice', 'fog', 'mist', 'haze', 'drizzle'}


def fetch_airport_weather(lat: float, lon: float, icao: str = '') -> Optional[dict]:
    """
    Fetch current weather for airport coordinates.
    
    Returns dict with keys:
        temp_f, temp_c, wind_speed_kts, wind_gust_kts, wind_dir,
        visibility_mi, conditions, description, icon,
        go_nogo ('GO', 'CAUTION', 'NO-GO'),
        go_nogo_reasons: list[str],
        storm_risk: ('Low', 'Medium', 'High'),
        covered_suggestion: bool
    
    Returns None if API call fails or key not set.
    """
    api_key = os.environ.get('OPENWEATHER_API_KEY', '')
    if not api_key:
        logger.warning("[WEATHER] OPENWEATHER_API_KEY not set, returning simulated data")
        return _simulated_weather(icao)

    try:
        import requests
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key,
            'units': 'imperial'  # Fahrenheit, mph
        }
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code != 200:
            logger.warning(f"[WEATHER] API returned {resp.status_code}: {resp.text[:200]}")
            return _simulated_weather(icao)

        data = resp.json()
        return _parse_owm_response(data, icao)

    except ImportError:
        logger.warning("[WEATHER] 'requests' not installed, using simulated data")
        return _simulated_weather(icao)
    except Exception as e:
        logger.error(f"[WEATHER] Error fetching weather: {e}")
        return _simulated_weather(icao)


def _parse_owm_response(data: dict, icao: str) -> dict:
    """Parse OpenWeatherMap JSON into our standard format."""
    main = data.get('main', {})
    wind = data.get('wind', {})
    weather_list = data.get('weather', [{}])
    weather_main = weather_list[0] if weather_list else {}
    vis = data.get('visibility', 10000)  # meters

    temp_f = main.get('temp', 70)
    temp_c = round((temp_f - 32) * 5 / 9, 1)
    
    # Wind: OWM gives m/s for metric, mph for imperial
    wind_speed_mph = wind.get('speed', 0)
    wind_gust_mph = wind.get('gust', 0)
    wind_speed_kts = round(wind_speed_mph * 0.868976, 1)
    wind_gust_kts = round(wind_gust_mph * 0.868976, 1) if wind_gust_mph else 0
    wind_dir = wind.get('deg', 0)

    # Visibility: OWM gives meters, convert to statute miles
    visibility_mi = round(vis / 1609.34, 1)

    conditions = weather_main.get('main', 'Clear')
    description = weather_main.get('description', 'clear sky')
    icon = weather_main.get('icon', '01d')

    # Go/No-Go decision
    go_nogo, reasons = _evaluate_go_nogo(
        wind_speed_kts, wind_gust_kts, visibility_mi, conditions, description
    )

    # Storm risk assessment
    storm_risk, covered_suggestion = _assess_storm_risk(conditions, description, wind_gust_kts)

    return {
        'temp_f': round(temp_f),
        'temp_c': temp_c,
        'wind_speed_kts': wind_speed_kts,
        'wind_gust_kts': wind_gust_kts,
        'wind_dir': wind_dir,
        'visibility_mi': visibility_mi,
        'conditions': conditions,
        'description': description.title(),
        'icon': icon,
        'go_nogo': go_nogo,
        'go_nogo_reasons': reasons,
        'storm_risk': storm_risk,
        'covered_suggestion': covered_suggestion,
        'icao': icao,
        'source': 'live'
    }


def _evaluate_go_nogo(wind_kts, gust_kts, vis_mi, conditions, desc):
    """Evaluate Go/No-Go based on VFR minimums."""
    reasons = []
    status = 'GO'

    desc_lower = desc.lower()
    cond_lower = conditions.lower()

    # Thunderstorms = always NO-GO
    if any(kw in desc_lower or kw in cond_lower for kw in STORM_KEYWORDS):
        reasons.append('Active thunderstorm/severe weather')
        return 'NO-GO', reasons

    # Wind checks
    if wind_kts >= WIND_NOGO_KTS or gust_kts >= GUST_NOGO_KTS:
        reasons.append(f'Winds {wind_kts} kts (gusts {gust_kts} kts) exceed safe limits')
        return 'NO-GO', reasons
    elif wind_kts >= WIND_CAUTION_KTS:
        reasons.append(f'Winds {wind_kts} kts — crosswind caution')
        status = 'CAUTION'

    # Visibility
    if vis_mi < VISIBILITY_MIN_MI:
        reasons.append(f'Visibility {vis_mi} SM — below VFR min')
        return 'NO-GO', reasons
    elif vis_mi < 5:
        reasons.append(f'Visibility {vis_mi} SM — marginal')
        if status != 'NO-GO':
            status = 'CAUTION'

    # Adverse conditions
    if any(kw in desc_lower for kw in ADVERSE_KEYWORDS):
        reasons.append(f'Adverse conditions: {desc.title()}')
        if status == 'GO':
            status = 'CAUTION'

    if not reasons:
        reasons.append('Conditions favorable for VFR operations')

    return status, reasons


def _assess_storm_risk(conditions, description, gust_kts):
    """Assess storm risk level and whether covered parking is recommended."""
    desc_lower = description.lower()
    cond_lower = conditions.lower()

    if any(kw in desc_lower or kw in cond_lower for kw in STORM_KEYWORDS):
        return 'High', True
    
    if gust_kts >= 25 or any(kw in desc_lower for kw in {'rain', 'snow', 'sleet', 'freezing'}):
        return 'Medium', True
    
    if any(kw in desc_lower for kw in {'drizzle', 'mist', 'haze', 'fog', 'clouds', 'overcast'}):
        return 'Low', False

    return 'Low', False


def _simulated_weather(icao: str) -> dict:
    """
    Return simulated weather data when API key isn't set.
    Uses ICAO code to generate varied but deterministic conditions.
    """
    import hashlib
    
    # Deterministic hash to vary conditions by airport
    h = int(hashlib.md5(icao.encode()).hexdigest()[:8], 16)
    
    # Generate variety based on hash
    temp_f = 55 + (h % 40)  # 55-94°F
    wind_kts = 5 + (h % 20)  # 5-24 kts
    vis_mi = 5.0 + (h % 6)  # 5-10 mi
    
    conditions_list = [
        ('Clear', 'clear sky', '01d', 'GO'),
        ('Clouds', 'scattered clouds', '03d', 'GO'),
        ('Clouds', 'broken clouds', '04d', 'CAUTION'),
        ('Rain', 'light rain', '10d', 'CAUTION'),
        ('Thunderstorm', 'thunderstorm with rain', '11d', 'NO-GO'),
    ]
    
    idx = h % len(conditions_list)
    cond, desc, icon, _ = conditions_list[idx]
    
    go_nogo, reasons = _evaluate_go_nogo(wind_kts, 0, vis_mi, cond, desc)
    storm_risk, covered_suggestion = _assess_storm_risk(cond, desc, 0)
    
    return {
        'temp_f': temp_f,
        'temp_c': round((temp_f - 32) * 5 / 9, 1),
        'wind_speed_kts': wind_kts,
        'wind_gust_kts': 0,
        'wind_dir': (h % 36) * 10,
        'visibility_mi': vis_mi,
        'conditions': cond,
        'description': desc.title(),
        'icon': icon,
        'go_nogo': go_nogo,
        'go_nogo_reasons': reasons,
        'storm_risk': storm_risk,
        'covered_suggestion': covered_suggestion,
        'icao': icao,
        'source': 'simulated'
    }
