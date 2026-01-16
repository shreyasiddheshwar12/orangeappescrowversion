from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Query, status, Request, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import random
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import cloudinary
import cloudinary.uploader
import razorpay
import hmac
import hashlib

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'orange-marketplace-secret-key-2024')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Cloudinary Configuration
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    api_key=os.environ.get('CLOUDINARY_API_KEY', ''),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET', ''),
    secure=True
)

# Razorpay Configuration (TEST MODE)
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_demo')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'demo_secret')
RAZORPAY_TEST_MODE = True  # Always use test mode for demo

razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET and not RAZORPAY_KEY_ID.startswith('rzp_test_demo'):
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Pricing Configuration
UNLOCK_PACK_PRICE = 20000  # ₹200 in paise
UNLOCK_PACK_CREDITS = 5
UNLOCK_CREDIT_VALIDITY_DAYS = 7
REQUEST_EXPIRY_HOURS = 72

# Create the main app
app = FastAPI(title="Orange - Two-Way Creator Marketplace API")

# Create routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
creator_router = APIRouter(prefix="/creator", tags=["Creator"])
business_router = APIRouter(prefix="/business", tags=["Business"])
marketplace_router = APIRouter(prefix="/marketplace", tags=["Marketplace"])
request_router = APIRouter(prefix="/requests", tags=["Requests"])
message_router = APIRouter(prefix="/messages", tags=["Messages"])
payment_router = APIRouter(prefix="/payments", tags=["Payments"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])

security = HTTPBearer()

# ============== BLOCKED KEYWORDS FOR CHAT ==============
BLOCKED_PATTERNS = [
    r'\b(instagram|insta|ig)\b',
    r'\b(whatsapp|whats\s*app|wa)\b',
    r'\b(telegram|signal|snapchat|snap)\b',
    r'\b(twitter|x\.com|facebook|fb|linkedin)\b',
    r'@\w+',  # @usernames
    r'\b(gmail|yahoo|hotmail|outlook)\b',
    r'\b\d{10}\b',  # 10 digit phone numbers
    r'\b\d{5}[\s-]?\d{5}\b',  # Phone with space/dash
    r'[\w\.-]+@[\w\.-]+\.\w+',  # Email pattern
]

def check_message_for_bypass(text: str) -> tuple:
    """Check if message contains blocked keywords. Returns (is_blocked, reason)"""
    text_lower = text.lower()
    
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True, "External contact sharing is not allowed before payment"
    
    return False, ""

def calculate_engagement_rate(followers: int, avg_likes: int, avg_comments: int) -> float:
    """Calculate engagement rate: (avg_likes + avg_comments) / followers * 100"""
    if followers <= 0:
        return 0.0
    return round(((avg_likes + avg_comments) / followers) * 100, 2)

# ============== MODELS ==============

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Literal["creator", "business"]

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    hasCompletedOnboarding: bool = False
    isAdmin: bool = False
    instagramVerified: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Instagram Verification (Simulated for Demo)
class InstagramVerifyRequest(BaseModel):
    instagramUsername: str

class InstagramVerifyResponse(BaseModel):
    success: bool
    instagramUserId: str
    instagramUsername: str
    followersCount: int
    engagementRate: float
    message: str

# Creator Profile
class RateInfo(BaseModel):
    reelPrice: float = 0
    storyPrice: float = 0
    carouselPrice: float = 0
    postPrice: float = 0
    bundlePrice: float = 0

class CreatorProfileCreate(BaseModel):
    name: str
    bio: Optional[str] = ""
    location: Optional[str] = ""
    niches: Optional[List[str]] = []
    isOpenToBarter: Optional[bool] = False
    rates: Optional[RateInfo] = None
    profilePhotoUrl: Optional[str] = ""
    sampleContent: Optional[List[str]] = []  # URLs to sample content

class CreatorProfileFull(BaseModel):
    id: str
    userId: str
    name: str
    bio: str
    location: str
    instagramUserId: Optional[str] = None
    instagramUsername: Optional[str] = None
    instagramVerified: bool = False
    followersCount: int
    engagementRate: float
    niches: List[str]
    isOpenToBarter: bool
    rates: RateInfo
    profilePhotoUrl: str
    sampleContent: List[str]
    createdAt: str
    updatedAt: str

# Discovery Mode (Free) - No identity
class CreatorDiscovery(BaseModel):
    id: str
    niches: List[str]
    location: str
    followersDisplay: str  # "40K+"
    engagementRateDisplay: str  # "~5.8%"
    rateRange: str  # "₹5k-₹15k"
    isOpenToBarter: bool
    previewContent: List[str]  # Watermarked previews
    isUnlocked: bool = False

# Unlocked Mode (After Credit) - Context, no identity
class CreatorUnlocked(BaseModel):
    id: str
    niches: List[str]
    location: str
    followersCount: int
    engagementRate: float
    rates: RateInfo
    isOpenToBarter: bool
    sampleContent: List[str]
    bio: str
    profilePhotoUrl: str
    # Hidden: instagramUsername, instagramUserId

# Full Access (After Payment) - Everything
class CreatorFullAccess(CreatorProfileFull):
    pass

# Brand Profile
class BrandProfileCreate(BaseModel):
    brandName: str
    industry: Optional[str] = ""
    bio: Optional[str] = ""
    location: Optional[str] = ""
    budgetRange: Optional[str] = ""  # "₹10k-₹50k"
    preferredNiches: Optional[List[str]] = []
    isOpenToBarter: Optional[bool] = False
    profilePhotoUrl: Optional[str] = ""
    pastCampaigns: Optional[List[str]] = []  # URLs to past campaign content

class BrandProfileFull(BaseModel):
    id: str
    userId: str
    brandName: str
    industry: str
    bio: str
    location: str
    instagramUserId: Optional[str] = None
    instagramUsername: Optional[str] = None
    instagramVerified: bool = False
    budgetRange: str
    preferredNiches: List[str]
    isOpenToBarter: bool
    profilePhotoUrl: str
    pastCampaigns: List[str]
    pastCollabCount: int = 0
    createdAt: str
    updatedAt: str

# Brand Discovery (For Creators to see)
class BrandDiscovery(BaseModel):
    id: str
    brandName: str
    industry: str
    location: str
    budgetRange: str
    preferredNiches: List[str]
    isOpenToBarter: bool
    pastCollabCount: int
    isUnlocked: bool = False

# Brand Unlocked (After Credit)
class BrandUnlocked(BaseModel):
    id: str
    brandName: str
    industry: str
    bio: str
    location: str
    budgetRange: str
    preferredNiches: List[str]
    isOpenToBarter: bool
    pastCampaigns: List[str]
    pastCollabCount: int
    profilePhotoUrl: str
    # Hidden: instagramUsername

# Credits
class UnlockCreditsResponse(BaseModel):
    totalCredits: int
    lockedCredits: int
    usedCredits: int
    availableCredits: int
    expiryDate: Optional[str]

# Two-Way Request
class CollabRequestCreate(BaseModel):
    receiverId: str  # Creator ID or Brand ID
    receiverType: Literal["creator", "business"]
    message: str
    proposedBudget: Optional[float] = 0
    deliverables: Optional[str] = ""

class CollabRequestResponse(BaseModel):
    id: str
    senderId: str
    senderType: str
    senderName: str
    receiverId: str
    receiverType: str
    receiverName: str
    message: str
    proposedBudget: float
    deliverables: str
    status: str  # pending, accepted, rejected, expired
    creditState: str  # locked, consumed, refunded
    identityUnlocked: bool
    expiresAt: str
    createdAt: str
    updatedAt: str

# Campaign (After acceptance)
class CampaignCreate(BaseModel):
    requestId: str
    title: str
    brief: str
    price: float
    deliverables: str
    timeline: str
    isBarter: bool = False
    barterDetails: Optional[str] = ""

class CampaignResponse(BaseModel):
    id: str
    requestId: str
    brandId: str
    creatorId: str
    title: str
    brief: str
    price: float
    deliverables: str
    timeline: str
    isBarter: bool
    barterDetails: str
    escrowStatus: str  # pending, paid_test, released
    campaignStatus: str  # negotiating, confirmed, in_progress, delivered, completed
    identityUnlocked: bool
    creatorInstagram: Optional[str] = None
    brandInstagram: Optional[str] = None
    createdAt: str
    updatedAt: str

# Messages
class MessageCreate(BaseModel):
    text: str

class MessageResponse(BaseModel):
    id: str
    campaignId: str
    senderUserId: str
    senderName: str
    text: str
    isBlocked: bool = False
    blockReason: Optional[str] = None
    createdAt: str

# Payments
class PaymentOrderResponse(BaseModel):
    orderId: str
    amount: int
    currency: str
    keyId: str
    testMode: bool = True

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

# ============== AUTH UTILITIES ==============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        if user.get("isBanned"):
            raise HTTPException(status_code=403, detail="Account banned")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    if not current_user.get("isAdmin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# ============== HELPER FUNCTIONS ==============

def format_followers(count: int) -> str:
    if count >= 1000000:
        return f"{count // 1000000}M+"
    elif count >= 1000:
        return f"{count // 1000}K+"
    return f"{count}+"

def format_engagement_rate(rate: float) -> str:
    return f"~{round(rate, 1)}%"

def format_rate_range(rates: dict) -> str:
    prices = [v for v in [rates.get('reelPrice', 0), rates.get('storyPrice', 0), 
                          rates.get('carouselPrice', 0)] if v > 0]
    if not prices:
        return "Ask for rates"
    min_price = min(prices) // 1000
    max_price = max(prices) // 1000
    if min_price == max_price:
        return f"₹{min_price}k"
    return f"₹{min_price}k-₹{max_price}k"

async def get_user_credits(user_id: str) -> dict:
    """Get user's unlock credits"""
    credits = await db.credits.find_one({"userId": user_id}, {"_id": 0})
    if not credits:
        return {"totalCredits": 0, "lockedCredits": 0, "usedCredits": 0, "availableCredits": 0, "expiryDate": None}
    
    # Check expiry
    if credits.get("expiryDate"):
        expiry = datetime.fromisoformat(credits["expiryDate"])
        if expiry < datetime.now(timezone.utc):
            return {"totalCredits": credits["totalCredits"], "lockedCredits": 0, 
                    "usedCredits": credits["totalCredits"], "availableCredits": 0, "expiryDate": credits["expiryDate"]}
    
    available = credits.get("totalCredits", 0) - credits.get("lockedCredits", 0) - credits.get("usedCredits", 0)
    return {
        "totalCredits": credits.get("totalCredits", 0),
        "lockedCredits": credits.get("lockedCredits", 0),
        "usedCredits": credits.get("usedCredits", 0),
        "availableCredits": max(0, available),
        "expiryDate": credits.get("expiryDate")
    }

async def check_profile_unlocked(user_id: str, target_id: str) -> bool:
    """Check if user has unlocked a profile"""
    unlock = await db.profile_unlocks.find_one({
        "userId": user_id,
        "targetId": target_id
    })
    return unlock is not None

async def check_identity_unlocked(user_id: str, target_id: str) -> bool:
    """Check if identity is unlocked (after payment)"""
    # Check if there's a completed campaign with escrow paid
    campaign = await db.campaigns.find_one({
        "$or": [
            {"brandId": user_id, "creatorId": target_id},
            {"creatorId": user_id, "brandId": target_id}
        ],
        "identityUnlocked": True
    })
    return campaign is not None

# ============== AUTH ROUTES ==============

@auth_router.post("/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "passwordHash": get_password_hash(user_data.password),
        "role": user_data.role,
        "hasCompletedOnboarding": False,
        "instagramVerified": False,
        "isAdmin": False,
        "isBanned": False,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    token = create_access_token({"sub": user_id, "email": user_data.email, "role": user_data.role})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user_id, email=user_data.email, role=user_data.role)
    )

@auth_router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if not user or not verify_password(user_data.password, user["passwordHash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user.get("isBanned"):
        raise HTTPException(status_code=403, detail="Account banned")
    
    token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"], 
            email=user["email"], 
            role=user["role"],
            hasCompletedOnboarding=user.get("hasCompletedOnboarding", False),
            isAdmin=user.get("isAdmin", False),
            instagramVerified=user.get("instagramVerified", False)
        )
    )

@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
        hasCompletedOnboarding=current_user.get("hasCompletedOnboarding", False),
        isAdmin=current_user.get("isAdmin", False),
        instagramVerified=current_user.get("instagramVerified", False)
    )

# ============== INSTAGRAM VERIFICATION (SIMULATED FOR DEMO) ==============

@api_router.post("/instagram/verify", response_model=InstagramVerifyResponse)
async def verify_instagram(
    data: InstagramVerifyRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Simulated Instagram OAuth verification for demo purposes.
    In production, this would redirect to Instagram OAuth and fetch real data.
    """
    username = data.instagramUsername.replace("@", "").strip()
    
    if not username:
        raise HTTPException(status_code=400, detail="Instagram username required")
    
    # Simulate Instagram API response
    # In production: Use Instagram Graph API with OAuth
    simulated_user_id = f"ig_{uuid.uuid4().hex[:12]}"
    simulated_followers = random.randint(5000, 500000)
    simulated_avg_likes = int(simulated_followers * random.uniform(0.02, 0.08))
    simulated_avg_comments = int(simulated_avg_likes * random.uniform(0.05, 0.15))
    
    engagement_rate = calculate_engagement_rate(
        simulated_followers, 
        simulated_avg_likes, 
        simulated_avg_comments
    )
    
    # Store verification in user record
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "instagramVerified": True,
            "instagramUserId": simulated_user_id,
            "instagramUsername": username
        }}
    )
    
    # Update profile with Instagram data
    collection = "creator_profiles" if current_user["role"] == "creator" else "brand_profiles"
    await db[collection].update_one(
        {"userId": current_user["id"]},
        {"$set": {
            "instagramUserId": simulated_user_id,
            "instagramUsername": username,
            "instagramVerified": True,
            "followersCount": simulated_followers,
            "engagementRate": engagement_rate
        }}
    )
    
    return InstagramVerifyResponse(
        success=True,
        instagramUserId=simulated_user_id,
        instagramUsername=username,
        followersCount=simulated_followers,
        engagementRate=engagement_rate,
        message="Instagram verified successfully! (Demo Mode)"
    )

# ============== CREATOR ROUTES ==============

@creator_router.post("/profile", response_model=CreatorProfileFull)
async def create_creator_profile(profile: CreatorProfileCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "creator":
        raise HTTPException(status_code=403, detail="Only creators can create creator profiles")
    
    existing = await db.creator_profiles.find_one({"userId": current_user["id"]})
    now = datetime.now(timezone.utc).isoformat()
    profile_id = existing["id"] if existing else str(uuid.uuid4())
    
    profile_doc = {
        "id": profile_id,
        "userId": current_user["id"],
        "name": profile.name,
        "bio": profile.bio or "",
        "location": profile.location or "",
        "instagramUserId": existing.get("instagramUserId") if existing else None,
        "instagramUsername": existing.get("instagramUsername") if existing else None,
        "instagramVerified": existing.get("instagramVerified", False) if existing else False,
        "followersCount": existing.get("followersCount", 0) if existing else 0,
        "engagementRate": existing.get("engagementRate", 0) if existing else 0,
        "niches": profile.niches or [],
        "isOpenToBarter": profile.isOpenToBarter or False,
        "rates": (profile.rates.model_dump() if profile.rates else RateInfo().model_dump()),
        "profilePhotoUrl": profile.profilePhotoUrl or "",
        "sampleContent": profile.sampleContent or [],
        "createdAt": existing["createdAt"] if existing else now,
        "updatedAt": now
    }
    
    if existing:
        await db.creator_profiles.update_one({"id": profile_id}, {"$set": profile_doc})
    else:
        await db.creator_profiles.insert_one(profile_doc)
    
    await db.users.update_one({"id": current_user["id"]}, {"$set": {"hasCompletedOnboarding": True}})
    
    return CreatorProfileFull(**profile_doc)

@creator_router.get("/profile", response_model=CreatorProfileFull)
async def get_my_creator_profile(current_user: dict = Depends(get_current_user)):
    profile = await db.creator_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return CreatorProfileFull(**profile)

# ============== BUSINESS ROUTES ==============

@business_router.post("/profile", response_model=BrandProfileFull)
async def create_brand_profile(profile: BrandProfileCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only businesses can create brand profiles")
    
    existing = await db.brand_profiles.find_one({"userId": current_user["id"]})
    now = datetime.now(timezone.utc).isoformat()
    profile_id = existing["id"] if existing else str(uuid.uuid4())
    
    # Count past collabs
    past_collab_count = await db.campaigns.count_documents({
        "brandId": current_user["id"],
        "campaignStatus": "completed"
    })
    
    profile_doc = {
        "id": profile_id,
        "userId": current_user["id"],
        "brandName": profile.brandName,
        "industry": profile.industry or "",
        "bio": profile.bio or "",
        "location": profile.location or "",
        "instagramUserId": existing.get("instagramUserId") if existing else None,
        "instagramUsername": existing.get("instagramUsername") if existing else None,
        "instagramVerified": existing.get("instagramVerified", False) if existing else False,
        "budgetRange": profile.budgetRange or "",
        "preferredNiches": profile.preferredNiches or [],
        "isOpenToBarter": profile.isOpenToBarter or False,
        "profilePhotoUrl": profile.profilePhotoUrl or "",
        "pastCampaigns": profile.pastCampaigns or [],
        "pastCollabCount": past_collab_count,
        "createdAt": existing["createdAt"] if existing else now,
        "updatedAt": now
    }
    
    if existing:
        await db.brand_profiles.update_one({"id": profile_id}, {"$set": profile_doc})
    else:
        await db.brand_profiles.insert_one(profile_doc)
    
    await db.users.update_one({"id": current_user["id"]}, {"$set": {"hasCompletedOnboarding": True}})
    
    return BrandProfileFull(**profile_doc)

@business_router.get("/profile", response_model=BrandProfileFull)
async def get_my_brand_profile(current_user: dict = Depends(get_current_user)):
    profile = await db.brand_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return BrandProfileFull(**profile)

# ============== TWO-WAY MARKETPLACE ==============

@marketplace_router.get("/creators", response_model=List[CreatorDiscovery])
async def discover_creators(
    niche: Optional[str] = Query(None),
    minFollowers: Optional[int] = Query(None),
    maxFollowers: Optional[int] = Query(None),
    location: Optional[str] = Query(None),
    openToBarter: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Brands discover creators (Layer 1 - Free)"""
    query = {"instagramVerified": True}  # Only show verified profiles
    
    if niche and niche != 'All':
        query["niches"] = {"$in": [niche]}
    if minFollowers:
        query["followersCount"] = {"$gte": minFollowers}
    if maxFollowers:
        query.setdefault("followersCount", {})["$lte"] = maxFollowers
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if openToBarter:
        query["isOpenToBarter"] = True
    
    creators = await db.creator_profiles.find(query, {"_id": 0}).limit(limit).to_list(limit)
    
    discovery_list = []
    for c in creators:
        is_unlocked = await check_profile_unlocked(current_user["id"], c["id"])
        
        discovery_list.append(CreatorDiscovery(
            id=c["id"],
            niches=c.get("niches", []),
            location=c.get("location", ""),
            followersDisplay=format_followers(c.get("followersCount", 0)),
            engagementRateDisplay=format_engagement_rate(c.get("engagementRate", 0)),
            rateRange=format_rate_range(c.get("rates", {})),
            isOpenToBarter=c.get("isOpenToBarter", False),
            previewContent=c.get("sampleContent", [])[:3],
            isUnlocked=is_unlocked
        ))
    
    return discovery_list

@marketplace_router.get("/brands", response_model=List[BrandDiscovery])
async def discover_brands(
    industry: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    openToBarter: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Creators discover brands (Layer 1 - Free)"""
    query = {"instagramVerified": True}
    
    if industry:
        query["industry"] = {"$regex": industry, "$options": "i"}
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if openToBarter:
        query["isOpenToBarter"] = True
    
    brands = await db.brand_profiles.find(query, {"_id": 0}).limit(limit).to_list(limit)
    
    discovery_list = []
    for b in brands:
        is_unlocked = await check_profile_unlocked(current_user["id"], b["id"])
        
        discovery_list.append(BrandDiscovery(
            id=b["id"],
            brandName=b.get("brandName", ""),
            industry=b.get("industry", ""),
            location=b.get("location", ""),
            budgetRange=b.get("budgetRange", ""),
            preferredNiches=b.get("preferredNiches", []),
            isOpenToBarter=b.get("isOpenToBarter", False),
            pastCollabCount=b.get("pastCollabCount", 0),
            isUnlocked=is_unlocked
        ))
    
    return discovery_list

@marketplace_router.get("/creators/{creator_id}/unlocked", response_model=CreatorUnlocked)
async def get_unlocked_creator(creator_id: str, current_user: dict = Depends(get_current_user)):
    """Get creator context after spending credit (Layer 2)"""
    is_unlocked = await check_profile_unlocked(current_user["id"], creator_id)
    if not is_unlocked:
        raise HTTPException(status_code=403, detail="Spend a credit to unlock this profile")
    
    creator = await db.creator_profiles.find_one({"id": creator_id}, {"_id": 0})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    return CreatorUnlocked(
        id=creator["id"],
        niches=creator.get("niches", []),
        location=creator.get("location", ""),
        followersCount=creator.get("followersCount", 0),
        engagementRate=creator.get("engagementRate", 0),
        rates=RateInfo(**creator.get("rates", {})),
        isOpenToBarter=creator.get("isOpenToBarter", False),
        sampleContent=creator.get("sampleContent", []),
        bio=creator.get("bio", ""),
        profilePhotoUrl=creator.get("profilePhotoUrl", "")
    )

@marketplace_router.get("/brands/{brand_id}/unlocked", response_model=BrandUnlocked)
async def get_unlocked_brand(brand_id: str, current_user: dict = Depends(get_current_user)):
    """Get brand context after spending credit (Layer 2)"""
    is_unlocked = await check_profile_unlocked(current_user["id"], brand_id)
    if not is_unlocked:
        raise HTTPException(status_code=403, detail="Spend a credit to unlock this profile")
    
    brand = await db.brand_profiles.find_one({"id": brand_id}, {"_id": 0})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    return BrandUnlocked(
        id=brand["id"],
        brandName=brand.get("brandName", ""),
        industry=brand.get("industry", ""),
        bio=brand.get("bio", ""),
        location=brand.get("location", ""),
        budgetRange=brand.get("budgetRange", ""),
        preferredNiches=brand.get("preferredNiches", []),
        isOpenToBarter=brand.get("isOpenToBarter", False),
        pastCampaigns=brand.get("pastCampaigns", []),
        pastCollabCount=brand.get("pastCollabCount", 0),
        profilePhotoUrl=brand.get("profilePhotoUrl", "")
    )

@marketplace_router.post("/{target_type}/{target_id}/unlock")
async def unlock_profile(
    target_type: Literal["creator", "brand"],
    target_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Spend 1 credit to unlock a profile (context only, not identity)"""
    # Check if already unlocked
    is_unlocked = await check_profile_unlocked(current_user["id"], target_id)
    if is_unlocked:
        return {"message": "Profile already unlocked", "success": True}
    
    # Check credits
    credits = await get_user_credits(current_user["id"])
    if credits["availableCredits"] <= 0:
        raise HTTPException(status_code=402, detail="No credits available. Purchase an unlock pack.")
    
    # Verify target exists
    collection = "creator_profiles" if target_type == "creator" else "brand_profiles"
    target = await db[collection].find_one({"id": target_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail=f"{target_type.title()} not found")
    
    # Use credit
    await db.credits.update_one(
        {"userId": current_user["id"]},
        {"$inc": {"usedCredits": 1}}
    )
    
    # Record unlock
    await db.profile_unlocks.insert_one({
        "id": str(uuid.uuid4()),
        "userId": current_user["id"],
        "targetId": target_id,
        "targetType": target_type,
        "unlockedAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Profile unlocked! You can now see full context.", "success": True}

# ============== TWO-WAY REQUEST SYSTEM ==============

@request_router.post("/", response_model=CollabRequestResponse, status_code=201)
async def create_collab_request(
    req_data: CollabRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send a collab request (works both ways: brand→creator or creator→brand)"""
    sender_type = current_user["role"]
    
    # Validate receiver
    if req_data.receiverType == sender_type:
        raise HTTPException(status_code=400, detail="Cannot send request to same role type")
    
    collection = "creator_profiles" if req_data.receiverType == "creator" else "brand_profiles"
    receiver = await db[collection].find_one({"id": req_data.receiverId}, {"_id": 0})
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")
    
    # Check credits
    credits = await get_user_credits(current_user["id"])
    if credits["availableCredits"] <= 0:
        raise HTTPException(status_code=402, detail="No credits available")
    
    # Get sender profile
    sender_collection = "creator_profiles" if sender_type == "creator" else "brand_profiles"
    sender_profile = await db[sender_collection].find_one({"userId": current_user["id"]}, {"_id": 0})
    if not sender_profile:
        raise HTTPException(status_code=404, detail="Complete your profile first")
    
    sender_name = sender_profile.get("name" if sender_type == "creator" else "brandName", "Unknown")
    receiver_name = receiver.get("name" if req_data.receiverType == "creator" else "brandName", "Unknown")
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=REQUEST_EXPIRY_HOURS)
    
    request_doc = {
        "id": str(uuid.uuid4()),
        "senderId": sender_profile["id"],
        "senderUserId": current_user["id"],
        "senderType": sender_type,
        "senderName": sender_name,
        "receiverId": req_data.receiverId,
        "receiverUserId": receiver["userId"],
        "receiverType": req_data.receiverType,
        "receiverName": receiver_name,
        "message": req_data.message,
        "proposedBudget": req_data.proposedBudget or 0,
        "deliverables": req_data.deliverables or "",
        "status": "pending",
        "creditState": "locked",  # Credit locked until response
        "identityUnlocked": False,
        "expiresAt": expires_at.isoformat(),
        "createdAt": now.isoformat(),
        "updatedAt": now.isoformat()
    }
    
    # Lock 1 credit
    await db.credits.update_one(
        {"userId": current_user["id"]},
        {"$inc": {"lockedCredits": 1}}
    )
    
    await db.collab_requests.insert_one(request_doc)
    
    # Auto-unlock profile for communication
    await db.profile_unlocks.update_one(
        {"userId": current_user["id"], "targetId": req_data.receiverId},
        {"$setOnInsert": {
            "id": str(uuid.uuid4()),
            "userId": current_user["id"],
            "targetId": req_data.receiverId,
            "targetType": req_data.receiverType,
            "unlockedAt": now.isoformat()
        }},
        upsert=True
    )
    
    return CollabRequestResponse(**request_doc)

@request_router.get("/incoming", response_model=List[CollabRequestResponse])
async def get_incoming_requests(current_user: dict = Depends(get_current_user)):
    """Get requests received by current user"""
    requests = await db.collab_requests.find(
        {"receiverUserId": current_user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(100)
    
    # Check and expire old requests
    now = datetime.now(timezone.utc)
    for req in requests:
        if req["status"] == "pending" and datetime.fromisoformat(req["expiresAt"]) < now:
            await expire_request(req["id"])
            req["status"] = "expired"
            req["creditState"] = "refunded"
    
    return [CollabRequestResponse(**r) for r in requests]

@request_router.get("/outgoing", response_model=List[CollabRequestResponse])
async def get_outgoing_requests(current_user: dict = Depends(get_current_user)):
    """Get requests sent by current user"""
    requests = await db.collab_requests.find(
        {"senderUserId": current_user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(100)
    
    return [CollabRequestResponse(**r) for r in requests]

async def expire_request(request_id: str):
    """Auto-expire request and refund credit"""
    req = await db.collab_requests.find_one({"id": request_id}, {"_id": 0})
    if not req or req["status"] != "pending":
        return
    
    # Refund credit
    await db.credits.update_one(
        {"userId": req["senderUserId"]},
        {"$inc": {"lockedCredits": -1}}  # Unlock the credit
    )
    
    # Update request
    await db.collab_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "expired",
            "creditState": "refunded",
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }}
    )

@request_router.patch("/{request_id}/respond")
async def respond_to_request(
    request_id: str,
    action: Literal["accept", "reject"] = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Accept or reject a collab request"""
    req = await db.collab_requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if req["receiverUserId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if req["status"] != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")
    
    now = datetime.now(timezone.utc)
    
    if action == "reject":
        # REFUND credit to sender
        await db.credits.update_one(
            {"userId": req["senderUserId"]},
            {"$inc": {"lockedCredits": -1}}  # Unlock credit (refund)
        )
        
        await db.collab_requests.update_one(
            {"id": request_id},
            {"$set": {
                "status": "rejected",
                "creditState": "refunded",
                "updatedAt": now.isoformat()
            }}
        )
        
        return {"message": "Request rejected. Credit refunded to sender.", "success": True}
    
    else:  # accept
        # CONSUME credit (move from locked to used)
        await db.credits.update_one(
            {"userId": req["senderUserId"]},
            {"$inc": {"lockedCredits": -1, "usedCredits": 1}}
        )
        
        # Auto-unlock sender's profile for receiver
        await db.profile_unlocks.update_one(
            {"userId": current_user["id"], "targetId": req["senderId"]},
            {"$setOnInsert": {
                "id": str(uuid.uuid4()),
                "userId": current_user["id"],
                "targetId": req["senderId"],
                "targetType": req["senderType"],
                "unlockedAt": now.isoformat()
            }},
            upsert=True
        )
        
        await db.collab_requests.update_one(
            {"id": request_id},
            {"$set": {
                "status": "accepted",
                "creditState": "consumed",
                "updatedAt": now.isoformat()
            }}
        )
        
        return {"message": "Request accepted! Negotiation can begin.", "success": True}

# ============== CAMPAIGNS (After Request Acceptance) ==============

@api_router.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a campaign from an accepted request"""
    req = await db.collab_requests.find_one({"id": campaign_data.requestId}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if req["status"] != "accepted":
        raise HTTPException(status_code=400, detail="Request must be accepted first")
    
    # Determine brand and creator
    if req["senderType"] == "business":
        brand_id = req["senderUserId"]
        creator_id = req["receiverUserId"]
    else:
        brand_id = req["receiverUserId"]
        creator_id = req["senderUserId"]
    
    now = datetime.now(timezone.utc).isoformat()
    
    campaign_doc = {
        "id": str(uuid.uuid4()),
        "requestId": campaign_data.requestId,
        "brandId": brand_id,
        "creatorId": creator_id,
        "title": campaign_data.title,
        "brief": campaign_data.brief,
        "price": campaign_data.price,
        "deliverables": campaign_data.deliverables,
        "timeline": campaign_data.timeline,
        "isBarter": campaign_data.isBarter,
        "barterDetails": campaign_data.barterDetails or "",
        "escrowStatus": "pending",
        "campaignStatus": "negotiating",
        "identityUnlocked": False,
        "createdAt": now,
        "updatedAt": now
    }
    
    await db.campaigns.insert_one(campaign_doc)
    
    return CampaignResponse(**campaign_doc)

@api_router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Get campaign details"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["brandId"] != current_user["id"] and campaign["creatorId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Add Instagram handles if identity is unlocked
    if campaign.get("identityUnlocked"):
        creator_profile = await db.creator_profiles.find_one({"userId": campaign["creatorId"]}, {"_id": 0})
        brand_profile = await db.brand_profiles.find_one({"userId": campaign["brandId"]}, {"_id": 0})
        
        if creator_profile:
            campaign["creatorInstagram"] = creator_profile.get("instagramUsername")
        if brand_profile:
            campaign["brandInstagram"] = brand_profile.get("instagramUsername")
    
    return CampaignResponse(**campaign)

@api_router.get("/campaigns/my/list", response_model=List[CampaignResponse])
async def get_my_campaigns(current_user: dict = Depends(get_current_user)):
    """Get all campaigns for current user"""
    campaigns = await db.campaigns.find(
        {"$or": [{"brandId": current_user["id"]}, {"creatorId": current_user["id"]}]},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(100)
    
    return [CampaignResponse(**c) for c in campaigns]

@api_router.patch("/campaigns/{campaign_id}/confirm")
async def confirm_campaign(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Both parties confirm the campaign terms"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "campaignStatus": "confirmed",
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Campaign confirmed! Proceed to payment.", "success": True}

# ============== PAYMENTS (TEST MODE) ==============

@payment_router.get("/credits", response_model=UnlockCreditsResponse)
async def get_credits(current_user: dict = Depends(get_current_user)):
    """Get user's credit balance"""
    credits = await get_user_credits(current_user["id"])
    return UnlockCreditsResponse(**credits)

@payment_router.post("/unlock-pack/order", response_model=PaymentOrderResponse)
async def create_unlock_order(current_user: dict = Depends(get_current_user)):
    """Create order for unlock pack (₹200 = 5 credits)"""
    order_id = f"order_test_{uuid.uuid4().hex[:16]}"
    
    if razorpay_client:
        try:
            order = razorpay_client.order.create({
                "amount": UNLOCK_PACK_PRICE,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {"userId": current_user["id"], "type": "unlock_pack"}
            })
            order_id = order["id"]
        except Exception as e:
            logging.error(f"Razorpay error: {e}")
    
    # Store order
    await db.payments.insert_one({
        "id": str(uuid.uuid4()),
        "orderId": order_id,
        "userId": current_user["id"],
        "type": "unlock_pack",
        "amount": UNLOCK_PACK_PRICE,
        "mode": "TEST",
        "status": "created",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return PaymentOrderResponse(
        orderId=order_id,
        amount=UNLOCK_PACK_PRICE,
        currency="INR",
        keyId=RAZORPAY_KEY_ID,
        testMode=True
    )

@payment_router.post("/unlock-pack/verify")
async def verify_unlock_payment(
    payment: PaymentVerifyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Verify unlock pack payment and add credits"""
    # In TEST MODE, we accept all payments
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=UNLOCK_CREDIT_VALIDITY_DAYS)
    
    # Update payment status
    await db.payments.update_one(
        {"orderId": payment.razorpay_order_id},
        {"$set": {
            "paymentId": payment.razorpay_payment_id,
            "status": "paid_test",
            "paidAt": now.isoformat()
        }}
    )
    
    # Add credits
    existing = await db.credits.find_one({"userId": current_user["id"]})
    if existing:
        await db.credits.update_one(
            {"userId": current_user["id"]},
            {
                "$inc": {"totalCredits": UNLOCK_PACK_CREDITS},
                "$set": {"expiryDate": expiry.isoformat()}
            }
        )
    else:
        await db.credits.insert_one({
            "userId": current_user["id"],
            "totalCredits": UNLOCK_PACK_CREDITS,
            "lockedCredits": 0,
            "usedCredits": 0,
            "expiryDate": expiry.isoformat(),
            "createdAt": now.isoformat()
        })
    
    return {"message": f"Payment successful (TEST)! {UNLOCK_PACK_CREDITS} credits added.", "success": True}

@payment_router.post("/unlock-pack/demo")
async def add_demo_credits(current_user: dict = Depends(get_current_user)):
    """Add free demo credits for testing (no real payment)"""
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=UNLOCK_CREDIT_VALIDITY_DAYS)
    
    existing = await db.credits.find_one({"userId": current_user["id"]})
    if existing:
        await db.credits.update_one(
            {"userId": current_user["id"]},
            {
                "$inc": {"totalCredits": UNLOCK_PACK_CREDITS},
                "$set": {"expiryDate": expiry.isoformat()}
            }
        )
    else:
        await db.credits.insert_one({
            "userId": current_user["id"],
            "totalCredits": UNLOCK_PACK_CREDITS,
            "lockedCredits": 0,
            "usedCredits": 0,
            "expiryDate": expiry.isoformat(),
            "createdAt": now.isoformat()
        })
    
    return {"message": f"Demo credits added! {UNLOCK_PACK_CREDITS} credits valid for 7 days.", "success": True}

@payment_router.post("/escrow/{campaign_id}/order", response_model=PaymentOrderResponse)
async def create_escrow_order(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Create escrow payment order for campaign"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["brandId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only brand can pay escrow")
    
    if campaign["escrowStatus"] != "pending":
        raise HTTPException(status_code=400, detail="Escrow already processed")
    
    amount_paise = int(campaign["price"] * 100)
    order_id = f"escrow_test_{uuid.uuid4().hex[:16]}"
    
    if razorpay_client:
        try:
            order = razorpay_client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {"userId": current_user["id"], "campaignId": campaign_id, "type": "escrow"}
            })
            order_id = order["id"]
        except Exception as e:
            logging.error(f"Razorpay error: {e}")
    
    await db.payments.insert_one({
        "id": str(uuid.uuid4()),
        "orderId": order_id,
        "userId": current_user["id"],
        "campaignId": campaign_id,
        "type": "escrow",
        "amount": amount_paise,
        "mode": "TEST",
        "status": "created",
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return PaymentOrderResponse(
        orderId=order_id,
        amount=amount_paise,
        currency="INR",
        keyId=RAZORPAY_KEY_ID,
        testMode=True
    )

@payment_router.post("/escrow/{campaign_id}/verify")
async def verify_escrow_payment(
    campaign_id: str,
    payment: PaymentVerifyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Verify escrow payment - UNLOCKS IDENTITY"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    now = datetime.now(timezone.utc)
    
    # Update payment
    await db.payments.update_one(
        {"orderId": payment.razorpay_order_id},
        {"$set": {
            "paymentId": payment.razorpay_payment_id,
            "status": "paid_test",
            "paidAt": now.isoformat()
        }}
    )
    
    # Update campaign - UNLOCK IDENTITY
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "escrowStatus": "paid_test",
            "campaignStatus": "in_progress",
            "identityUnlocked": True,
            "escrowPaidAt": now.isoformat(),
            "updatedAt": now.isoformat()
        }}
    )
    
    return {
        "message": "Escrow paid (TEST)! Instagram handles are now visible.",
        "success": True,
        "identityUnlocked": True
    }

@payment_router.post("/escrow/{campaign_id}/demo")
async def demo_escrow_payment(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Demo escrow payment - UNLOCKS IDENTITY without real payment"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["brandId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only brand can pay escrow")
    
    now = datetime.now(timezone.utc)
    
    # Update campaign - UNLOCK IDENTITY
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "escrowStatus": "paid_test",
            "campaignStatus": "in_progress",
            "identityUnlocked": True,
            "escrowPaidAt": now.isoformat(),
            "updatedAt": now.isoformat()
        }}
    )
    
    return {
        "message": "Demo escrow marked as paid! Instagram handles unlocked.",
        "success": True,
        "identityUnlocked": True
    }

# ============== MESSAGES (WITH ANTI-BYPASS) ==============

@message_router.get("/{campaign_id}", response_model=List[MessageResponse])
async def get_messages(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Get chat messages for a campaign"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["brandId"] != current_user["id"] and campaign["creatorId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = await db.messages.find({"campaignId": campaign_id}, {"_id": 0}).sort("createdAt", 1).to_list(500)
    return [MessageResponse(**m) for m in messages]

@message_router.post("/{campaign_id}", response_model=MessageResponse)
async def send_message(
    campaign_id: str,
    msg_data: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send a message in campaign chat"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["brandId"] != current_user["id"] and campaign["creatorId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check for bypass BEFORE identity unlock
    is_blocked = False
    block_reason = None
    
    if not campaign.get("identityUnlocked"):
        is_blocked, block_reason = check_message_for_bypass(msg_data.text)
        
        if is_blocked:
            await db.bypass_attempts.insert_one({
                "id": str(uuid.uuid4()),
                "campaignId": campaign_id,
                "userId": current_user["id"],
                "message": msg_data.text,
                "reason": block_reason,
                "createdAt": datetime.now(timezone.utc).isoformat()
            })
    
    # Get sender name
    sender_name = current_user["email"]
    if current_user["role"] == "creator":
        profile = await db.creator_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
        if profile:
            sender_name = profile.get("name", sender_name)
    else:
        profile = await db.brand_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
        if profile:
            sender_name = profile.get("brandName", sender_name)
    
    message_doc = {
        "id": str(uuid.uuid4()),
        "campaignId": campaign_id,
        "senderUserId": current_user["id"],
        "senderName": sender_name,
        "text": msg_data.text if not is_blocked else "[Message blocked - external contact not allowed before payment]",
        "isBlocked": is_blocked,
        "blockReason": block_reason,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.messages.insert_one(message_doc)
    
    if is_blocked:
        # Add system warning
        await db.messages.insert_one({
            "id": str(uuid.uuid4()),
            "campaignId": campaign_id,
            "senderUserId": "system",
            "senderName": "🍊 Orange",
            "text": "⚠️ External contact sharing is blocked until escrow payment. Keep communication inside Orange for safety.",
            "isBlocked": False,
            "blockReason": None,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
    
    return MessageResponse(**message_doc)

# ============== ADMIN ==============

@admin_router.get("/stats")
async def get_admin_stats(admin: dict = Depends(get_admin_user)):
    """Admin dashboard stats"""
    stats = {
        "totalUsers": await db.users.count_documents({}),
        "totalCreators": await db.creator_profiles.count_documents({}),
        "totalBrands": await db.brand_profiles.count_documents({}),
        "verifiedCreators": await db.creator_profiles.count_documents({"instagramVerified": True}),
        "verifiedBrands": await db.brand_profiles.count_documents({"instagramVerified": True}),
        "totalRequests": await db.collab_requests.count_documents({}),
        "totalCampaigns": await db.campaigns.count_documents({}),
        "completedCampaigns": await db.campaigns.count_documents({"campaignStatus": "completed"}),
        "bypassAttempts": await db.bypass_attempts.count_documents({}),
        "totalPayments": await db.payments.count_documents({"status": "paid_test"})
    }
    return stats

@admin_router.get("/bypass-attempts")
async def get_bypass_attempts(limit: int = 50, admin: dict = Depends(get_admin_user)):
    """Get flagged bypass attempts"""
    attempts = await db.bypass_attempts.find({}, {"_id": 0}).sort("createdAt", -1).limit(limit).to_list(limit)
    return attempts

@admin_router.post("/users/{user_id}/ban")
async def ban_user(user_id: str, admin: dict = Depends(get_admin_user)):
    """Ban a user"""
    await db.users.update_one({"id": user_id}, {"$set": {"isBanned": True}})
    return {"message": "User banned"}

# ============== UPLOAD ==============

@api_router.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Upload file to Cloudinary"""
    try:
        contents = await file.read()
        content_type = file.content_type or ""
        resource_type = "video" if content_type.startswith("video") else "image"
        
        result = cloudinary.uploader.upload(
            contents,
            resource_type=resource_type,
            folder="orange_marketplace",
            public_id=f"{current_user['id']}_{uuid.uuid4()}"
        )
        
        return {
            "url": result.get("secure_url", result.get("url", "")),
            "thumbnailUrl": result.get("secure_url", result.get("url", "")),
            "type": resource_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# ============== SEED ==============

@api_router.post("/seed")
async def seed_data():
    """Seed demo data"""
    # Clear existing
    for col in ["users", "creator_profiles", "brand_profiles", "credits", "profile_unlocks", 
                "collab_requests", "campaigns", "messages", "payments", "bypass_attempts"]:
        await db[col].delete_many({})
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Admin
    admin_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": admin_id,
        "email": "admin@orange.com",
        "passwordHash": get_password_hash("admin123"),
        "role": "business",
        "hasCompletedOnboarding": True,
        "instagramVerified": True,
        "isAdmin": True,
        "isBanned": False,
        "createdAt": now
    })
    
    # Sample Creators
    creators = [
        {"name": "Priya Sharma", "location": "Mumbai", "niches": ["Fashion", "Lifestyle"], 
         "followers": 520000, "engagement": 5.8, "rates": {"reelPrice": 15000, "storyPrice": 5000, "carouselPrice": 10000, "postPrice": 8000, "bundlePrice": 25000}},
        {"name": "Arjun Kapoor", "location": "Delhi", "niches": ["Fitness", "Sports"],
         "followers": 280000, "engagement": 4.2, "rates": {"reelPrice": 12000, "storyPrice": 4000, "carouselPrice": 8000, "postPrice": 6000, "bundlePrice": 20000}},
        {"name": "Meera Patel", "location": "Bangalore", "niches": ["Beauty", "Skincare"],
         "followers": 150000, "engagement": 6.5, "rates": {"reelPrice": 8000, "storyPrice": 3000, "carouselPrice": 6000, "postPrice": 4000, "bundlePrice": 15000}},
    ]
    
    for i, c in enumerate(creators):
        user_id = str(uuid.uuid4())
        profile_id = str(uuid.uuid4())
        
        await db.users.insert_one({
            "id": user_id,
            "email": f"creator{i+1}@orange.com",
            "passwordHash": get_password_hash("password123"),
            "role": "creator",
            "hasCompletedOnboarding": True,
            "instagramVerified": True,
            "instagramUserId": f"ig_{uuid.uuid4().hex[:8]}",
            "instagramUsername": f"@{c['name'].lower().replace(' ', '')}",
            "isAdmin": False,
            "isBanned": False,
            "createdAt": now
        })
        
        await db.creator_profiles.insert_one({
            "id": profile_id,
            "userId": user_id,
            "name": c["name"],
            "bio": f"Content creator passionate about {c['niches'][0].lower()}",
            "location": c["location"],
            "instagramUserId": f"ig_{uuid.uuid4().hex[:8]}",
            "instagramUsername": f"@{c['name'].lower().replace(' ', '')}",
            "instagramVerified": True,
            "followersCount": c["followers"],
            "engagementRate": c["engagement"],
            "niches": c["niches"],
            "isOpenToBarter": i % 2 == 0,
            "rates": c["rates"],
            "profilePhotoUrl": f"https://i.pravatar.cc/300?img={10+i}",
            "sampleContent": [],
            "createdAt": now,
            "updatedAt": now
        })
    
    # Sample Brands
    brands = [
        {"name": "Glow Cosmetics", "industry": "Beauty", "location": "Mumbai", "budget": "₹10k-₹50k", "niches": ["Beauty", "Skincare"]},
        {"name": "FitLife Nutrition", "industry": "Health & Fitness", "location": "Delhi", "budget": "₹15k-₹40k", "niches": ["Fitness", "Health"]},
    ]
    
    for i, b in enumerate(brands):
        user_id = str(uuid.uuid4())
        profile_id = str(uuid.uuid4())
        
        await db.users.insert_one({
            "id": user_id,
            "email": f"brand{i+1}@orange.com",
            "passwordHash": get_password_hash("password123"),
            "role": "business",
            "hasCompletedOnboarding": True,
            "instagramVerified": True,
            "instagramUserId": f"ig_{uuid.uuid4().hex[:8]}",
            "instagramUsername": f"@{b['name'].lower().replace(' ', '')}",
            "isAdmin": False,
            "isBanned": False,
            "createdAt": now
        })
        
        # Give brands some credits
        expiry = datetime.now(timezone.utc) + timedelta(days=7)
        await db.credits.insert_one({
            "userId": user_id,
            "totalCredits": 5,
            "lockedCredits": 0,
            "usedCredits": 0,
            "expiryDate": expiry.isoformat(),
            "createdAt": now
        })
        
        await db.brand_profiles.insert_one({
            "id": profile_id,
            "userId": user_id,
            "brandName": b["name"],
            "industry": b["industry"],
            "bio": f"Leading brand in {b['industry'].lower()}",
            "location": b["location"],
            "instagramUserId": f"ig_{uuid.uuid4().hex[:8]}",
            "instagramUsername": f"@{b['name'].lower().replace(' ', '')}",
            "instagramVerified": True,
            "budgetRange": b["budget"],
            "preferredNiches": b["niches"],
            "isOpenToBarter": True,
            "profilePhotoUrl": f"https://i.pravatar.cc/300?img={20+i}",
            "pastCampaigns": [],
            "pastCollabCount": 0,
            "createdAt": now,
            "updatedAt": now
        })
    
    return {
        "message": "Seed data created!",
        "creators": len(creators),
        "brands": len(brands),
        "demo_accounts": {
            "admin": "admin@orange.com / admin123",
            "creator": "creator1@orange.com / password123",
            "brand": "brand1@orange.com / password123 (5 credits)"
        }
    }

# ============== ROOT ==============

@api_router.get("/")
async def root():
    return {"message": "Orange - Two-Way Creator Marketplace API 🍊", "version": "2.0"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "testMode": True}

# Include routers
api_router.include_router(auth_router)
api_router.include_router(creator_router)
api_router.include_router(business_router)
api_router.include_router(marketplace_router)
api_router.include_router(request_router)
api_router.include_router(payment_router)
api_router.include_router(message_router)
api_router.include_router(admin_router)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
