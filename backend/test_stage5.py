"""Stage 5: attribution codes, links and QR, TrustScore, saved creators, repeat campaigns and the ledger view."""
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "orange_test")
os.environ.setdefault("JWT_SECRET", "ci-test-secret")

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

import server


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(server, "db", AsyncMongoMockClient()["orange_stage5"])
    for key in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "PAYMENT_PROVIDER", "APP_ENV", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    with TestClient(server.app) as c:
        yield c


def auth(t):
    return {"Authorization": f"Bearer {t}"}


def signup(client, email, role):
    r = client.post("/api/auth/signup", json={"email": email, "password": "secret12", "role": role})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def setup_completed(client):
    ct = signup(client, "asha@x.com", "creator")
    bt = signup(client, "cafe@x.com", "business")
    creator = client.post("/api/creator/profile", headers=auth(ct), json={"name": "Asha Kulkarni", "location": "Baner, Pune", "niches": ["Food"], "rates": {"reelPrice": 3000}}).json()
    client.portal.call(server.db.creator_profiles.update_one, {"id": creator["id"]}, {"$set": {"instagramVerified": True, "instagramUsername": "asha.eats"}})
    client.post("/api/business/profile", headers=auth(bt), json={"brandName": "Third Wave Corner", "industry": "Food", "location": "Baner, Pune"})
    camp = client.post("/api/campaigns/", headers=auth(bt), json={"receiverId": creator["id"], "receiverType": "creator", "campaignType": "paid", "deliverables": "1 reel", "budget": 3000, "brief": "Cold brew reel"}).json()
    # No tracking before acceptance.
    assert client.get(f"/api/campaigns/{camp['id']}/tracking", headers=auth(bt)).status_code == 400
    client.patch(f"/api/campaigns/{camp['id']}/respond?action=accept", headers=auth(ct))
    order = client.post(f"/api/payments/campaigns/{camp['id']}/order", headers=auth(bt)).json()
    settled = client.post(f"/api/payments/simulated/{order['orderId']}/settle", headers=auth(bt)).json()
    client.post(f"/api/payments/campaigns/{camp['id']}/verify", headers=auth(bt), json=settled)
    client.post(f"/api/campaigns/{camp['id']}/submit-link?contentLink=https://instagram.com/reel/y", headers=auth(ct))
    client.post(f"/api/campaigns/{camp['id']}/verify-link", headers=auth(bt))
    client.post(f"/api/campaigns/{camp['id']}/complete", headers=auth(bt))
    return ct, bt, creator, camp


def test_tracking_link_qr_offer_and_redemption(client):
    ct, bt, creator, camp = setup_completed(client)
    t = client.get(f"/api/campaigns/{camp['id']}/tracking", headers=auth(bt)).json()
    assert t["couponCode"].startswith("ASHA-") and t["clicks"] == 0 and t["redemptions"] == 0
    # Same assets for the creator, and stable across calls.
    assert client.get(f"/api/campaigns/{camp['id']}/tracking", headers=auth(ct)).json()["couponCode"] == t["couponCode"]
    assert client.patch(f"/api/campaigns/{camp['id']}/tracking", headers=auth(ct), json={"offer": "x"}).status_code == 403
    client.patch(f"/api/campaigns/{camp['id']}/tracking", headers=auth(bt), json={"offer": "10% off any cold brew"})

    r = client.get(f"/api/r/{t['slug']}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].endswith(f"/o/{t['slug']}")
    qr = client.get(f"/api/r/{t['slug']}/qr.svg")
    assert qr.status_code == 200 and qr.headers["content-type"].startswith("image/svg+xml") and b"<svg" in qr.content
    offer = client.get(f"/api/offers/{t['slug']}").json()
    assert offer == {"brandName": "Third Wave Corner", "location": "Baner, Pune", "websiteUrl": "", "offer": "10% off any cold brew", "couponCode": t["couponCode"]}

    other = signup(client, "other@x.com", "business")
    assert client.post("/api/tracking/redeem", headers=auth(other), json={"code": t["couponCode"]}).status_code == 404
    red = client.post("/api/tracking/redeem", headers=auth(bt), json={"code": t["couponCode"].lower(), "amount": 450}).json()
    assert red["redemptions"] == 1 and red["clicks"] == 1 and red["redeemedValue"] == 450 and red["creatorName"] == "Asha Kulkarni"


def test_trust_score_is_new_until_three_completed(client):
    ct, bt, creator, camp = setup_completed(client)
    t = client.get(f"/api/trust/creator/{creator['id']}", headers=auth(bt)).json()
    assert t["isNew"] is True and t["score"] is None and t["completed"] == 1
    factors = {f["factor"]: f for f in t["factors"]}
    assert factors["onTime"]["value"] == 1.0  # submitted same day as payment, from recorded history
    assert factors["response"]["value"] == 1.0 and factors["completion"]["value"] == 1.0
    assert factors["rating"]["value"] is None

    # Two more completed collaborations through "Repeat campaign" make the score visible.
    last = camp
    for _ in range(2):
        rep = client.post(f"/api/campaigns/{last['id']}/repeat", headers=auth(bt))
        assert rep.status_code == 201, rep.text
        new = rep.json()
        assert new["status"] == "requested" and new["budget"] == 3000 and new["brief"] == "Cold brew reel"
        client.patch(f"/api/campaigns/{new['id']}/respond?action=accept", headers=auth(ct))
        order = client.post(f"/api/payments/campaigns/{new['id']}/order", headers=auth(bt)).json()
        settled = client.post(f"/api/payments/simulated/{order['orderId']}/settle", headers=auth(bt)).json()
        client.post(f"/api/payments/campaigns/{new['id']}/verify", headers=auth(bt), json=settled)
        client.post(f"/api/campaigns/{new['id']}/submit-link?contentLink=https://instagram.com/reel/z", headers=auth(ct))
        client.post(f"/api/campaigns/{new['id']}/verify-link", headers=auth(bt))
        client.post(f"/api/campaigns/{new['id']}/complete", headers=auth(bt))
        last = new
    t = client.get(f"/api/trust/creator/{creator['id']}", headers=auth(bt)).json()
    assert t["isNew"] is False and t["score"] == 100
    b = client.get(f"/api/trust/brand/{client.get('/api/business/profile', headers=auth(bt)).json()['id']}", headers=auth(ct)).json()
    assert b["completed"] == 3 and b["score"] == 100


def test_saved_creators_and_ledger(client):
    ct, bt, creator, camp = setup_completed(client)
    assert client.post(f"/api/business/saved/{creator['id']}", headers=auth(ct)).status_code == 403
    assert client.post(f"/api/business/saved/{creator['id']}", headers=auth(bt)).status_code == 201
    mine = client.get("/api/business/creators", headers=auth(bt)).json()
    assert len(mine) == 1
    row = mine[0]
    assert row["saved"] and row["name"] == "Asha Kulkarni" and row["completed"] == 1 and row["lastCompletedId"] == camp["id"]
    assert client.post(f"/api/campaigns/{camp['id']}/repeat", headers=auth(ct)).status_code == 403

    brand_ledger = client.get("/api/payments/ledger", headers=auth(bt)).json()
    assert [(e["type"], e["amount"], e["direction"]) for e in brand_ledger] == [("funded", 3000.0, "out")]
    creator_ledger = client.get("/api/payments/ledger", headers=auth(ct)).json()
    assert sorted((e["type"], e["amount"], e["direction"]) for e in creator_ledger) == [("commission", 300.0, "out"), ("payout_released", 2700.0, "in")]
    assert creator_ledger[0]["counterpart"] == "Third Wave Corner"
