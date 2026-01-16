# Orange - Two-Way Creator Marketplace PRD

## Overview
Orange is a two-sided creator marketplace connecting brands with content creators for paid and barter collaborations. The platform features a gated access system where profiles are progressively unlocked through credits and payments.

## Tech Stack
- **Backend:** FastAPI (Python) with MongoDB
- **Frontend:** React with Tailwind CSS, shadcn/ui
- **Auth:** JWT-based authentication
- **Payments:** Razorpay (TEST MODE with demo credits)
- **Media:** Cloudinary (optional, for uploads)

## Core Features (Implemented)

### 1. Authentication System ✅
- Email/password signup and login
- Role-based access (creator, business, admin)
- JWT token-based authentication
- Onboarding flow for profile completion

### 2. Instagram Verification (MOCKED) ✅
- Simulated Instagram OAuth for demo purposes
- Auto-generates follower counts (5K-500K) and engagement rates
- System-calculated engagement rate (not user-editable)
- Note: In production, this would use real Instagram Graph API OAuth

### 3. Two-Way Marketplace Discovery ✅
- **Layer 1 (Free):** Brands discover creators, creators discover brands
- Anonymized display (rounded followers "50K+", approximate engagement "~5.8%")
- Filter by niche, location, barter availability, follower range
- Lock icons indicate unlockable profiles

### 4. Credit-Based Unlock System ✅
- **Pricing:** ₹200 = 5 credits (7-day expiry)
- **Context Unlock:** 1 credit unlocks full profile (bio, exact metrics, rates)
- Instagram handle remains hidden until campaign payment
- Demo credits available for testing

### 5. Payment Integration ✅
- Razorpay TEST MODE integration
- Demo credits fallback when no valid keys configured
- Unlock Pack purchase flow
- Escrow payment preparation (pending full implementation)

### 6. Creator Dashboard ✅
- Profile display with rates and niches
- Incoming campaign requests view
- Edit profile functionality

### 7. Brand Dashboard ✅
- Creator marketplace browsing
- Credit balance display
- Unlock modal for gated access
- Campaigns tab (pending campaigns implementation)

## Database Schema

### Collections:
- `users` - Authentication and role data
- `creator_profiles` - Creator details, Instagram, rates
- `brand_profiles` - Brand details, industry, budget
- `credits` - User credit balances and expiry
- `profile_unlocks` - Track which profiles are unlocked
- `collab_requests` - Two-way request system
- `campaigns` - Campaign details after acceptance
- `messages` - Chat messages with anti-bypass
- `payments` - Payment records
- `bypass_attempts` - Logged anti-bypass violations

## API Endpoints

### Auth
- POST `/api/auth/signup` - Create account
- POST `/api/auth/login` - Login
- GET `/api/auth/me` - Get current user

### Marketplace
- GET `/api/marketplace/creators` - Discover creators (Layer 1)
- GET `/api/marketplace/brands` - Discover brands (Layer 1)
- GET `/api/marketplace/creators/{id}/unlocked` - View unlocked profile
- POST `/api/marketplace/creator/{id}/unlock` - Unlock a profile

### Payments
- GET `/api/payments/credits` - Get credit balance
- POST `/api/payments/unlock-pack/order` - Create unlock pack order
- POST `/api/payments/unlock-pack/demo` - Add demo credits (testing)
- POST `/api/payments/escrow/{campaign_id}/order` - Create escrow order

### Instagram
- POST `/api/instagram/verify` - Verify Instagram (MOCKED)

### Admin
- GET `/api/admin/stats` - Platform statistics
- GET `/api/admin/bypass-attempts` - View flagged messages

## Test Accounts (Seeded)
```
Admin: admin@orange.com / admin123
Creator: creator1@orange.com / password123
Brand: brand1@orange.com / password123 (starts with 5 credits)
```

## What's Working (Jan 2026)
1. ✅ Full authentication flow
2. ✅ Creator and brand dashboards
3. ✅ Marketplace discovery with filters
4. ✅ Credit-based unlock system
5. ✅ Demo credits for testing
6. ✅ Instagram verification (simulated)
7. ✅ Admin statistics endpoint
8. ✅ Responsive UI with Orange theme

## Pending Features (P1)
1. ⏳ Two-way request flow (backend ready, frontend pending)
2. ⏳ Campaign creation after request acceptance
3. ⏳ Chat with anti-bypass filtering
4. ⏳ Escrow payment flow for identity unlock
5. ⏳ Campaign status tracking

## Future Features (P2)
1. Admin dashboard UI
2. Barter collaboration tracking
3. Analytics and insights
4. Email notifications
5. Real Instagram OAuth integration
6. Production Razorpay keys

## Known Limitations
- Instagram OAuth is **MOCKED** for demo - generates random data
- Razorpay uses **TEST MODE** with demo credits fallback
- Chat anti-bypass system backend-ready but UI not connected
- No email notifications implemented
