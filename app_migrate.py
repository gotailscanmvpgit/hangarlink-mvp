from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE listings ADD COLUMN price_night FLOAT DEFAULT 0.0"))
        print("Added price_night column")
    except Exception as e:
        print(f"price_night column might exist: {e}")
        
    try:
        db.session.execute(text("ALTER TABLE listings ADD COLUMN min_stay_nights INTEGER DEFAULT 1"))
        print("Added min_stay_nights column")
    except Exception as e:
        print(f"min_stay_nights column might exist: {e}")
        
    for col, def_val in [
        ('door_type', 'TEXT DEFAULT NULL'),
        ('access_24_7', 'BOOLEAN DEFAULT 0'),
        ('is_heated', 'BOOLEAN DEFAULT 0'),
        ('battery_tender', 'BOOLEAN DEFAULT 0'),
        ('engine_heater', 'BOOLEAN DEFAULT 0'),
        ('snow_removal', 'BOOLEAN DEFAULT 0'),
        ('hurricane_tiedowns', 'BOOLEAN DEFAULT 0'),
        ('ramp_cam_url', 'TEXT DEFAULT NULL'),
        ('tail_height_clearance', 'FLOAT DEFAULT NULL'),
        ('nfpa_409_compliant', 'BOOLEAN DEFAULT 0'),
        ('floor_loading_pcn', 'TEXT DEFAULT NULL'),
        ('gpu_power_available', 'BOOLEAN DEFAULT 0')
    ]:
        try:
            db.session.execute(text(f"ALTER TABLE listings ADD COLUMN {col} {def_val}"))
            print(f"Added {col} column")
        except Exception as e:
            print(f"Skipped {col}: {e}")

    for col, def_val in [
        ('owner_signed', 'BOOLEAN DEFAULT 0'),
        ('renter_signed', 'BOOLEAN DEFAULT 0'),
        ('lease_pdf_path', 'TEXT DEFAULT NULL'),
        ('sign_token_owner', 'TEXT DEFAULT NULL'),
        ('sign_token_renter', 'TEXT DEFAULT NULL')
    ]:
        try:
            db.session.execute(text(f"ALTER TABLE bookings ADD COLUMN {col} {def_val}"))
            print(f"Added bookings {col} column")
        except Exception as e:
            print(f"Skipped bookings {col}: {e}")
            
    db.session.commit()
