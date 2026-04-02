import os
from app import app, db
from sqlalchemy import inspect

with app.app_context():
    print(f"DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    insp = inspect(db.engine)
    print(f"Tables: {insp.get_table_names()}")
    from models import Listing
    count = Listing.query.count()
    print(f"Listings count: {count}")
