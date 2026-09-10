import os

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('DB_NAME', 'orange_test')
os.environ.setdefault('JWT_SECRET', 'test-secret')
os.environ.setdefault('FRONTEND_URL', 'http://localhost:3000')
os.environ.setdefault('CORS_ORIGINS', 'http://localhost:3000')
os.environ.setdefault('RAZORPAY_KEY_ID', 'rzp_test_dummy')
os.environ.setdefault('RAZORPAY_KEY_SECRET', 'dummy')
os.environ.setdefault('INSTAGRAM_APP_ID', 'test-app')
os.environ.setdefault('INSTAGRAM_APP_SECRET', 'test-secret')

from server import app  # noqa: E402


def test_critical_routes_are_registered():
    paths = {route.path for route in app.routes}
    assert '/api/auth/instagram/connect' in paths
    assert '/api/auth/instagram/callback' in paths
    assert '/api/auth/instagram/status' in paths
    assert '/api/auth/instagram/disconnect' in paths
    assert '/api/payments/campaigns/{campaign_id}/order' in paths
    assert '/api/payments/campaigns/{campaign_id}/verify' in paths
    assert '/api/payments/razorpay/webhook' in paths
    assert '/api/campaigns/{campaign_id}/complete' in paths


def test_instagram_authorization_url_is_server_generated():
    from server import build_instagram_authorization_url

    url = build_instagram_authorization_url('unit-test-state')
    assert url.startswith('https://www.instagram.com/oauth/authorize?')
    assert 'client_id=test-app' in url
    assert 'state=unit-test-state' in url
    assert 'instagram_business_basic' in url
