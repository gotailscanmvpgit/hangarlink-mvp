import os
import sys
import json
import logging
import requests
from datetime import datetime

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
INSTANTLY_API_KEY = os.environ.get('INSTANTLY_API_KEY')
INSTANTLY_API_BASE = "https://api.instantly.ai/api/v1"
DOMAIN_TO_WARMUP = "tryhangarlinks.com"
ACCOUNT_EMAIL = "no-reply@tryhangarlinks.com"
TEST_EMAIL = "test@tryhangarlinks.com"

# Safety toggle: If True, do not make real API calls
DEV_MODE = os.environ.get('FLASK_DEBUG', '1') == '1'

def get_headers():
    if not INSTANTLY_API_KEY and not DEV_MODE:
        logger.error("INSTANTLY_API_KEY is missing from environment variables.")
        sys.exit(1)
    return {
        "Authorization": f"Bearer {INSTANTLY_API_KEY}",
        "Content-Type": "application/json"
    }

def get_account_id():
    """Fetch the specific email account ID from Instantly to target."""
    if DEV_MODE:
        logger.info(f"[DEV MODE] Simulating fetching account ID for {ACCOUNT_EMAIL}")
        return "simulated_account_id_12345"
    
    url = f"{INSTANTLY_API_BASE}/account/list"
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        accounts = response.json()
        for account in accounts:
            if account.get('email') == ACCOUNT_EMAIL:
                return account.get('id')
        logger.error(f"Account {ACCOUNT_EMAIL} not found in Instantly.")
        return None
    except Exception as e:
        logger.error(f"Failed to fetch account ID: {e}")
        return None

def configure_warmup(account_id):
    """Configure warmup settings: gradual volume, spam recovery, tracking."""
    payload = {
        "warmup_enabled": True,
        "daily_limit": 50, # Start at 50/day
        "ramp_up_increment": 10, # Add 10 per day to ramp up to 200+ by week 3
        "spam_recovery": True, # Automatically rescue emails from spam
        "custom_tracking_domain": f"track.{DOMAIN_TO_WARMUP}",
        "reply_rate": 30 # 30% of warmup emails will receive simulated replies
    }
    
    if DEV_MODE:
        logger.info(f"[DEV MODE] Simulating warmup configuration for Account {account_id}")
        logger.info(f"[DEV MODE] Payload: {json.dumps(payload, indent=2)}")
        return True

    url = f"{INSTANTLY_API_BASE}/account/{account_id}/warmup/settings"
    try:
        response = requests.patch(url, headers=get_headers(), json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully configured warmup settings for {DOMAIN_TO_WARMUP}.")
        return True
    except Exception as e:
        logger.error(f"Failed to configure warmup: {e}")
        return False

def check_health(account_id):
    """Monitor domain score and pause if it drops below 90."""
    if DEV_MODE:
        logger.info(f"[DEV MODE] Simulating health check for Account {account_id}")
        simulated_stats = {"health_score": 98, "sent_today": 42, "bounces": 0}
        logger.info(f"Health Stats: Score={simulated_stats['health_score']}, Sent Today={simulated_stats['sent_today']}, Bounces={simulated_stats['bounces']}")
        return simulated_stats

    url = f"{INSTANTLY_API_BASE}/account/{account_id}/warmup/stats"
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        stats = response.json()
        
        score = stats.get('health_score', 100)
        logger.info(f"Current Health Score: {score}")
        logger.info(f"Emails Sent Today: {stats.get('sent_today', 0)}")
        logger.info(f"Bounce Rate: {stats.get('bounce_rate_percent', 0)}%")
        
        if score < 90:
            logger.warning(f"Health score dropped to {score}! Pausing warmup and campaigns to protect domain reputation.")
            pause_campaigns(account_id)
            
        return stats
    except Exception as e:
        logger.error(f"Failed to check health: {e}")
        return None

def pause_campaigns(account_id):
    """Pause sending if health drops to protect the domain."""
    payload = {"status": "paused"}
    if DEV_MODE:
        logger.warning(f"[DEV MODE] Simulating pausing campaigns for Account {account_id} due to low health score.")
        return True
        
    url = f"{INSTANTLY_API_BASE}/account/{account_id}/status"
    try:
        requests.patch(url, headers=get_headers(), json=payload, timeout=10)
        logger.info("Successfully paused account sending.")
        return True
    except Exception as e:
        logger.error(f"Failed to pause campaigns: {e}")
        return False

def send_test_email(account_id):
    """Send a singular sample text email to verify connection."""
    payload = {
        "to": TEST_EMAIL,
        "subject": "Warmup Diagnostics Test #1",
        "body": "This is an automated test ensuring the Instantly API connection and SMTP pipeline are healthy."
    }
    
    if DEV_MODE:
        logger.info(f"[DEV MODE] Simulating test email from Account {account_id} to {TEST_EMAIL}")
        logger.info(f"[DEV MODE] Subject: {payload['subject']}")
        return True
        
    url = f"{INSTANTLY_API_BASE}/account/{account_id}/send"
    try:
        response = requests.post(url, headers=get_headers(), json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully sent test email to {TEST_EMAIL}.")
        return True
    except Exception as e:
        logger.error(f"Failed to send test email: {e}")
        return False

def main():
    print(f"\n{'='*60}")
    print(f"🚀 tryhangarlinks.com - Domain Warmup Automation")
    print(f"{'='*60}")
    
    if DEV_MODE:
        logger.info("Running in DEV_MODE. No real API calls will be made.")
    elif not INSTANTLY_API_KEY:
        logger.error("INSTANTLY_API_KEY is required to run in production mode.")
        sys.exit(1)
        
    account_id = get_account_id()
    if not account_id:
        logger.error("Could not proceed without a valid account ID.")
        sys.exit(1)
        
    logger.info("Step 1: Configuring optimal warmup settings...")
    configure_warmup(account_id)
    
    logger.info("\nStep 2: Checking health and daily stats...")
    check_health(account_id)
    
    logger.info("\nStep 3: Dispatching diagnostic test email...")
    send_test_email(account_id)
    
    print(f"\n{'='*60}")
    print(f"✅ Daily Warmup Routine Complete")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
