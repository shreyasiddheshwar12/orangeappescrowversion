"""Routes for attribution (codes, links, QR), TrustScore, saved creators, repeat campaigns and the ledger view."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, Field

from . import tracking, trust


class OfferUpdate(BaseModel):
    offer: str = Field(max_length=140)


class Redeem(BaseModel):
    code: str = Field(min_length=3, max_length=40)
    amount: Optional[float] = Field(default=None, ge=0)


def build_router(*, get_db: Callable, get_current_user: Callable, ensure_party: Callable, brand_user_id: Callable, creator_user_id: Callable,
                 create_request: Callable, backend_url: Callable[[], str], frontend_url: Callable[[], str]) -> APIRouter:
    r = APIRouter()

    def link_for(t: dict) -> dict:
        base = backend_url().rstrip("/")
        return {**t, "url": f"{base}/api/r/{t['slug']}", "qrUrl": f"{base}/api/r/{t['slug']}/qr.svg"}

    async def campaign_for(campaign_id: str, user: dict) -> dict:
        c = await get_db().campaigns.find_one({"id": campaign_id}, {"_id": 0})
        if not c:
            raise HTTPException(status_code=404, detail="Campaign not found")
        ensure_party(c, user)
        return c

    async def names(c: dict) -> tuple[str, str]:
        db = get_db()
        cp = await db.creator_profiles.find_one({"userId": creator_user_id(c)}, {"_id": 0, "name": 1})
        bp = await db.brand_profiles.find_one({"userId": brand_user_id(c)}, {"_id": 0, "brandName": 1})
        return (cp or {}).get("name", ""), (bp or {}).get("brandName", "")

    # --- Attribution -------------------------------------------------------
    @r.get("/campaigns/{campaign_id}/tracking")
    async def get_tracking(campaign_id: str, user=Depends(get_current_user)):
        c = await campaign_for(campaign_id, user)
        if c["status"] not in tracking.TRACKABLE:
            raise HTTPException(status_code=400, detail="Tracking starts once the creator accepts")
        creator_name, _ = await names(c)
        t = await tracking.ensure(get_db(), {"id": c["id"], "brandUserId": brand_user_id(c), "creatorUserId": creator_user_id(c)}, creator_name)
        return {**link_for(t), **await tracking.stats(get_db(), t["id"])}

    @r.patch("/campaigns/{campaign_id}/tracking")
    async def set_offer(campaign_id: str, body: OfferUpdate, user=Depends(get_current_user)):
        c = await campaign_for(campaign_id, user)
        if brand_user_id(c) != user["id"]:
            raise HTTPException(status_code=403, detail="Only the business sets the offer")
        await get_db().tracking_links.update_one({"campaignId": campaign_id}, {"$set": {"offer": body.offer.strip()}})
        return await get_tracking(campaign_id, user)

    @r.get("/r/{slug}")
    async def follow(slug: str):
        t = await get_db().tracking_links.find_one({"slug": slug}, {"_id": 0})
        if not t:
            raise HTTPException(status_code=404, detail="Link not found")
        await tracking.record(get_db(), t, "click")
        return RedirectResponse(f"{frontend_url().rstrip('/')}/o/{slug}", status_code=302)

    @r.get("/r/{slug}/qr.svg")
    async def qr(slug: str):
        t = await get_db().tracking_links.find_one({"slug": slug}, {"_id": 0})
        if not t:
            raise HTTPException(status_code=404, detail="Link not found")
        return Response(tracking.qr_svg(link_for(t)["url"]), media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})

    @r.get("/offers/{slug}")
    async def offer(slug: str):
        """Public page data for customers. Shows the business and the code, never the creator's identity."""
        t = await get_db().tracking_links.find_one({"slug": slug}, {"_id": 0})
        if not t:
            raise HTTPException(status_code=404, detail="Offer not found")
        b = await get_db().brand_profiles.find_one({"userId": t["brandUserId"]}, {"_id": 0})
        b = b or {}
        return {"brandName": b.get("brandName", ""), "location": b.get("location", ""), "websiteUrl": b.get("websiteUrl", ""), "offer": t.get("offer", ""), "couponCode": t["couponCode"]}

    @r.post("/tracking/redeem")
    async def redeem(body: Redeem, user=Depends(get_current_user)):
        code = body.code.strip().upper()
        t = await get_db().tracking_links.find_one({"couponCode": code}, {"_id": 0})
        if not t or t["brandUserId"] != user["id"]:
            raise HTTPException(status_code=404, detail="That code isn't one of yours")
        await tracking.record(get_db(), t, "redeem", amount=body.amount)
        c = await get_db().campaigns.find_one({"id": t["campaignId"]}, {"_id": 0})
        creator_name, _ = await names(c)
        return {"campaignId": t["campaignId"], "couponCode": code, "creatorName": creator_name if c.get("identityUnlocked") else "Creator", **await tracking.stats(get_db(), t["id"])}

    # --- TrustScore --------------------------------------------------------
    @r.get("/trust/creator/{profile_id}")
    async def creator_trust(profile_id: str, user=Depends(get_current_user)):
        p = await get_db().creator_profiles.find_one({"id": profile_id}, {"_id": 0, "userId": 1})
        if not p:
            raise HTTPException(status_code=404, detail="Creator not found")
        return await trust.creator_trust(get_db(), p["userId"])

    @r.get("/trust/brand/{profile_id}")
    async def brand_trust(profile_id: str, user=Depends(get_current_user)):
        p = await get_db().brand_profiles.find_one({"id": profile_id}, {"_id": 0, "userId": 1})
        if not p:
            raise HTTPException(status_code=404, detail="Business not found")
        return await trust.business_trust(get_db(), p["userId"])

    # --- Saved creators and repeat campaigns -------------------------------
    def business_only(user: dict) -> None:
        if user.get("role") != "business":
            raise HTTPException(status_code=403, detail="Only businesses can do this")

    @r.post("/business/saved/{creator_profile_id}", status_code=201)
    async def save(creator_profile_id: str, user=Depends(get_current_user)):
        business_only(user)
        if not await get_db().creator_profiles.find_one({"id": creator_profile_id}, {"_id": 1}):
            raise HTTPException(status_code=404, detail="Creator not found")
        await get_db().saved_creators.update_one({"brandUserId": user["id"], "creatorProfileId": creator_profile_id},
                                                 {"$setOnInsert": {"id": str(uuid.uuid4()), "createdAt": datetime.now(timezone.utc).isoformat()}}, upsert=True)
        return {"saved": True}

    @r.delete("/business/saved/{creator_profile_id}")
    async def unsave(creator_profile_id: str, user=Depends(get_current_user)):
        business_only(user)
        await get_db().saved_creators.delete_one({"brandUserId": user["id"], "creatorProfileId": creator_profile_id})
        return {"saved": False}

    @r.get("/business/creators")
    async def my_creators(user=Depends(get_current_user)):
        """Saved creators plus everyone this business has worked with, with history for each."""
        business_only(user)
        db = get_db()
        saved = {s["creatorProfileId"] for s in await db.saved_creators.find({"brandUserId": user["id"]}, {"_id": 0}).to_list(500)}
        cs = await db.campaigns.find({"$or": [{"senderUserId": user["id"]}, {"receiverUserId": user["id"]}]}, {"_id": 0}).sort("createdAt", -1).to_list(1000)
        by_creator: dict[str, list] = {}
        for c in cs:
            pid = c["receiverId"] if c.get("receiverType") == "creator" else c["senderId"]
            by_creator.setdefault(pid, []).append(c)
        given = {g["campaignId"]: g["rating"] for g in await db.ratings.find({"raterId": user["id"]}, {"_id": 0}).to_list(1000)}
        out = []
        for pid in saved | set(by_creator):
            p = await db.creator_profiles.find_one({"id": pid}, {"_id": 0})
            if not p:
                continue
            history = by_creator.get(pid, [])
            unlocked = any(c.get("identityUnlocked") for c in history)
            done = [c for c in history if c["status"] == "completed"]
            ratings = [given[c["id"]] for c in done if c["id"] in given]
            redemptions = 0
            for c in history:
                t = await db.tracking_links.find_one({"campaignId": c["id"]}, {"_id": 0, "id": 1})
                if t:
                    redemptions += (await tracking.stats(db, t["id"]))["redemptions"]
            out.append({
                "creatorId": pid, "saved": pid in saved,
                "name": p.get("name") if unlocked else f"{p.get('niche') or 'Local'} creator",
                "instagramUsername": p.get("instagramUsername") if unlocked else None,
                "niche": p.get("niche", ""), "location": p.get("location", ""), "reelPrice": p.get("reelPrice", 0),
                "collaborations": len(history), "completed": len(done), "yourRating": round(sum(ratings) / len(ratings), 1) if ratings else None,
                "redemptions": redemptions, "lastCompletedId": done[0]["id"] if done else None,
                "lastActivity": history[0]["updatedAt"] if history else None,
            })
        out.sort(key=lambda x: (-x["completed"], not x["saved"], x["name"]))
        return out

    @r.post("/campaigns/{campaign_id}/repeat", status_code=201)
    async def repeat(campaign_id: str, user=Depends(get_current_user)):
        c = await campaign_for(campaign_id, user)
        if brand_user_id(c) != user["id"]:
            raise HTTPException(status_code=403, detail="Only the business can repeat a campaign")
        if c["status"] != "completed":
            raise HTTPException(status_code=400, detail="Only completed collaborations can be repeated")
        creator_pid = c["receiverId"] if c.get("receiverType") == "creator" else c["senderId"]
        payload = {"receiverId": creator_pid, "receiverType": "creator", "campaignType": c["campaignType"], "deliverables": c.get("deliverables", ""),
                   "budget": c.get("budget") or 0, "productValue": c.get("productValue") or 0, "timeline": c.get("timeline", ""),
                   "brief": c.get("brief", ""), "barterDetails": c.get("barterDetails", "")}
        created = await create_request(payload, user)
        await get_db().campaigns.update_one({"id": created["id"]}, {"$set": {"repeatOf": campaign_id}})
        return created

    # --- Ledger ------------------------------------------------------------
    @r.get("/payments/ledger")
    async def my_ledger(user=Depends(get_current_user)):
        db = get_db()
        cs = await db.campaigns.find({"$or": [{"senderUserId": user["id"]}, {"receiverUserId": user["id"]}]}, {"_id": 0}).to_list(1000)
        is_brand = {c["id"]: brand_user_id(c) == user["id"] for c in cs}
        label = {}
        for c in cs:
            mine_is_sender = c["senderUserId"] == user["id"]
            other = c["receiverName"] if mine_is_sender else c["senderName"]
            label[c["id"]] = other if c.get("identityUnlocked") else ("Creator" if is_brand[c["id"]] else "Brand")
        entries = await db.ledger_entries.find({"campaignId": {"$in": list(is_brand)}}, {"_id": 0}).sort("createdAt", -1).to_list(2000)
        visible = []
        for e in entries:
            brand_view = is_brand[e["campaignId"]]
            # Businesses see money in and fees; creators see payouts and the commission taken from them.
            if brand_view and e["type"] in ("funded", "barter_fee", "refund"):
                direction = "out" if e["type"] != "refund" else "in"
            elif not brand_view and e["type"] in ("payout_released", "payout_pending", "commission"):
                direction = "out" if e["type"] == "commission" else "in"
            else:
                continue
            visible.append({**e, "direction": direction, "counterpart": label[e["campaignId"]]})
        return visible

    return r
