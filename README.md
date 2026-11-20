# Orange 🍊

Creator–brand marketplace with protected collaboration payments and an escrow-style workflow.

## What is functional

- Creator and brand signup/login with JWT authentication.
- Creator and brand profiles.
- Anonymous marketplace discovery before collaboration unlock.
- Two-way collaboration requests: brand → creator and creator → brand.
- Paid campaigns and barter campaigns.
- Razorpay Standard Checkout for live/test payments.
- Server-side Razorpay signature verification and payment-status verification.
- Payment webhooks with duplicate-event protection.
- Escrow ledger on campaigns: funded → work → link submitted → verified → completion.
- Creator payout plumbing through Razorpay Route when a creator has an onboarded Linked Account.
- In-app collaboration chat with external-contact filtering.
- Content-link submission, brand verification, ratings and dispute reporting.
- Admin reporting and platform statistics.
- Seed data for local/demo testing.

## Payment flow

1. A collaboration is requested.
2. The receiver accepts.
3. The **brand is the payer** for paid and barter collaborations.
4. The brand clicks **Pay**; Orange creates a Razorpay Order server-side and opens Razorpay Checkout.
5. Razorpay returns `razorpay_order_id`, `razorpay_payment_id` and `razorpay_signature`.
6. Orange verifies the signature and confirms the payment is captured before unlocking the paid workflow.
7. Chat is enabled. For paid campaigns, identity is unlocked after payment. For barter, identity remains locked until content verification.
8. Creator submits the content link.
9. Brand verifies the link.
10. Brand completes the campaign.
11. For paid campaigns, Orange attempts a Razorpay Route transfer to the creator's Linked Account. If Route onboarding is not configured, the campaign completes but the payout remains marked pending rather than pretending funds were released.

This is an **escrow-style application workflow and ledger**. Standard Razorpay Checkout does not by itself create a legally regulated escrow account. Production fund disbursement to creators requires an approved Razorpay Route setup and properly onboarded Linked Accounts.

## Growth Assistant

`backend/orange/growth/` runs a business's goal through five capabilities and stores every step so the dashboard can show a timeline:

1. **Business Intelligence** reads the brand profile.
2. **Performance Analyst** summarises past collaborations from campaigns, ratings and the ledger.
3. **Marketing Planner** turns the goal and budget into a plan. The budget is capped in code (at least 10% kept in reserve).
4. **Creator Matching** ranks creators with a deterministic score: niche 25, location 20, price fit 20, TrustScore 15, measured engagement 10, language 5, availability 5. A factor without data is left out rather than guessed, and each creator shows why they scored as they did.
5. **Campaign Assistant** writes briefs and sends real collaboration requests, but only after the business approves the shortlist.

With `ANTHROPIC_API_KEY` set, steps 1, 3 and 5 (and 2 once there is history) use the Claude API with structured outputs. The key never leaves the server. Without it, each step falls back to rules that only restate the business's own data, and the timeline labels which engine ran.

Routes live under `/api/growth`: `GET /status`, `POST /runs`, `GET /runs`, `GET /runs/{id}`, `POST /runs/{id}/approve`, `POST /runs/{id}/cancel`.

**Data changes (additive):** new collections `agent_runs`, `agent_steps` and `growth_campaigns`, and an optional `growthCampaignId` on `campaigns`. Existing documents need no migration.

**Chat:** messages that contain contact details are no longer replaced. They are delivered with `flagged: true`, and the app reminds both sides that payments outside Orange aren't protected. Attempts are still logged in `bypass_attempts`.

## Payment providers

Payment execution sits behind `backend/orange/payments/` (`PaymentProvider`). Two providers exist:

- `razorpay`: Razorpay Standard Checkout plus Route transfers (the flow described above).
- `simulated`: for local development and demos. Orders are settled by the backend, no money moves, and every payment, payout and ledger entry is marked `simulated`. It is refused when `APP_ENV=production`.

Set `PAYMENT_PROVIDER` to choose. When unset, Orange uses Razorpay if keys are present and the simulated provider otherwise. Every money movement is written to the `ledger_entries` collection.

## Local setup

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn server:app --reload --port 8000
```

Required values:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=orange
JWT_SECRET=replace-me
FRONTEND_URL=http://localhost:3000
RAZORPAY_KEY_ID=rzp_test_xxx
RAZORPAY_KEY_SECRET=xxx
RAZORPAY_WEBHOOK_SECRET=xxx
```

### Frontend

```bash
cd frontend
yarn install
yarn start
```

Set:

```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

## Razorpay dashboard setup

For development, use **Test Mode** keys. For actual customer transactions, Razorpay requires Live Mode keys and an activated account. Configure payment capture appropriately and add a webhook pointing to:

```text
POST https://<your-backend-domain>/api/payments/razorpay/webhook
```

Recommended webhook events:

- `payment.captured`
- `payment.failed`
- `order.paid`

Keep `RAZORPAY_KEY_SECRET` and `RAZORPAY_WEBHOOK_SECRET` only on the backend. Never commit them to GitHub.

For automatic creator payouts, enable Razorpay Route for the platform account and complete Linked Account onboarding. Store the resulting creator `account_id` as `razorpayLinkedAccountId` on that creator's user record.

## Demo seed

The existing demo seed endpoint is preserved:

```text
POST /api/seed
```

Demo accounts created by the seed fixture:

- Brand: `brand1@orange.com` / `password123`
- Creator: `creator1@orange.com` / `password123`
- Admin: `admin@orange.com` / `admin123`

Do not use seeded credentials in production.

## Branch

The live-payment implementation is developed on:

`feat/live-razorpay-escrow`
