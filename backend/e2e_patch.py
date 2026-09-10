"""Runtime hardening layer for the legacy Orange FastAPI server.

Loaded by sitecustomize before uvicorn serves the app. This deliberately keeps
existing UI/routes intact while replacing the few broken integration points.
"""
from __future__ import annotations

import asyncio
import os
import re
import secrets
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_UPLOADS = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "video/mp4", "video/quicktime", "video/webm",
}


def _now():
    return datetime.now(timezone.utc)


def _remove_routes(app, path: str, methods: set[str]):
    app.router.routes[:] = [
        route for route in app.router.routes
        if not (getattr(route, "path", None) == path and
                set(getattr(route, "methods", set())) & methods)
    ]


def _patch_server(server):
    app = server.app
    db = server.db

    # ---------- Instagram OAuth ----------
    async def instagram_connect(current_user=server.Depends(server.get_current_user)):
        if not server.INSTAGRAM_APP_ID or not server.INSTAGRAM_APP_SECRET:
            raise HTTPException(
                status_code=503,
                detail="Instagram OAuth is not configured. Add INSTAGRAM_APP_ID and INSTAGRAM_APP_SECRET to backend/.env.",
            )
        state = secrets.token_urlsafe(32)
        await db.instagram_oauth_states.update_one(
            {"userId": current_user["id"]},
            {"$set": {"userId": current_user["id"], "state": state,
                      "expiresAt": _now().timestamp() + 600}},
            upsert=True,
        )
        params = {
            "client_id": server.INSTAGRAM_APP_ID,
            "redirect_uri": server.INSTAGRAM_REDIRECT_URI,
            "response_type": "code",
            "scope": server.INSTAGRAM_SCOPES,
            "state": state,
        }
        return {"authorizationUrl": "https://www.instagram.com/oauth/authorize?" + urlencode(params)}

    async def instagram_callback(code: Optional[str] = None, state: Optional[str] = None,
                                 error: Optional[str] = None, error_reason: Optional[str] = None):
        if error:
            return RedirectResponse(f"{server.FRONTEND_URL}/instagram/callback?instagram=error&reason={error_reason or error}")
        if not code or not state:
            return RedirectResponse(f"{server.FRONTEND_URL}/instagram/callback?instagram=error&reason=missing_oauth_parameters")
        state_doc = await db.instagram_oauth_states.find_one({"state": state}, {"_id": 0})
        if not state_doc:
            return RedirectResponse(f"{server.FRONTEND_URL}/instagram/callback?instagram=error&reason=invalid_or_expired_state")
        expires = state_doc.get("expiresAt")
        if isinstance(expires, (int, float)) and expires < _now().timestamp():
            await db.instagram_oauth_states.delete_one({"_id": state_doc.get("_id")})
            return RedirectResponse(f"{server.FRONTEND_URL}/instagram/callback?instagram=error&reason=expired_state")
        await db.instagram_oauth_states.delete_one({"state": state})
        try:
            instagram = await asyncio.to_thread(server.exchange_instagram_code, code)
        except Exception as exc:
            server.logger.exception("Instagram OAuth exchange failed")
            reason = re.sub(r"[^a-zA-Z0-9_-]", "_", str(exc))[:180]
            return RedirectResponse(f"{server.FRONTEND_URL}/instagram/callback?instagram=error&reason={reason}")

        now = _now()
        expires_at = None
        if instagram.get("expiresIn"):
            try:
                from datetime import timedelta
                expires_at = now + timedelta(seconds=int(instagram["expiresIn"]))
            except (TypeError, ValueError):
                expires_at = None

        # Instagram Login's basic profile response does not guarantee follower
        # metrics. Persist a real metric when supplied; otherwise use 0 rather
        # than inventing a number. Engagement is likewise 0 until measured.
        followers = int(instagram.get("followersCount") or 0)
        fields = {
            "instagramVerified": True,
            "instagramUserId": instagram.get("instagramUserId"),
            "instagramUsername": instagram.get("instagramUsername"),
            "instagramAccessToken": instagram.get("accessToken"),
            "instagramTokenExpiresAt": expires_at,
            "instagramConnectedAt": now,
            "instagramAccountType": instagram.get("accountType"),
            "instagramMediaCount": instagram.get("mediaCount"),
            "followersCount": followers,
            "engagementRate": 0,
        }
        await db.users.update_one({"id": state_doc["userId"]}, {"$set": fields})
        user = await db.users.find_one({"id": state_doc["userId"]}, {"_id": 0})
        if user:
            collection = "creator_profiles" if user.get("role") == "creator" else "brand_profiles"
            await db[collection].update_one(
                {"userId": state_doc["userId"]},
                {"$set": fields},
                upsert=False,
            )
        return RedirectResponse(f"{server.FRONTEND_URL}/instagram/callback?instagram=connected")

    async def instagram_status(current_user=server.Depends(server.get_current_user)):
        return {
            "connected": bool(current_user.get("instagramVerified") and current_user.get("instagramUserId")),
            "instagramUserId": current_user.get("instagramUserId"),
            "instagramUsername": current_user.get("instagramUsername"),
            "followersCount": current_user.get("followersCount", 0),
            "engagementRate": current_user.get("engagementRate", 0),
        }

    async def instagram_disconnect(current_user=server.Depends(server.get_current_user)):
        fields = {
            "instagramVerified": False, "instagramUserId": None,
            "instagramUsername": None, "instagramAccessToken": None,
            "instagramTokenExpiresAt": None, "instagramConnectedAt": None,
            "instagramAccountType": None, "instagramMediaCount": None,
            "followersCount": 0, "engagementRate": 0,
        }
        await db.users.update_one({"id": current_user["id"]}, {"$set": fields})
        collection = "creator_profiles" if current_user["role"] == "creator" else "brand_profiles"
        await db[collection].update_one({"userId": current_user["id"]}, {"$set": fields})
        return {"success": True, "message": "Instagram disconnected successfully"}

    _remove_routes(app, "/api/auth/instagram/connect", {"GET"})
    _remove_routes(app, "/api/auth/instagram/callback", {"GET"})
    _remove_routes(app, "/api/auth/instagram/status", {"GET"})
    _remove_routes(app, "/api/auth/instagram/disconnect", {"POST"})
    app.add_api_route("/api/auth/instagram/connect", instagram_connect, methods=["GET"])
    app.add_api_route("/api/auth/instagram/callback", instagram_callback, methods=["GET"])
    app.add_api_route("/api/auth/instagram/status", instagram_status, methods=["GET"])
    app.add_api_route("/api/auth/instagram/disconnect", instagram_disconnect, methods=["POST"])

    # ---------- Real local uploads ----------
    upload_dir = Path(server.ROOT_DIR) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    if not any(getattr(r, "path", None) == "/uploads" for r in app.routes):
        app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

    async def upload_file(file: UploadFile = File(...), current_user=server.Depends(server.get_current_user)):
        if file.content_type not in ALLOWED_UPLOADS:
            raise HTTPException(status_code=415, detail="Unsupported file type")
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File is larger than 25 MB")
        suffix = Path(file.filename or "upload").suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".webm"}:
            suffix = ".bin"
        name = f"{uuid.uuid4().hex}{suffix}"
        target = upload_dir / name
        target.write_bytes(data)
        base = server.FRONTEND_URL
        # BACKEND_PUBLIC_URL is optional; localhost fallback is correct for local dev.
        public_base = os.environ.get("BACKEND_PUBLIC_URL", "http://localhost:8000")
        kind = "video" if file.content_type.startswith("video/") else "image"
        url = f"{public_base.rstrip('/')}/uploads/{name}"
        return {"url": url, "type": kind, "thumbnailUrl": url, "filename": file.filename, "size": len(data)}

    _remove_routes(app, "/api/uploads", {"POST"})
    app.add_api_route("/api/uploads", upload_file, methods=["POST"])

    # ---------- Backward-compatible paid campaign endpoint ----------
    async def pay_campaign(campaign_id: str, current_user=server.Depends(server.get_current_user)):
        c = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
        if not c:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if server.brand_user_id(c) != current_user["id"]:
            raise HTTPException(status_code=403, detail="Only the brand can fund this collaboration")
        if c.get("status") not in {"accepted", "payment_pending"}:
            raise HTTPException(status_code=400, detail="Campaign must be accepted before payment")
        if not server.razorpay_configured():
            raise HTTPException(status_code=503, detail="Razorpay is not configured")
        order = server.razorpay_request("POST", "/orders", json={
            "amount": int(round(c.get("escrowAmount", 0) * 100)),
            "currency": "INR", "receipt": f"campaign_{campaign_id}",
            "notes": {"campaign_id": campaign_id},
        })
        await db.campaigns.update_one({"id": campaign_id}, {"$set": {"status": "payment_pending", "updatedAt": _now().isoformat()}})
        return {"success": True, "status": "payment_pending", "orderId": order["id"], "amount": order["amount"], "currency": order["currency"], "keyId": server.RAZORPAY_KEY_ID}

    _remove_routes(app, "/api/campaigns/{campaign_id}/pay", {"POST"})
    app.add_api_route("/api/campaigns/{campaign_id}/pay", pay_campaign, methods=["POST"])

    # ---------- Admin-safe seed behaviour ----------
    async def safe_seed(current_user=server.Depends(server.get_current_user)):
        if os.environ.get("SEED_ENABLED", "false").lower() != "true":
            raise HTTPException(status_code=403, detail="Seed endpoint disabled. Set SEED_ENABLED=true for local development only.")
        if not current_user.get("isAdmin"):
            raise HTTPException(status_code=403, detail="Admin access required")
        from seed import build_seed_documents
        users, creators, brands = build_seed_documents()
        for col in ["users", "creator_profiles", "brand_profiles", "campaigns", "messages", "payments", "reports", "ratings", "payouts", "razorpay_events", "bypass_attempts"]:
            await db[col].delete_many({})
        if users: await db.users.insert_many(users)
        if creators: await db.creator_profiles.insert_many(creators)
        if brands: await db.brand_profiles.insert_many(brands)
        return {"message": "Seed data created!", "creators": len(creators), "brands": len(brands)}

    _remove_routes(app, "/api/seed", {"POST"})
    app.add_api_route("/api/seed", safe_seed, methods=["POST"])

    app.state.e2e_hardened = True


def install_when_server_imports():
    """Install a tiny import hook so the existing `uvicorn server:app` command
    remains unchanged while this compatibility layer runs after server.py has
    finished defining all routes.
    """
    import importlib.abc
    import importlib.machinery

    if getattr(install_when_server_imports, "installed", False):
        return
    install_when_server_imports.installed = True

    class Loader(importlib.abc.Loader):
        def __init__(self, wrapped):
            self.wrapped = wrapped
        def create_module(self, spec):
            if hasattr(self.wrapped, "create_module"):
                return self.wrapped.create_module(spec)
            return None
        def exec_module(self, module):
            self.wrapped.exec_module(module)
            _patch_server(module)

    class Finder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname != "server":
                return None
            spec = importlib.machinery.PathFinder.find_spec(fullname, path)
            if spec and spec.loader:
                spec.loader = Loader(spec.loader)
            return spec

    sys.meta_path.insert(0, Finder())


install_when_server_imports()
