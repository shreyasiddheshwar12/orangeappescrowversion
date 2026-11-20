"""End-to-end test of the core collaboration loop against an in-memory MongoDB.

Covers signup, onboarding field mapping, discovery, public profiles, request,
acceptance, payment (Razorpay calls stubbed), content link, verification,
completion and rating.
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "orange_test")
os.environ.setdefault("JWT_SECRET", "ci-test-secret")

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

import server
from orange.payments.razorpay import RazorpayProvider


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(server, "db", AsyncMongoMockClient()["orange_core_loop"])
    for key in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "PAYMENT_PROVIDER", "APP_ENV"):
        monkeypatch.delenv(key, raising=False)
    return TestClient(server.app)


def use_fake_razorpay(monkeypatch, handler):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_dummy")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "dummy")
    monkeypatch.setattr(RazorpayProvider, "_request", lambda self, method, path, **kw: handler(method, path, **kw))
    monkeypatch.setattr(RazorpayProvider, "verify_signature", lambda self, *a: True)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def signup(client, email, role):
    r = client.post("/api/auth/signup", json={"email": email, "password": "secret12", "role": role})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def make_creator(client, token):
    r = client.post("/api/creator/profile", headers=auth(token), json={
        "name": "Asha Kulkarni",
        "bio": "Pune food reels",
        "location": "Baner, Pune",
        "niches": ["Food"],
        "language": "Marathi",
        "followersCount": 18000,
        "mediaGallery": [{"id": "m1", "type": "image", "url": "https://example.com/a.jpg"}],
        "rates": {"reelPrice": 4000, "storyPrice": 1200, "postPrice": 2500, "bundlePrice": 6000},
    })
    assert r.status_code == 200, r.text
    return r.json()


def test_creator_onboarding_saves_nested_rates_and_no_invented_engagement(client):
    token = signup(client, "creator@x.com", "creator")
    profile = make_creator(client, token)
    assert profile["reelPrice"] == 4000
    assert profile["storyPrice"] == 1200
    assert profile["bundlePrice"] == 6000
    assert profile["followersCount"] == 18000
    assert profile["mediaGallery"][0]["url"] == "https://example.com/a.jpg"
    assert profile["engagementRate"] is None
    assert profile["engagementMeasured"] is False

    # Re-saving without prices keeps the stored prices instead of zeroing them.
    again = client.post("/api/creator/profile", headers=auth(token), json={"name": "Asha Kulkarni"}).json()
    assert again["reelPrice"] == 4000


def test_brand_onboarding_keeps_preferences(client):
    token = signup(client, "brand@x.com", "business")
    r = client.post("/api/business/profile", headers=auth(token), json={
        "brandName": "Cafe Baner", "industry": "Food & Beverage", "preferredNiches": ["Food"],
        "isOpenToBarter": False,
        "pastCollaborations": [{"campaignName": "Monsoon menu"}, {"campaignName": ""}],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["preferredNiches"] == ["Food"]
    assert body["barterEnabled"] is False
    assert [c["campaignName"] for c in body["pastCollaborations"]] == ["Monsoon menu"]


def test_full_paid_collaboration_loop(client, monkeypatch):
    creator_token = signup(client, "creator@x.com", "creator")
    brand_token = signup(client, "brand@x.com", "business")
    creator = make_creator(client, creator_token)
    client.post("/api/business/profile", headers=auth(brand_token), json={"brandName": "Cafe Baner", "industry": "Food"})

    # Discovery lists only verified creators.
    assert client.get("/api/marketplace/creators", headers=auth(brand_token)).json() == []
    run(server.db.creator_profiles.update_one({"id": creator["id"]}, {"$set": {"instagramVerified": True, "instagramUsername": "asha.eats"}}))
    listed = client.get("/api/marketplace/creators", headers=auth(brand_token)).json()
    assert [c["id"] for c in listed] == [creator["id"]]
    assert listed[0]["reelPrice"] == 4000 and listed[0]["engagementRate"] is None

    # Public profile is masked before payment.
    public = client.get(f"/api/marketplace/creators/{creator['id']}", headers=auth(brand_token)).json()
    assert public["identityUnlocked"] is False
    assert public["name"] != "Asha Kulkarni" and public["instagramUsername"] is None
    assert client.get("/api/marketplace/creators/missing", headers=auth(brand_token)).status_code == 404

    camp = client.post("/api/campaigns/", headers=auth(brand_token), json={
        "receiverId": creator["id"], "receiverType": "creator", "campaignType": "paid",
        "deliverables": "1 reel", "budget": 5000,
    }).json()
    assert camp["status"] == "requested" and camp["creatorPayout"] == 4500

    assert client.patch(f"/api/campaigns/{camp['id']}/respond?action=accept", headers=auth(creator_token)).json()["status"] == "accepted"

    # Stub Razorpay network calls.
    def fake_razorpay(method, path, **kwargs):
        if path == "/orders":
            return {"id": "order_1", "amount": kwargs["json"]["amount"]}
        if path.startswith("/payments/pay_1"):
            return {"order_id": "order_1", "amount": 500000, "status": "captured"}
        raise AssertionError(path)
    use_fake_razorpay(monkeypatch, fake_razorpay)

    order = client.post(f"/api/payments/campaigns/{camp['id']}/order", headers=auth(brand_token))
    assert order.status_code == 200, order.text
    assert order.json()["provider"] == "razorpay"
    verified = client.post(f"/api/payments/campaigns/{camp['id']}/verify", headers=auth(brand_token), json={
        "razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1", "razorpay_signature": "sig",
    }).json()
    assert verified["status"] == "paid" and verified["identityUnlocked"] is True

    unlocked = client.get(f"/api/marketplace/creators/{creator['id']}", headers=auth(brand_token)).json()
    assert unlocked["name"] == "Asha Kulkarni" and unlocked["instagramUsername"] == "asha.eats"

    msg = client.post(f"/api/messages/{camp['id']}", headers=auth(brand_token), json={"content": "Shoot on Saturday?"})
    assert msg.status_code == 201 and msg.json()["blocked"] is False

    assert client.post(f"/api/campaigns/{camp['id']}/submit-link?contentLink=https://instagram.com/reel/x", headers=auth(creator_token)).status_code == 200
    assert client.post(f"/api/campaigns/{camp['id']}/verify-link", headers=auth(brand_token)).json()["status"] == "link_verified"
    done = client.post(f"/api/campaigns/{camp['id']}/complete", headers=auth(brand_token)).json()
    assert done["status"] == "completed" and done["payoutStatus"] == "pending"

    rated = client.post(f"/api/campaigns/{camp['id']}/rate?rating=5&feedback=Great%20reel%20and%20on%20time", headers=auth(brand_token))
    assert rated.status_code == 200
    public = client.get(f"/api/marketplace/creators/{creator['id']}", headers=auth(brand_token)).json()
    assert public["rating"] == 5 and public["totalCollabs"] == 1 and len(public["ratings"]) == 1


def test_legacy_pay_route_uses_payment_order_flow(client, monkeypatch):
    creator_token = signup(client, "creator@x.com", "creator")
    brand_token = signup(client, "brand@x.com", "business")
    creator = make_creator(client, creator_token)
    client.post("/api/business/profile", headers=auth(brand_token), json={"brandName": "Cafe", "industry": "Food"})
    camp = client.post("/api/campaigns/", headers=auth(brand_token), json={
        "receiverId": creator["id"], "receiverType": "creator", "campaignType": "barter_product",
        "deliverables": "1 story", "productValue": 1000,
    }).json()
    client.patch(f"/api/campaigns/{camp['id']}/respond?action=accept", headers=auth(creator_token))
    seen = {}

    def fake_razorpay(method, path, **kwargs):
        seen["amount"] = kwargs["json"]["amount"]
        return {"id": "order_b", "amount": kwargs["json"]["amount"]}
    use_fake_razorpay(monkeypatch, fake_razorpay)
    r = client.post(f"/api/campaigns/{camp['id']}/pay", headers=auth(brand_token))
    assert r.status_code == 200, r.text
    assert seen["amount"] == 10000  # 10% barter fee of Rs 1,000, in paise


def test_simulated_provider_runs_full_lifecycle_without_keys(client):
    creator_token = signup(client, "creator@x.com", "creator")
    brand_token = signup(client, "brand@x.com", "business")
    creator = make_creator(client, creator_token)
    client.post("/api/business/profile", headers=auth(brand_token), json={"brandName": "Cafe", "industry": "Food"})
    assert client.get("/api/payments/provider", headers=auth(brand_token)).json()["simulated"] is True
    camp = client.post("/api/campaigns/", headers=auth(brand_token), json={
        "receiverId": creator["id"], "receiverType": "creator", "campaignType": "paid", "deliverables": "1 reel", "budget": 3000,
    }).json()
    client.patch(f"/api/campaigns/{camp['id']}/respond?action=accept", headers=auth(creator_token))
    order = client.post(f"/api/payments/campaigns/{camp['id']}/order", headers=auth(brand_token)).json()
    assert order["checkout"] == "simulated" and order["amount"] == 300000

    # Only the payer may settle; forged signatures are rejected.
    assert client.post(f"/api/payments/simulated/{order['orderId']}/settle", headers=auth(creator_token)).status_code == 403
    settled = client.post(f"/api/payments/simulated/{order['orderId']}/settle", headers=auth(brand_token)).json()
    forged = {**settled, "razorpay_signature": "0" * 64}
    assert client.post(f"/api/payments/campaigns/{camp['id']}/verify", headers=auth(brand_token), json=forged).status_code == 400
    verified = client.post(f"/api/payments/campaigns/{camp['id']}/verify", headers=auth(brand_token), json=settled).json()
    assert verified["status"] == "paid" and verified["simulated"] is True

    client.post(f"/api/campaigns/{camp['id']}/submit-link?contentLink=https://instagram.com/reel/y", headers=auth(creator_token))
    client.post(f"/api/campaigns/{camp['id']}/verify-link", headers=auth(brand_token))
    done = client.post(f"/api/campaigns/{camp['id']}/complete", headers=auth(brand_token)).json()
    assert done["payoutStatus"] == "released"

    entries = run(server.db.ledger_entries.find({"campaignId": camp["id"]}, {"_id": 0}).to_list(10))
    assert sorted((e["type"], e["amount"]) for e in entries) == [("commission", 300.0), ("funded", 3000.0), ("payout_released", 2700.0)]
    assert all(e["simulated"] for e in entries)


def test_simulated_payments_refused_in_production(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    brand_token = signup(client, "brand@x.com", "business")
    info = client.get("/api/payments/provider", headers=auth(brand_token)).json()
    assert info["configured"] is False


def test_chat_attachments_must_be_orange_uploads(client):
    creator_token = signup(client, "creator@x.com", "creator")
    brand_token = signup(client, "brand@x.com", "business")
    creator = make_creator(client, creator_token)
    client.post("/api/business/profile", headers=auth(brand_token), json={"brandName": "Cafe", "industry": "Food"})
    camp = client.post("/api/campaigns/", headers=auth(brand_token), json={
        "receiverId": creator["id"], "receiverType": "creator", "campaignType": "paid", "deliverables": "1 reel", "budget": 2000,
    }).json()
    run(server.db.campaigns.update_one({"id": camp["id"]}, {"$set": {"chatEnabled": True}}))
    bad = client.post(f"/api/messages/{camp['id']}", headers=auth(brand_token), json={"content": "", "attachments": [{"url": "https://evil.example/x.png", "type": "image"}]})
    assert bad.status_code == 400
    ok = client.post(f"/api/messages/{camp['id']}", headers=auth(brand_token), json={"content": "Moodboard", "attachments": [{"url": "http://localhost:8000/uploads/abc.png", "type": "image", "name": "mood.png"}]})
    assert ok.status_code == 201 and ok.json()["attachments"][0]["name"] == "mood.png"
    assert client.post(f"/api/messages/{camp['id']}", headers=auth(brand_token), json={"content": "   "}).status_code == 400
