"""Run the Orange API against an in-memory MongoDB with demo seed data.

For local UI work and demos only. Nothing persists after the process exits.

    python dev_inmemory.py            # http://localhost:8000
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://in-memory")
os.environ.setdefault("DB_NAME", "orange_dev")
os.environ.setdefault("JWT_SECRET", "dev-only-secret")
os.environ.setdefault("PAYMENT_PROVIDER", "simulated")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import server  # noqa: E402
import e2e_patch  # noqa: E402
from seed import build_seed_documents  # noqa: E402

server.db = AsyncMongoMockClient()[os.environ["DB_NAME"]]
if not getattr(server.app.state, "e2e_hardened", False):
    e2e_patch._patch_server(server)
app = server.app


async def _seed():
    users, creators, brands = build_seed_documents()
    await server.db.users.insert_many(users)
    await server.db.creator_profiles.insert_many(creators)
    await server.db.brand_profiles.insert_many(brands)


asyncio.new_event_loop().run_until_complete(_seed())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
