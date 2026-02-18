# Fix Complete: Cache Import Added

The `NameError: name 'Cache' is not defined` has been resolved.

I have:
1.  Updated `app/extensions.py` to import and initialize `Cache`.
2.  Installed `flask-caching`.

## Next Steps

Please run the following commands in your terminal to apply the database changes:

```bash
# 1. Generate the migration for new indexes and caching support
flask db migrate -m "Add performance indexes and caching"

# 2. Apply the migration
flask db upgrade

# 3. (Optional) Verify the app starts
python run.py
```

If you see `sqlite3.OperationalError: table _alembic_tmp_ad already exists`, it means a previous migration failed. You may need to delete your local `hangarlink_local.db` and run `flask db upgrade` again to start fresh locally. In production (Postgres), this should not happen.
