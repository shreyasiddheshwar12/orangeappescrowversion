# Orange - Creator Marketplace

## Original Problem Statement
Build a Gen-Z friendly two-sided marketplace where:
- **Creators** build profiles, upload photos/videos, set rates, and receive collaboration requests
- **Brands** browse creators, filter them, view profiles, see media, click "Go to Instagram", and send requests
- Both sides can chat

## Architecture & Tech Stack
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React with Tailwind CSS, shadcn/ui components
- **Database**: MongoDB
- **Media Storage**: Cloudinary (credentials pending from user)
- **Authentication**: JWT-based with email/password

## Completed Features

### Authentication
- ✅ Signup with role selection (Creator/Business)
- ✅ Login with JWT tokens
- ✅ Protected routes based on role
- ✅ Session persistence

### Creator Features
- ✅ 5-step onboarding flow (Basic Info, Social Stats, Rates, Profile Photo, Media Gallery)
- ✅ Dashboard with profile card
- ✅ Collaboration requests management (Accept/Decline)
- ✅ Edit profile functionality
- ✅ Public profile page
- ✅ Go to Instagram button

### Business Features
- ✅ 3-step onboarding flow (Brand Info, Social/Website, Media Upload)
- ✅ Dashboard with brand profile
- ✅ Creator Marketplace with grid view
- ✅ Fully working filters (niche, followers range, location, barter toggle)
- ✅ View creator profiles
- ✅ Send collaboration requests
- ✅ Track sent requests

### Collaboration System
- ✅ Create requests with title, brief, offer amount, deliverables, timeline
- ✅ Request status management (pending/accepted/declined)
- ✅ Chat functionality per request
- ✅ Real-time message updates

### UI/UX
- ✅ Gen-Z orange theme (bright orange, peach accents)
- ✅ Catchy microcopy throughout the app
- ✅ Syne + Plus Jakarta Sans fonts
- ✅ Pill buttons, rounded cards
- ✅ Responsive design
- ✅ Smooth animations with framer-motion

## Database Collections
- `users` - User accounts with role and onboarding status
- `creator_profiles` - Creator profiles with rates, niches, media
- `business_profiles` - Brand profiles with category, media
- `collaboration_requests` - Collab requests between brands and creators
- `messages` - Chat messages per request

## API Endpoints
- `/api/auth/*` - Authentication (signup, login, me, logout)
- `/api/upload` - Cloudinary file upload
- `/api/creator/*` - Creator profile and requests
- `/api/business/*` - Business profile
- `/api/creators` - Marketplace with filters
- `/api/requests/*` - Collaboration request CRUD
- `/api/messages/*` - Chat messages

## Environment Variables Required

### Backend (.env)
- `MONGO_URL` - MongoDB connection string
- `DB_NAME` - Database name
- `JWT_SECRET` - JWT signing secret
- `CLOUDINARY_CLOUD_NAME` - Cloudinary cloud name
- `CLOUDINARY_API_KEY` - Cloudinary API key
- `CLOUDINARY_API_SECRET` - Cloudinary API secret

### Frontend (.env)
- `REACT_APP_BACKEND_URL` - Backend API URL

## Demo Accounts
- Creator: creator1@orange.com / password123
- Business: business1@orange.com / password123

## Next Steps / Enhancements
1. Add Cloudinary credentials for media uploads to work
2. Email notifications for new requests
3. Creator analytics dashboard
4. Payment integration (Razorpay/Stripe)
5. Advanced search with creator categories
6. Portfolio showcase with Instagram integration
7. Contract/Agreement generation for collabs
