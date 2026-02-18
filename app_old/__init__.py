from flask import Flask
from .extensions import db, login_manager, migrate, cache
from .models import User, Ad
import os
import random

def create_app(config_class='config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    login_manager.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login' # Blueprint prefix
    
    # Register Blueprints
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    # User Loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    # Context Processors
    @app.context_processor
    def inject_legal():
        try:
            with open('planning/legal-disclaimers.txt', 'r') as f:
                disclaimer = f.read()
        except FileNotFoundError:
            disclaimer = "Legal disclaimer not found."
            
        return {
            'legal_disclaimer': disclaimer,
            'app_version': 'v2.0.0', # Updated version
            'stripe_publishable_key': app.config['STRIPE_PUBLISHABLE_KEY']
        }
        
    @app.context_processor
    def inject_ads():
        """Inject active ads into all templates"""
        try:
            active_ads = Ad.query.filter_by(active=True).all()
        except Exception:
            active_ads = []
            
        # Organize by placement
        ads_by_placement = {
            'home_banner': [ad for ad in active_ads if ad.placement == 'home_banner'],
            'sidebar': [ad for ad in active_ads if ad.placement == 'sidebar'],
            'listing_detail': [ad for ad in active_ads if ad.placement == 'listing_detail']
        }
        # Provide a random ad for each spot if available
        context_ads = {}
        for place, ads in ads_by_placement.items():
            if ads:
                context_ads[place] = random.choice(ads)
        
        return dict(ads=context_ads)
        
    return app
