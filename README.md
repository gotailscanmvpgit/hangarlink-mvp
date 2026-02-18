# HangarLink Clean 2026

Refactored clean version of the HangarLink MVP project.

## Structure

- **app/**: Main application package.
  - **__init__.py**: Application Factory (`create_app`).
  - **routes.py**: Main Blueprint with all routes.
  - **models.py**: Database models.
  - **extensions.py**: Flask extensions (db, login, migrate).
  - **templates/**: HTML templates.
  - **static/**: Static assets (CSS, JS, images).
- **migrations/**: Database migration scripts.
- **planning/**: Documentation and planning files.
- **config.py**: Configuration settings.
- **run.py**: Entry point for running the app.
- **requirements.txt**: Python dependencies.

## How to Run

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the application**:
    ```bash
    python run.py
    ```

## Deployment

This structure is ready for Railway/Render.
- `Procfile` uses `gunicorn --bind 0.0.0.0:$PORT run:app`.
- Ensure `DATABASE_URL` is set in environment variables.
