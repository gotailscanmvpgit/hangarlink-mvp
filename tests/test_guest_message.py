"""
test_guest_message.py — pytest tests for guest (unauthenticated) messaging.
Verifies that:
  1. A guest can send a message via the contact form (no login required)
  2. Missing fields return a redirect (not a 500)
  3. The message actually persists in the database
  4. Anti-spam flagging works on suspicious content
"""
import pytest
from conftest import make_owner, make_listing
from models import Message


class TestGuestMessage:
    """Suite for the /contact-guest/<listing_id> route."""

    @pytest.fixture(autouse=True)
    def _setup(self, db):
        """Create an owner + listing for every test, then clean up."""
        self.owner = make_owner(db, username='guestmsg_owner',
                                email='gmowner@test.com')
        self.listing = make_listing(db, self.owner, icao='KJFK')
        yield
        # Cleanup messages first (FK constraint)
        Message.query.filter_by(listing_id=self.listing.id).delete()
        db.session.delete(self.listing)
        db.session.delete(self.owner)
        db.session.commit()

    def test_guest_message_success(self, client, db):
        """POST with valid email + message → 302 redirect + message in DB."""
        resp = client.post(
            f'/contact-guest/{self.listing.id}',
            data={
                'guest_email': 'guest@example.com',
                'message': 'Is this hangar still available?'
            },
            follow_redirects=False
        )
        # Should redirect (302) back to listing detail
        assert resp.status_code == 302
        assert f'/listing/{self.listing.id}' in resp.headers.get('Location', '')

        # Verify message persisted
        msg = Message.query.filter_by(
            listing_id=self.listing.id,
            receiver_id=self.owner.id,
            is_guest=True
        ).first()
        assert msg is not None, "Guest message was not saved to DB"
        assert 'guest@example.com' in msg.content
        assert msg.sender_id is None
        assert msg.guest_email == 'guest@example.com'

    def test_guest_message_missing_email(self, client):
        """POST without email → redirect, NOT a 500."""
        resp = client.post(
            f'/contact-guest/{self.listing.id}',
            data={'message': 'Hello!'},
            follow_redirects=False
        )
        assert resp.status_code == 302  # redirect, not 500

    def test_guest_message_missing_body(self, client):
        """POST without message body → redirect, NOT a 500."""
        resp = client.post(
            f'/contact-guest/{self.listing.id}',
            data={'guest_email': 'guest@example.com'},
            follow_redirects=False
        )
        assert resp.status_code == 302

    def test_guest_message_invalid_email(self, client):
        """POST with bad email format → redirect, NOT a 500."""
        resp = client.post(
            f'/contact-guest/{self.listing.id}',
            data={
                'guest_email': 'not-an-email',
                'message': 'Hello!'
            },
            follow_redirects=False
        )
        assert resp.status_code == 302

    def test_guest_message_spam_flagged(self, client, db):
        """Message containing spam keywords is flagged but still saved."""
        resp = client.post(
            f'/contact-guest/{self.listing.id}',
            data={
                'guest_email': 'spammer@example.com',
                'message': 'Send me bitcoin gift card please'
            },
            follow_redirects=False
        )
        assert resp.status_code == 302

        msg = Message.query.filter_by(
            guest_email='spammer@example.com',
            listing_id=self.listing.id
        ).first()
        assert msg is not None
        assert msg.is_flagged is True
        assert msg.flag_reason is not None

    def test_guest_message_nonexistent_listing(self, client):
        """POST to a listing that doesn't exist → 404."""
        resp = client.post(
            '/contact-guest/999999',
            data={
                'guest_email': 'guest@example.com',
                'message': 'Hello!'
            },
            follow_redirects=False
        )
        assert resp.status_code in (404, 429)  # 429 if rate-limited from prior tests
