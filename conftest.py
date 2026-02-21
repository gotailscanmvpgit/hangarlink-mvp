"""
conftest.py — pytest fixtures for HangarLink MVP tests
Uses an in-memory SQLite database so tests never touch production data.
"""
import pytest
from werkzeug.security import generate_password_hash
from app import create_app
from extensions import db as _db
from models import User, Listing, Ad


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret-key-not-for-prod'
    WTF_CSRF_ENABLED = False
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 0
    STRIPE_SECRET_KEY = ''
    STRIPE_PUBLISHABLE_KEY = ''
    MAIL_USERNAME = ''
    LOGIN_DISABLED = False


@pytest.fixture(scope='session')
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope='session')
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


# ── Seed helpers ──────────────────────────────────────────────────────────────

def make_user(db, username='testpilot', email='pilot@test.com',
              password='Password1!', role='renter', is_admin=False):
    u = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
        is_admin=is_admin,
    )
    db.session.add(u)
    db.session.commit()
    return u


def make_owner(db, username='ownerpilot', email='owner@test.com',
               password='Password1!'):
    return make_user(db, username=username, email=email,
                     password=password, role='owner')


def make_listing(db, owner, icao='CYTZ', price=350.0, covered=True, size=1500):
    l = Listing(
        airport_icao=icao,
        price_month=price,
        covered=covered,
        size_sqft=size,
        description='Test hangar listing',
        owner_id=owner.id,
        status='Active',
        health_score=80,
    )
    db.session.add(l)
    db.session.commit()
    return l


@pytest.fixture
def seed_owner(db):
    u = make_owner(db)
    yield u
    db.session.delete(u)
    db.session.commit()


@pytest.fixture
def seed_listing(db, seed_owner):
    l = make_listing(db, seed_owner)
    yield l
    db.session.delete(l)
    db.session.commit()
