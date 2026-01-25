# Orange - Creator-Brand Marketplace PRD

## Overview
Orange is a two-sided marketplace connecting creators and brands for paid and barter collaborations, with built-in identity protection, content previews, and trust systems.

## Tech Stack
- **Backend:** FastAPI (Python) + MongoDB
- **Frontend:** React + Tailwind CSS + shadcn/ui
- **Authentication:** JWT-based
- **Payments:** Razorpay (Test Mode - MOCKED)

## Core Principles
1. **Discovery is free, identity is gated** - Brands see creator niches/prices/location but NOT names or Instagram handles
2. **Identity unlocks after commitment** - Paid collabs unlock after payment; Barter collabs unlock after link verification
3. **All communication stays on Orange** - External contact sharing blocked until identity unlock

---

## ✅ Implemented Features (V2)

### Authentication & Onboarding
- [x] User signup/login with JWT
- [x] Role selection (Creator/Brand)
- [x] Multi-step onboarding (5 steps for creators)
- [x] **DUMMY Instagram verification** - Generates simulated followers/engagement
- [x] Creator visibility subscription toggle (MOCKED - ₹50/month)

### Marketplace Discovery
- [x] Anonymous creator listing (no names/handles shown)
- [x] Filter by niche, barter-only
- [x] Partial data shown: niche, location, pricing, engagement rate
- [x] Orange watermark overlay on preview cards

### Collaboration Flow
- [x] **Paid Collaborations**
  - Full budget goes to escrow
  - 10% platform commission
  - Identity unlocks immediately after payment
  
- [x] **Barter Collaborations** (Product & Service)
  - 10% fee on declared product/service value
  - Identity unlocks AFTER link verification (not payment)
  - Shipping details tracking
  - Product received confirmation

### Campaign States
- `requested` → `accepted` → `paid` → `in_progress` → `link_submitted` → `link_verified` → `completed`
- Also: `disputed`, `cancelled`

### Messaging
- [x] In-app chat (only available after payment)
- [x] External contact blocking (Instagram handles, phone numbers, links blocked until identity unlock)

### Ratings & Feedback
- [x] 1-5 star ratings after completion
- [x] Mandatory feedback comments
- [x] Average rating calculation and display

### Security Features
- [x] Identity masking until unlock conditions met
- [x] Message filtering for external contacts
- [x] Blacklist system for violations
- [x] Report/dispute mechanism

---

## MOCKED Components (MVP)
- **Instagram OAuth:** Using dummy verification with simulated metrics
- **Payments:** Test mode only, no real money processing
- **Creator Subscription:** Toggle-based visibility, no actual payment required
- **Content Watermarking:** CSS overlay only, no server-side processing

---

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Create account
- `POST /api/auth/login` - Login and get JWT
- `POST /api/auth/instagram/verify` - **DUMMY** Instagram verification
- `GET /api/auth/me` - Get current user

### Profiles
- `POST /api/creator/profile` - Create/update creator profile
- `GET /api/creator/profile` - Get own creator profile
- `POST /api/creator/subscription/toggle` - Toggle marketplace visibility
- `POST /api/business/profile` - Create/update brand profile
- `GET /api/business/profile` - Get own brand profile

### Marketplace
- `GET /api/marketplace/creators` - Browse creators (anonymous)
- `GET /api/marketplace/brands` - Browse brands (anonymous)

### Campaigns
- `POST /api/campaigns/` - Create campaign request
- `GET /api/campaigns/incoming` - Get received requests
- `GET /api/campaigns/outgoing` - Get sent requests
- `GET /api/campaigns/{id}` - Get campaign details
- `PATCH /api/campaigns/{id}/respond?action=accept|reject` - Respond to request
- `POST /api/campaigns/{id}/pay` - Pay escrow/fee
- `POST /api/campaigns/{id}/submit-link` - Submit reel/story link
- `POST /api/campaigns/{id}/verify-link` - Verify submitted link
- `POST /api/campaigns/{id}/complete` - Mark as complete
- `POST /api/campaigns/{id}/rate` - Submit rating
- `POST /api/campaigns/{id}/report` - Report issue

### Messages
- `GET /api/messages/{campaignId}` - Get messages
- `POST /api/messages/{campaignId}` - Send message

---

## Test Credentials
- **Creator:** creator1@orange.com / password123
- **Brand:** brand1@orange.com / password123
- **Admin:** admin@orange.com / admin123

---

## Future Tasks (Backlog)

### P1 - Post-MVP
- [ ] Real Instagram OAuth integration
- [ ] Razorpay production mode
- [ ] Server-side content watermarking/blurring
- [ ] Advanced content previews (video trimming, muting)

### P2 - Enhancements
- [ ] Admin panel for disputes/blacklisting
- [ ] Brand-side creator rejection (hide from view)
- [ ] Auto-flag for deleted content
- [ ] Push notifications
- [ ] Analytics dashboard

---

## Last Updated
January 25, 2025

## Version
V2.0 - MVP Complete
