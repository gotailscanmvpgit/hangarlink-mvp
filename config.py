import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this-in-prod'
    
    # Priority order for Database URI:
    # 1. DATABASE_URL (Standard)
    # 2. DATABASE_PRIVATE_URL (Railway Private)
    # 3. POSTGRES_URL (Alternative name)
    # 4. Local SQLite (fallback)
    raw_db_url = os.environ.get('DATABASE_URL') or \
                 os.environ.get('DATABASE_PRIVATE_URL') or \
                 os.environ.get('POSTGRES_URL')
    
    # Log all available environment keys (not values) for debugging
    print(f"DEBUG: Available Env Keys: {list(os.environ.keys())}")
    
    if raw_db_url:
        # Standardize for SQLAlchemy
        if raw_db_url.startswith("postgres://"):
            SQLALCHEMY_DATABASE_URI = raw_db_url.replace("postgres://", "postgresql://", 1)
        else:
            SQLALCHEMY_DATABASE_URI = raw_db_url
        DB_TYPE = "POSTGRESQL"
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///hangarlink.db'
        DB_TYPE = "SQLITE (EPHEMERAL - DATA WILL BE LOST ON REDEPLOY)"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ... rest of the config ...
    
    # Uploads
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Caching
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Stripe
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '').strip()
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '').strip()
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '').strip()
    
    # Application
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'

    # Airport Data (Loaded on startup in app.py)
    # Accessible via current_app.config['AIRPORT_COORDS']
    AIRPORT_COORDS = {} 

    # Aircraft Dimensions for Size Comparison Tool
    AIRCRAFT_SIZES = {
        'GA Aircraft': {
            'Cessna 172': {'length': 27.2, 'wingspan': 36.1, 'height': 8.9},
            'Piper PA-28 Cherokee': {'length': 23.3, 'wingspan': 30, 'height': 7.3},
            'Beechcraft Bonanza': {'length': 27.5, 'wingspan': 33.5, 'height': 8.5},
            'Cirrus SR22': {'length': 26, 'wingspan': 38.3, 'height': 8.9},
            'Mooney M20': {'length': 26.8, 'wingspan': 36.1, 'height': 8.3},
            'Diamond DA40': {'length': 26.5, 'wingspan': 39.4, 'height': 6.5},
            'Cessna 182 Skylane': {'length': 29, 'wingspan': 36, 'height': 9.3},
            'Piper PA-32 Saratoga': {'length': 28.2, 'wingspan': 36.2, 'height': 9.5},
            'Beechcraft Baron': {'length': 29.8, 'wingspan': 37.8, 'height': 9.8},
            'Cessna 206 Stationair': {'length': 28, 'wingspan': 36, 'height': 9.3},
            "Van's RV-10": {'length': 24.7, 'wingspan': 31.9, 'height': 8.7},
            'Pilatus PC-12': {'length': 47.3, 'wingspan': 53.4, 'height': 14},
            'Cessna 150': {'length': 23.9, 'wingspan': 33.4, 'height': 8.5},
            'Piper Cub': {'length': 22.5, 'wingspan': 35.3, 'height': 6.8},
            'Socata TB20': {'length': 25.3, 'wingspan': 32.8, 'height': 9.3},
            'Robinson R44': {'length': 29.4, 'wingspan': 33, 'height': 10.8},
            'Diamond DA42': {'length': 28.2, 'wingspan': 44, 'height': 8.2},
            'Cessna 310': {'length': 27, 'wingspan': 35.8, 'height': 10.5},
            'Mooney M20R Ovation': {'length': 26.8, 'wingspan': 36.1, 'height': 8.3},
            'Cirrus SR20': {'length': 26, 'wingspan': 38.3, 'height': 8.9},
            'Beechcraft King Air 90': {'length': 35.5, 'wingspan': 50.3, 'height': 14.8},
            "Van's RV-7": {'length': 20.2, 'wingspan': 25, 'height': 5.8},
            'Cessna 152': {'length': 24.2, 'wingspan': 33.4, 'height': 8.5},
            'Piper PA-18 Super Cub': {'length': 22.5, 'wingspan': 35.3, 'height': 6.8},
            'Socata TBM 930': {'length': 35.2, 'wingspan': 42.1, 'height': 14.3},
            'Diamond DA20 Katana': {'length': 23.5, 'wingspan': 35.7, 'height': 7.2},
            'Cessna 185 Skywagon': {'length': 27.3, 'wingspan': 36, 'height': 7.8},
            'Piper PA-34 Seneca': {'length': 28.8, 'wingspan': 38.9, 'height': 9.9},
            'Beechcraft Musketeer': {'length': 25.5, 'wingspan': 32.8, 'height': 8.3},
            "Van's RV-9": {'length': 20.5, 'wingspan': 28, 'height': 5.8},
            'Cessna 210 Centurion': {'length': 28.2, 'wingspan': 36.8, 'height': 9.8},
            'Piper PA-46 Malibu': {'length': 28.8, 'wingspan': 43, 'height': 11.3},
            'Cirrus SF50 Vision Jet': {'length': 30.9, 'wingspan': 38.7, 'height': 10.9},
            'Mooney M20J': {'length': 26.8, 'wingspan': 36.1, 'height': 8.3},
            'Diamond DA50 RG': {'length': 30.6, 'wingspan': 44.3, 'height': 9.2},
            'Cessna 208 Caravan': {'length': 37.6, 'wingspan': 52.1, 'height': 14.9},
            'Piper PA-24 Comanche': {'length': 25, 'wingspan': 36, 'height': 7.5},
            'Beechcraft Duchess': {'length': 29.1, 'wingspan': 38, 'height': 9.5},
            "Van's RV-14": {'length': 21.2, 'wingspan': 27, 'height': 8.2},
            'Cessna 140': {'length': 21.3, 'wingspan': 33.4, 'height': 6.2},
            'Piper PA-38 Tomahawk': {'length': 23.1, 'wingspan': 34, 'height': 9.1},
            'Socata TB10 Tobago': {'length': 25.4, 'wingspan': 32.8, 'height': 9.3},
            'Robinson R22': {'length': 28.8, 'wingspan': 25.3, 'height': 9},
            'Diamond DA62': {'length': 30.1, 'wingspan': 47.2, 'height': 9.3},
            'Cessna 340': {'length': 34.4, 'wingspan': 38.2, 'height': 12.6},
            'Piper PA-31 Navajo': {'length': 32.7, 'wingspan': 40.8, 'height': 13},
            'Beechcraft Sierra': {'length': 24.5, 'wingspan': 32.8, 'height': 8.5},
            "Van's RV-8": {'length': 21, 'wingspan': 24, 'height': 5.3},
            'Cessna 195': {'length': 27.4, 'wingspan': 42.1, 'height': 7.6},
            'Piper PA-44 Seminole': {'length': 27.6, 'wingspan': 38.6, 'height': 8.5},
            'Cirrus SR22T': {'length': 26, 'wingspan': 38.3, 'height': 8.9},
            'Mooney M20K': {'length': 26.8, 'wingspan': 36.1, 'height': 8.3},
            'Cessna 421 Golden Eagle': {'length': 36.5, 'wingspan': 41.2, 'height': 11.5},
            'Piper PA-60 Aerostar': {'length': 34.8, 'wingspan': 36.7, 'height': 12.1},
            'Beechcraft Duke': {'length': 33.4, 'wingspan': 39.2, 'height': 12.3},
            "Van's RV-6": {'length': 20.2, 'wingspan': 23, 'height': 5.8},
            'Cessna 177 Cardinal': {'length': 27.2, 'wingspan': 35.5, 'height': 8.6},
            'Piper PA-23 Apache': {'length': 31, 'wingspan': 37, 'height': 10.3},
            'Socata TB21 Trinidad': {'length': 25.3, 'wingspan': 32.8, 'height': 9.3},
            'Robinson R66': {'length': 38, 'wingspan': 33, 'height': 11.4},
            'Diamond DA20 Eclipse': {'length': 23.5, 'wingspan': 35.7, 'height': 7.2},
            'Cessna 120': {'length': 21, 'wingspan': 33.4, 'height': 6.2},
            'Piper PA-12 Super Cruiser': {'length': 22.7, 'wingspan': 35.5, 'height': 6.8},
            'Beechcraft Skipper': {'length': 24, 'wingspan': 30, 'height': 7.9},
            "Van's RV-12": {'length': 19.8, 'wingspan': 26.8, 'height': 8.3},
            'Cessna 188 Agwagon': {'length': 26, 'wingspan': 42, 'height': 7.8},
            'Piper PA-36 Pawnee Brave': {'length': 27.6, 'wingspan': 39.1, 'height': 7.5},
            'Cirrus SR20 G6': {'length': 26, 'wingspan': 38.3, 'height': 8.9},
            'Mooney M20M Bravo': {'length': 26.8, 'wingspan': 36.1, 'height': 8.3},
            'Cessna 414 Chancellor': {'length': 36.4, 'wingspan': 44.1, 'height': 11.5},
            'Piper PA-42 Cheyenne': {'length': 43.4, 'wingspan': 47.7, 'height': 14.9},
            'Beechcraft Starship': {'length': 46.1, 'wingspan': 54.5, 'height': 12.9},
            "Van's RV-3": {'length': 19.3, 'wingspan': 19.8, 'height': 5},
            'Cessna 170': {'length': 25, 'wingspan': 36, 'height': 6.5},
            'Piper PA-25 Pawnee': {'length': 24.8, 'wingspan': 36.2, 'height': 7.2},
            'Socata TBM 850': {'length': 34.9, 'wingspan': 41.6, 'height': 14.3},
            'Cessna 337 Skymaster': {'length': 29.8, 'wingspan': 38, 'height': 9.3},
            'Piper PA-30 Twin Comanche': {'length': 25, 'wingspan': 36, 'height': 8.2},
            'Beechcraft Travel Air': {'length': 25, 'wingspan': 37.8, 'height': 9.5},
            "Van's RV-4": {'length': 20.4, 'wingspan': 23, 'height': 5.3},
            'Cessna 175 Skylark': {'length': 26.5, 'wingspan': 36, 'height': 8.9},
            'Piper PA-20 Pacer': {'length': 20.5, 'wingspan': 29.3, 'height': 8.3},
            'Socata TB9 Tampico': {'length': 25.3, 'wingspan': 32.8, 'height': 9.3},
            'Cessna 404 Titan': {'length': 39.5, 'wingspan': 46.3, 'height': 13.3},
            'Piper PA-31P Pressurized Navajo': {'length': 32.7, 'wingspan': 40.8, 'height': 13},
            'Beechcraft Queen Air': {'length': 35.6, 'wingspan': 50.3, 'height': 14.2},
            'Cessna 336 Skymaster': {'length': 29.8, 'wingspan': 38, 'height': 9.3},
            'Piper PA-22 Tri-Pacer': {'length': 20.5, 'wingspan': 29.3, 'height': 8.3},
            'Socata TB30 Epsilon': {'length': 25.2, 'wingspan': 26, 'height': 8.8},
            'Beechcraft Sundowner': {'length': 25.7, 'wingspan': 33, 'height': 8.3},
            "Van's RV-9A": {'length': 20.5, 'wingspan': 28, 'height': 5.8},
            'Cessna 205': {'length': 28, 'wingspan': 36.8, 'height': 9.3},
            'Piper PA-28R Arrow': {'length': 24.7, 'wingspan': 35.5, 'height': 7.9},
            'Socata TB200 Tobago XL': {'length': 25.3, 'wingspan': 32.8, 'height': 9.3},
            'Cessna 303 Crusader': {'length': 30.2, 'wingspan': 39, 'height': 13.3},
            'Piper PA-34-200 Seneca I': {'length': 28.7, 'wingspan': 38.9, 'height': 9.9},
            'Beechcraft Baron 58': {'length': 29.8, 'wingspan': 37.8, 'height': 9.8},
            "Van's RV-7A": {'length': 20.2, 'wingspan': 25, 'height': 5.8},
            'Cessna 180 Skywagon': {'length': 25.9, 'wingspan': 36, 'height': 7.8},
            'Piper PA-46-350P Mirage': {'length': 28.8, 'wingspan': 43, 'height': 11.3},
            'Socata TBM 700': {'length': 34.9, 'wingspan': 41.6, 'height': 14.3},
            'Cessna 425 Corsair': {'length': 35.5, 'wingspan': 44.1, 'height': 12.9},
            'Piper PA-46-500TP Meridian': {'length': 29.6, 'wingspan': 43, 'height': 11.3},
            'Beechcraft King Air B200': {'length': 43.8, 'wingspan': 54.5, 'height': 15},
            "Van's RV-8A": {'length': 21, 'wingspan': 24, 'height': 5.3},
            'Piper PA-46R-350T Matrix': {'length': 28.8, 'wingspan': 43, 'height': 11.3},
            'Socata TBM 910': {'length': 35.2, 'wingspan': 42.1, 'height': 14.3},
            'Cessna 441 Conquest II': {'length': 39, 'wingspan': 39.4, 'height': 13.1},
            'Piper PA-60-700P Aerostar': {'length': 34.8, 'wingspan': 36.7, 'height': 12.1},
            'Beechcraft King Air 350': {'length': 46.7, 'wingspan': 57.9, 'height': 14.3},
            "Van's RV-12iS": {'length': 19.8, 'wingspan': 26.8, 'height': 8.3},
            'Piper PA-28-161 Warrior': {'length': 23.8, 'wingspan': 35, 'height': 7.3},
            'Cessna 340A': {'length': 34.4, 'wingspan': 38.2, 'height': 12.6},
            'Piper PA-31-350 Chieftain': {'length': 34.7, 'wingspan': 40.7, 'height': 13},
            'Beechcraft Baron G58': {'length': 29.8, 'wingspan': 37.8, 'height': 9.8},
            'Cessna 177B Cardinal': {'length': 27.2, 'wingspan': 35.5, 'height': 8.6},
            'Piper PA-23-250 Aztec': {'length': 31.2, 'wingspan': 37.2, 'height': 10.3},
            'Socata TBM 940': {'length': 35.2, 'wingspan': 42.1, 'height': 14.3},
            'Cessna 414A Chancellor': {'length': 36.4, 'wingspan': 44.1, 'height': 11.5},
            'Piper PA-46-600TP M600': {'length': 29.7, 'wingspan': 43, 'height': 11.3},
            'Beechcraft King Air C90GTx': {'length': 35.5, 'wingspan': 50.3, 'height': 14.3},
            "Van's RV-14A": {'length': 21.2, 'wingspan': 27, 'height': 8.2},
            'Cessna 210 Turbo Centurion': {'length': 28.2, 'wingspan': 36.8, 'height': 9.8},
            'Piper PA-28-181 Archer': {'length': 23.8, 'wingspan': 35, 'height': 7.3},
            'Socata TBM 900': {'length': 35.2, 'wingspan': 42.1, 'height': 14.3},
            'Diamond DA42-VI': {'length': 28.2, 'wingspan': 44, 'height': 8.2},
            'Cessna 172RG Cutlass': {'length': 27.2, 'wingspan': 36.1, 'height': 8.9},
            'Piper PA-32R Lance': {'length': 28.2, 'wingspan': 36.2, 'height': 9.5},
            'Socata TB21 Trinidad TC': {'length': 25.3, 'wingspan': 32.8, 'height': 9.3},
            'Cessna 402': {'length': 36.4, 'wingspan': 44.1, 'height': 11.5},
            'Piper PA-31T Cheyenne': {'length': 34.5, 'wingspan': 42.7, 'height': 12.7},
            'Beechcraft Baron 55': {'length': 26.8, 'wingspan': 37.8, 'height': 9.5},
            'Piper PA-46-310P Malibu': {'length': 28.8, 'wingspan': 43, 'height': 11.3},
            'Piper PA-23-150 Apache': {'length': 27, 'wingspan': 37, 'height': 10.3},
            'Beechcraft V35 Bonanza': {'length': 26.4, 'wingspan': 33.5, 'height': 7.7},
            "Van's RV-3B": {'length': 19.3, 'wingspan': 19.8, 'height': 5},
            'Piper PA-28-140 Cherokee Cruiser': {'length': 23.3, 'wingspan': 30, 'height': 7.3},
            'Diamond DA42 L360': {'length': 28.2, 'wingspan': 44, 'height': 8.2},
            'Piper PA-28-201T Turbo Arrow': {'length': 24.7, 'wingspan': 35.5, 'height': 7.9},
        },
        'Jets & Large Aircraft': {
            'Cessna Citation M2': {'length': 42.6, 'wingspan': 47.3, 'height': 13.9},
            'Cessna Citation Latitude': {'length': 62.3, 'wingspan': 72.3, 'height': 20.9},
            'Embraer Phenom 100': {'length': 42.1, 'wingspan': 40.3, 'height': 14.3},
            'Embraer Phenom 300': {'length': 51.3, 'wingspan': 52.2, 'height': 16.8},
            'HondaJet HA-420': {'length': 42.6, 'wingspan': 39.8, 'height': 14.9},
            'Learjet 75': {'length': 58, 'wingspan': 50.9, 'height': 14.1},
            'Pilatus PC-24': {'length': 55.2, 'wingspan': 55.8, 'height': 17.3},
            'Gulfstream G280': {'length': 66.8, 'wingspan': 63, 'height': 21.3},
            'Bombardier Challenger 350': {'length': 68.7, 'wingspan': 69, 'height': 20},
            'Cessna Citation Longitude': {'length': 73.2, 'wingspan': 68.9, 'height': 19.4},
            'Dassault Falcon 2000LXS': {'length': 66.3, 'wingspan': 70.2, 'height': 23.2},
            'Embraer Praetor 600': {'length': 67.9, 'wingspan': 70.5, 'height': 21},
            'Gulfstream G650ER': {'length': 99.8, 'wingspan': 98.2, 'height': 25.7},
            'Bombardier Global 7500': {'length': 111.1, 'wingspan': 104, 'height': 27},
            'Cessna Citation X+': {'length': 73.6, 'wingspan': 69.2, 'height': 19.2},
            'Dassault Falcon 8X': {'length': 80.3, 'wingspan': 86.2, 'height': 26.1},
            'Embraer Lineage 1000E': {'length': 118.9, 'wingspan': 94.2, 'height': 34.6},
            'Boeing BBJ 737-7': {'length': 110.3, 'wingspan': 117.4, 'height': 41.2},
            'Airbus ACJ319neo': {'length': 111, 'wingspan': 117.5, 'height': 38.6},
            'Cessna Citation Sovereign+': {'length': 63.5, 'wingspan': 72.4, 'height': 20.3},
            'Learjet 45': {'length': 57.6, 'wingspan': 47.8, 'height': 14.1},
            'Hawker 800XP': {'length': 51.2, 'wingspan': 54.3, 'height': 18.1},
            'Cessna Citation CJ4': {'length': 53.3, 'wingspan': 50.8, 'height': 15.4},
            'Phenom 300E': {'length': 51.3, 'wingspan': 52.2, 'height': 16.8},
            'Nextant 400XTi': {'length': 48.4, 'wingspan': 43.8, 'height': 13.8},
            'Cessna Citation XLS+': {'length': 52.5, 'wingspan': 56.3, 'height': 17.2},
            'Bombardier Learjet 60': {'length': 58.7, 'wingspan': 43.8, 'height': 14.7},
            'Gulfstream G150': {'length': 56.8, 'wingspan': 52.1, 'height': 18.1},
            'Dassault Falcon 50EX': {'length': 60.8, 'wingspan': 61.8, 'height': 22.9},
            'Cessna Citation Bravo': {'length': 47.8, 'wingspan': 51.8, 'height': 14.8},
        }
    }
