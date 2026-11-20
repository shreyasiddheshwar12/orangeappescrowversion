"""Growth Assistant tests: deterministic matching, the full run with and without Claude, and the approval gate."""
import os
import time

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "orange_test")
os.environ.setdefault("JWT_SECRET", "ci-test-secret")

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

import server
from orange.growth import capabilities, llm
from orange.growth.matching import score_creator


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(server, "db", AsyncMongoMockClient()["orange_growth"])
    for key in ("ANTHROPIC_API_KEY", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "PAYMENT_PROVIDER", "APP_ENV"):
        monkeypatch.delenv(key, raising=False)
    with TestClient(server.app) as c:  # keep one event loop alive so background runs finish
        yield c


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def signup(client, email, role):
    r = client.post("/api/auth/signup", json={"email": email, "password": "secret12", "role": role})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def creator(client, email, name, niche, location, reel, language="English"):
    token = signup(client, email, "creator")
    r = client.post("/api/creator/profile", headers=auth(token), json={"name": name, "location": location, "niches": [niche], "language": language, "rates": {"reelPrice": reel, "storyPrice": 500, "postPrice": 800}})
    assert r.status_code in (200, 201), r.text
    profile = r.json()
    client.portal.call(server.db.creator_profiles.update_one, {"id": profile["id"]}, {"$set": {"instagramVerified": True, "instagramUsername": "@" + name.lower().replace(" ", "_")}})
    return profile


def brand(client):
    token = signup(client, "cafe@example.com", "business")
    r = client.post("/api/business/profile", headers=auth(token), json={
        "brandName": "Third Wave Corner", "industry": "Food", "location": "Baner, Pune", "preferredNiches": ["Food"],
        "objectives": ["More footfall"], "targetAudience": "College students", "monthlyBudget": 15000, "products": "Cold brew and sandwiches",
    })
    assert r.status_code in (200, 201), r.text
    return token


def wait_status(client, token, run_id, wanted, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        run = client.get(f"/api/growth/runs/{run_id}", headers=auth(token)).json()
        if run["status"] in wanted:
            return run
        time.sleep(0.05)
    raise AssertionError(f"run stuck in {run['status']}: {run.get('error')}")


def test_matching_scores_only_known_factors():
    c = {"niche": "Food", "niches": ["Food"], "location": "Baner, Pune", "reelPrice": 4000, "language": "Marathi", "paidCollabsEnabled": True}
    s = score_creator(c, {"niches": ["Food"], "location": "Baner, Pune", "campaignType": "paid", "budgetPerCreator": 4500})
    factors = {b["factor"]: b for b in s["breakdown"]}
    assert factors["engagement"]["value"] is None and factors["trust"]["value"] is None and factors["language"]["value"] is None
    assert s["coverage"] == 25 + 20 + 20 + 5
    assert s["score"] == 100
    far = score_creator({**c, "location": "Andheri, Mumbai", "reelPrice": 9000}, {"niches": ["Food"], "location": "Baner, Pune", "campaignType": "paid", "budgetPerCreator": 4500})
    assert far["score"] < s["score"]


def test_growth_run_rules_engine_end_to_end(client):
    near = creator(client, "c1@example.com", "Sneha Joshi", "Food", "Baner, Pune", 4000)
    creator(client, "c2@example.com", "Kabir Shah", "Food", "Andheri, Mumbai", 9000)
    creator(client, "c3@example.com", "Ira Kulkarni", "Fashion", "Baner, Pune", 3000)
    token = brand(client)
    assert client.get("/api/growth/status", headers=auth(token)).json()["aiConfigured"] is False

    r = client.post("/api/growth/runs", headers=auth(token), json={"goal": "More college students visiting this month", "budget": 15000})
    assert r.status_code == 201, r.text
    run = wait_status(client, token, r.json()["id"], {"awaiting_approval", "failed"})
    assert run["status"] == "awaiting_approval", run.get("error")
    assert [s["status"] for s in run["steps"]] == ["done"] * 4
    assert all(s["engine"] == "rules" for s in run["steps"])

    plan = run["outputs"]["marketing_planner"]
    assert plan["budgetPerCreator"] * plan["creatorCount"] <= 15000
    shortlist = run["outputs"]["creator_matching"]["creators"]
    names = [c["name"] for c in shortlist]
    assert "Ira Kulkarni" not in names  # wrong niche is never recommended
    assert shortlist[0]["name"] == "Sneha Joshi" and shortlist[0]["instagramUsername"] == "@sneha_joshi"
    assert all(b["reason"] for b in shortlist[0]["breakdown"])

    # Only businesses can use the assistant.
    creator_token = signup(client, "c9@example.com", "creator")
    assert client.post("/api/growth/runs", headers=auth(creator_token), json={"goal": "hello there"}).status_code == 403

    bad = client.post(f"/api/growth/runs/{run['id']}/approve", headers=auth(token), json={"creatorIds": ["not-on-list"]})
    assert bad.status_code == 400

    ok = client.post(f"/api/growth/runs/{run['id']}/approve", headers=auth(token), json={"creatorIds": [near["id"]]})
    assert ok.status_code == 200, ok.text
    done = wait_status(client, token, run["id"], {"completed", "failed"})
    assert done["status"] == "completed", done.get("error")
    launch = done["outputs"]["campaign_assistant"]
    assert len(launch["sent"]) == 1 and not launch["failed"]

    outgoing = client.get("/api/campaigns/outgoing", headers=auth(token)).json()
    assert len(outgoing) == 1 and outgoing[0]["status"] == "requested"
    stored = client.portal.call(server.db.campaigns.find_one, {"id": outgoing[0]["id"]})
    assert stored["growthCampaignId"] == done["growthCampaignId"]
    assert stored["brief"]
    growth = client.portal.call(server.db.growth_campaigns.find_one, {"id": done["growthCampaignId"]})
    assert growth["campaignIds"] == [outgoing[0]["id"]]


def test_growth_run_with_claude_is_validated(client, monkeypatch):
    creator(client, "c1@example.com", "Sneha Joshi", "Food", "Baner, Pune", 4000)
    token = brand(client)
    monkeypatch.setattr(llm, "configured", lambda: True)

    async def fake(system, prompt, schema, effort="medium"):
        if schema is capabilities.BusinessRead:
            return schema(summary="A café in Baner.", audience="Students", sellingPoints=["Cold brew"], gaps=[], suggestedNiches=["Food", "Space travel"])
        if schema is capabilities.Plan:
            # Over budget and with a niche Orange doesn't have: both must be corrected.
            return schema(campaignName="Study break", objective="More students", approach="Reels", campaignType="paid", creatorCount=3, budgetPerCreator=20000, deliverables="1 reel", timeline="2 weeks", contentIdeas=["Exam-week combo"], kpis=["Redemptions"], niches=["Food", "Made up"])
        if schema is capabilities.Briefs:
            return schema(items=[])
        raise AssertionError(schema)

    monkeypatch.setattr(llm, "structured", fake)
    r = client.post("/api/growth/runs", headers=auth(token), json={"goal": "More college students visiting this month", "budget": 15000})
    run = wait_status(client, token, r.json()["id"], {"awaiting_approval", "failed"})
    assert run["status"] == "awaiting_approval", run.get("error")
    assert run["outputs"]["business_intelligence"]["suggestedNiches"] == ["Food"]
    plan = run["outputs"]["marketing_planner"]
    assert plan["engine"] == "claude" and plan["niches"] == ["Food"]
    assert plan["budgetPerCreator"] * plan["creatorCount"] <= 15000
    # No completed history: the analyst answers from data without calling Claude.
    assert run["outputs"]["performance_analyst"]["engine"] == "rules"


def test_failed_ai_step_shows_on_timeline(client, monkeypatch):
    token = brand(client)
    monkeypatch.setattr(llm, "configured", lambda: True)

    async def broken(*a, **k):
        raise llm.LLMError("The AI service is busy. Try again in a minute.")

    monkeypatch.setattr(llm, "structured", broken)
    r = client.post("/api/growth/runs", headers=auth(token), json={"goal": "More college students visiting"})
    run = wait_status(client, token, r.json()["id"], {"failed", "awaiting_approval"})
    assert run["status"] == "failed" and "busy" in run["error"]
    assert [s["status"] for s in run["steps"]] == ["failed", "skipped", "skipped", "skipped"]
