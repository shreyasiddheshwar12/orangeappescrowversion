from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Query, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
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

# Razorpay Configuration
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')

razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Pricing Configuration
UNLOCK_PACK_PRICE = 20000  # ₹200 in paise
UNLOCK_PACK_CREDITS = 5
UNLOCK_CREDIT_VALIDITY_DAYS = 7

# Create the main app
app = FastAPI(title="Orange - Creator Marketplace API")

# Create routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
creator_router = APIRouter(prefix="/creator", tags=["Creator"])
business_router = APIRouter(prefix="/business", tags=["Business"])
request_router = APIRouter(prefix="/requests", tags=["Requests"])
message_router = APIRouter(prefix="/messages", tags=["Messages"])
payment_router = APIRouter(prefix="/payments", tags=["Payments"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])

security = HTTPBearer()

# ============== BLOCKED KEYWORDS FOR CHAT ==============
BLOCKED_KEYWORDS = [
    'instagram', 'insta', 'ig', 'dm', 'whatsapp', 'whats app', 'wa',
    'telegram', 'signal', 'snapchat', 'snap', 'twitter', 'x.com',
    'facebook', 'fb', 'linkedin', 'youtube', 'yt',
    '@', 'gmail', 'yahoo', 'hotmail', 'outlook',
    r'\b\d{10}\b',  # Phone numbers
    r'\b\d{5}[\s-]?\d{5}\b',  # Phone with space/dash
]

def check_message_for_bypass(text: str) -> tuple[bool, str]:
    """Check if message contains blocked keywords. Returns (is_blocked, reason)"""
    text_lower = text.lower()
    
    for keyword in BLOCKED_KEYWORDS:
        if keyword.startswith(r'\b'):
            # Regex pattern
            if re.search(keyword, text_lower):
                return True, "Phone numbers are not allowed before payment"
        elif keyword in text_lower:
            return True, f"External contact sharing is not allowed before payment"
    
    return False, ""

# ============== MODELS ==============

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str  # "creator" or "business"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    hasCompletedOnboarding: bool = False
    isAdmin: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class MediaItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    url: str
    thumbnailUrl: str
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class RateInfo(BaseModel):
    reelPrice: Optional[float] = 0
    storyPrice: Optional[float] = 0
    postPrice: Optional[float] = 0
    bundlePrice: Optional[float] = 0

class CreatorProfileCreate(BaseModel):
    name: str
    bio: Optional[str] = ""
    location: Optional[str] = ""
    instagramHandle: Optional[str] = ""
    instagramUrl: Optional[str] = ""
    followersCount: Optional[int] = 0
    engagementRate: Optional[float] = 0
    avgReelViews: Optional[int] = 0
    niches: Optional[List[str]] = []
    isOpenToBarter: Optional[bool] = False
    rates: Optional[RateInfo] = None
    profilePhotoUrl: Optional[str] = ""
    mediaGallery: Optional[List[MediaItem]] = []

class CreatorProfileResponse(BaseModel):
    id: str
    userId: str
    name: str
    bio: str
    location: str
    profilePhotoUrl: str
    instagramHandle: str
    instagramUrl: str
    followersCount: int
    engagementRate: float
    avgReelViews: int
    niches: List[str]
    isOpenToBarter: bool
    rates: RateInfo
    mediaGallery: List[MediaItem]
    createdAt: str
    updatedAt: str

# Discovery Mode Response (Layer 1 - Free)
class CreatorDiscoveryResponse(BaseModel):
    id: str
    displayName: str  # First name only
    niches: List[str]
    city: str
    followersDisplay: str  # "40K+"
    engagementRateDisplay: str  # "~5.8%"
    avgReelViewsDisplay: str  # "10k-20k"
    rateRangeDisplay: str  # "₹5k-₹8k"
    previewImages: List[str]  # Blurred/watermarked
    isOpenToBarter: bool
    isUnlocked: bool = False

# Unlocked Mode Response (Layer 2 - After ₹200)
class CreatorUnlockedResponse(BaseModel):
    id: str
    name: str
    bio: str
    niches: List[str]
    city: str
    followersCount: int
    engagementRate: float
    avgReelViews: int
    rates: RateInfo
    mediaGallery: List[MediaItem]
    isOpenToBarter: bool
    profilePhotoUrl: str
    # Still hidden: instagramHandle, instagramUrl

# Full Access Response (Layer 3 - After Escrow)
class CreatorFullAccessResponse(CreatorProfileResponse):
    pass  # Everything visible

class BusinessProfileCreate(BaseModel):
    brandName: str
    category: Optional[str] = ""
    bio: Optional[str] = ""
    location: Optional[str] = ""
    websiteUrl: Optional[str] = ""
    instagramHandle: Optional[str] = ""
    instagramUrl: Optional[str] = ""
    profilePhotoUrl: Optional[str] = ""
    mediaGallery: Optional[List[MediaItem]] = []

class BusinessProfileResponse(BaseModel):
    id: str
    userId: str
    brandName: str
    category: str
    bio: str
    location: str
    websiteUrl: str
    instagramHandle: str
    instagramUrl: str
    profilePhotoUrl: str
    mediaGallery: List[MediaItem]
    createdAt: str
    updatedAt: str
    unlockCredits: int = 0
    unlockCreditsExpiry: Optional[str] = None

class UnlockCreditsResponse(BaseModel):
    totalCredits: int
    usedCredits: int
    availableCredits: int
    expiryDate: Optional[str]

class PaymentOrderResponse(BaseModel):
    orderId: str
    amount: int
    currency: str
    keyId: str

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class CampaignCreate(BaseModel):
    creatorId: str
    title: str
    brief: str
    deliverables: str
    timeline: str
    price: float
    isBarter: bool = False
    barterDetails: Optional[str] = ""

class CampaignResponse(BaseModel):
    id: str
    brandId: str
    creatorId: str
    title: str
    brief: str
    deliverables: str
    timeline: str
    price: float
    isBarter: bool
    barterDetails: str
    escrowStatus: str  # pending, paid, released, refunded
    campaignStatus: str  # draft, proposed, accepted, in_progress, delivered, completed, cancelled
    createdAt: str
    updatedAt: str
    creatorName: Optional[str] = ""
    brandName: Optional[str] = ""
    # Full access fields (only after escrow)
    instagramHandle: Optional[str] = None
    instagramUrl: Optional[str] = None

class MessageCreate(BaseModel):
    text: str

class MessageResponse(BaseModel):
    id: str
    requestId: str
    senderUserId: str
    senderName: str
    text: str
    createdAt: str
    isBlocked: bool = False
    blockReason: Optional[str] = None

class UploadResponse(BaseModel):
    url: str
    thumbnailUrl: str
    type: str

# Admin Models
class AdminStats(BaseModel):
    totalUsers: int
    totalCreators: int
    totalBrands: int
    totalCampaigns: int
    totalRevenue: float
    bypassAttempts: int
    activeUnlocks: int

class FlaggedChat(BaseModel):
    id: str
    campaignId: str
    senderName: str
    message: str
    reason: str
    createdAt: str

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
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    if not current_user.get("isAdmin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# ============== HELPER FUNCTIONS ==============

def format_followers(count: int) -> str:
    """Format followers count for discovery mode"""
    if count >= 1000000:
        return f"{count // 1000000}M+"
    elif count >= 1000:
        return f"{count // 1000}K+"
    return f"{count}+"

def format_engagement_rate(rate: float) -> str:
    """Format engagement rate for discovery mode (rounded)"""
    return f"~{round(rate, 1)}%"

def format_reel_views(views: int) -> str:
    """Format avg reel views as range"""
    if views >= 100000:
        lower = (views // 100000) * 100
        upper = lower + 100
        return f"{lower}k-{upper}k"
    elif views >= 10000:
        lower = (views // 10000) * 10
        upper = lower + 10
        return f"{lower}k-{upper}k"
    elif views >= 1000:
        lower = (views // 1000)
        upper = lower + 5
        return f"{lower}k-{upper}k"
    return f"{views}+"

def format_rate_range(rates: dict) -> str:
    """Format rate range for discovery mode"""
    prices = [v for v in [rates.get('reelPrice', 0), rates.get('storyPrice', 0), 
                          rates.get('postPrice', 0)] if v > 0]
    if not prices:
        return "Ask for rates"
    min_price = min(prices) // 1000
    max_price = max(prices) // 1000
    if min_price == max_price:
        return f"₹{min_price}k"
    return f"₹{min_price}k-₹{max_price}k"

def get_display_name(full_name: str) -> str:
    """Get first name for discovery mode"""
    return full_name.split()[0] if full_name else "Creator"

async def check_creator_unlocked(brand_id: str, creator_id: str) -> bool:
    """Check if brand has unlocked this creator"""
    unlock = await db.creator_unlocks.find_one({
        "brandId": brand_id,
        "creatorId": creator_id
    })
    return unlock is not None

async def check_escrow_paid(brand_id: str, creator_id: str) -> bool:
    """Check if brand has paid escrow for any campaign with this creator"""
    campaign = await db.campaigns.find_one({
        "brandId": brand_id,
        "creatorId": creator_id,
        "escrowStatus": {"$in": ["paid", "released"]}
    })
    return campaign is not None

async def get_brand_unlock_credits(brand_id: str) -> dict:
    """Get brand's unlock credits"""
    credits = await db.unlock_credits.find_one({"brandId": brand_id}, {"_id": 0})
    if not credits:
        return {"totalCredits": 0, "usedCredits": 0, "availableCredits": 0, "expiryDate": None}
    
    # Check expiry
    if credits.get("expiryDate"):
        expiry = datetime.fromisoformat(credits["expiryDate"])
        if expiry < datetime.now(timezone.utc):
            # Credits expired
            return {"totalCredits": credits["totalCredits"], "usedCredits": credits["totalCredits"], 
                    "availableCredits": 0, "expiryDate": credits["expiryDate"]}
    
    available = credits.get("totalCredits", 0) - credits.get("usedCredits", 0)
    return {
        "totalCredits": credits.get("totalCredits", 0),
        "usedCredits": credits.get("usedCredits", 0),
        "availableCredits": max(0, available),
        "expiryDate": credits.get("expiryDate")
    }

# ============== AUTH ROUTES ==============

@auth_router.post("/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if user_data.role not in ["creator", "business"]:
        raise HTTPException(status_code=400, detail="Role must be 'creator' or 'business'")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "passwordHash": get_password_hash(user_data.password),
        "role": user_data.role,
        "hasCompletedOnboarding": False,
        "isAdmin": False,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    token = create_access_token({"sub": user_id, "email": user_data.email, "role": user_data.role})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user_id, email=user_data.email, role=user_data.role, hasCompletedOnboarding=False)
    )

@auth_router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(user_data.password, user["passwordHash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"], 
            email=user["email"], 
            role=user["role"],
            hasCompletedOnboarding=user.get("hasCompletedOnboarding", False),
            isAdmin=user.get("isAdmin", False)
        )
    )

@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
        hasCompletedOnboarding=current_user.get("hasCompletedOnboarding", False),
        isAdmin=current_user.get("isAdmin", False)
    )

@auth_router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}

# ============== UPLOAD ROUTES ==============

@api_router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
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
        
        url = result.get("secure_url", result.get("url", ""))
        
        if resource_type == "video":
            thumbnail_url = cloudinary.CloudinaryImage(result["public_id"]).build_url(
                resource_type="video",
                format="jpg",
                transformation=[{"start_offset": "2", "width": 400, "height": 400, "crop": "fill"}]
            )
        else:
            thumbnail_url = cloudinary.CloudinaryImage(result["public_id"]).build_url(
                width=400, height=400, crop="fill"
            )
        
        return UploadResponse(url=url, thumbnailUrl=thumbnail_url, type=resource_type)
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# ============== CREATOR ROUTES ==============

@creator_router.post("/profile", response_model=CreatorProfileResponse)
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
        "profilePhotoUrl": profile.profilePhotoUrl or "",
        "instagramHandle": profile.instagramHandle or "",
        "instagramUrl": profile.instagramUrl or "",
        "followersCount": profile.followersCount or 0,
        "engagementRate": profile.engagementRate or 0,
        "avgReelViews": profile.avgReelViews or 0,
        "niches": profile.niches or [],
        "isOpenToBarter": profile.isOpenToBarter or False,
        "rates": (profile.rates.model_dump() if profile.rates else RateInfo().model_dump()),
        "mediaGallery": [m.model_dump() for m in (profile.mediaGallery or [])],
        "createdAt": existing["createdAt"] if existing else now,
        "updatedAt": now
    }
    
    if existing:
        await db.creator_profiles.update_one({"id": profile_id}, {"$set": profile_doc})
    else:
        await db.creator_profiles.insert_one(profile_doc)
    
    await db.users.update_one({"id": current_user["id"]}, {"$set": {"hasCompletedOnboarding": True}})
    
    return CreatorProfileResponse(**profile_doc)

@creator_router.get("/profile", response_model=CreatorProfileResponse)
async def get_my_creator_profile(current_user: dict = Depends(get_current_user)):
    profile = await db.creator_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return CreatorProfileResponse(**profile)

@creator_router.get("/requests", response_model=List[CampaignResponse])
async def get_creator_campaigns(current_user: dict = Depends(get_current_user)):
    profile = await db.creator_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Creator profile not found")
    
    campaigns = await db.campaigns.find({"creatorId": profile["id"]}, {"_id": 0}).to_list(100)
    
    for campaign in campaigns:
        business = await db.business_profiles.find_one({"userId": campaign["brandId"]}, {"_id": 0})
        if business:
            campaign["brandName"] = business.get("brandName", "")
        campaign["creatorName"] = profile.get("name", "")
        
        # Only show Instagram after escrow paid
        if campaign.get("escrowStatus") in ["paid", "released"]:
            campaign["instagramHandle"] = profile.get("instagramHandle")
            campaign["instagramUrl"] = profile.get("instagramUrl")
    
    return [CampaignResponse(**c) for c in campaigns]

# ============== BUSINESS ROUTES ==============

@business_router.post("/profile", response_model=BusinessProfileResponse)
async def create_business_profile(profile: BusinessProfileCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only businesses can create business profiles")
    
    existing = await db.business_profiles.find_one({"userId": current_user["id"]})
    now = datetime.now(timezone.utc).isoformat()
    profile_id = existing["id"] if existing else str(uuid.uuid4())
    
    profile_doc = {
        "id": profile_id,
        "userId": current_user["id"],
        "brandName": profile.brandName,
        "category": profile.category or "",
        "bio": profile.bio or "",
        "location": profile.location or "",
        "websiteUrl": profile.websiteUrl or "",
        "instagramHandle": profile.instagramHandle or "",
        "instagramUrl": profile.instagramUrl or "",
        "profilePhotoUrl": profile.profilePhotoUrl or "",
        "mediaGallery": [m.model_dump() for m in (profile.mediaGallery or [])],
        "createdAt": existing["createdAt"] if existing else now,
        "updatedAt": now
    }
    
    if existing:
        await db.business_profiles.update_one({"id": profile_id}, {"$set": profile_doc})
    else:
        await db.business_profiles.insert_one(profile_doc)
    
    await db.users.update_one({"id": current_user["id"]}, {"$set": {"hasCompletedOnboarding": True}})
    
    # Get unlock credits
    credits = await get_brand_unlock_credits(current_user["id"])
    
    return BusinessProfileResponse(**profile_doc, unlockCredits=credits["availableCredits"], 
                                   unlockCreditsExpiry=credits["expiryDate"])

@business_router.get("/profile", response_model=BusinessProfileResponse)
async def get_my_business_profile(current_user: dict = Depends(get_current_user)):
    profile = await db.business_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    credits = await get_brand_unlock_credits(current_user["id"])
    return BusinessProfileResponse(**profile, unlockCredits=credits["availableCredits"],
                                   unlockCreditsExpiry=credits["expiryDate"])

@business_router.get("/unlock-credits", response_model=UnlockCreditsResponse)
async def get_unlock_credits(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only businesses have unlock credits")
    
    credits = await get_brand_unlock_credits(current_user["id"])
    return UnlockCreditsResponse(**credits)

# ============== MARKETPLACE ROUTES (GATED) ==============

@api_router.get("/creators/discover", response_model=List[CreatorDiscoveryResponse])
async def discover_creators(
    niche: Optional[str] = Query(None),
    minFollowers: Optional[int] = Query(None),
    maxFollowers: Optional[int] = Query(None),
    location: Optional[str] = Query(None),
    openToBarter: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    skip: int = Query(0),
    current_user: dict = Depends(get_current_user)
):
    """Layer 1: Discovery Mode - Free for all brands"""
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only businesses can browse creators")
    
    query = {}
    if niche and niche != 'All':
        query["niches"] = {"$in": [niche]}
    if minFollowers is not None:
        query["followersCount"] = {"$gte": minFollowers}
    if maxFollowers is not None:
        if "followersCount" in query:
            query["followersCount"]["$lte"] = maxFollowers
        else:
            query["followersCount"] = {"$lte": maxFollowers}
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if openToBarter is not None:
        query["isOpenToBarter"] = openToBarter
    
    creators = await db.creator_profiles.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    
    discovery_list = []
    for creator in creators:
        # Check if unlocked
        is_unlocked = await check_creator_unlocked(current_user["id"], creator["id"])
        
        # Get preview images (first 3, would be watermarked in production)
        preview_images = [m.get("thumbnailUrl", m.get("url", "")) 
                         for m in creator.get("mediaGallery", [])[:3]]
        
        discovery = CreatorDiscoveryResponse(
            id=creator["id"],
            displayName=get_display_name(creator.get("name", "Creator")),
            niches=creator.get("niches", []),
            city=creator.get("location", "").split(",")[0] if creator.get("location") else "",
            followersDisplay=format_followers(creator.get("followersCount", 0)),
            engagementRateDisplay=format_engagement_rate(creator.get("engagementRate", 0)),
            avgReelViewsDisplay=format_reel_views(creator.get("avgReelViews", 0)),
            rateRangeDisplay=format_rate_range(creator.get("rates", {})),
            previewImages=preview_images,
            isOpenToBarter=creator.get("isOpenToBarter", False),
            isUnlocked=is_unlocked
        )
        discovery_list.append(discovery)
    
    return discovery_list

@api_router.get("/creators/{creator_id}/unlocked", response_model=CreatorUnlockedResponse)
async def get_unlocked_creator(creator_id: str, current_user: dict = Depends(get_current_user)):
    """Layer 2: Unlocked Mode - After using unlock credit"""
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only businesses can view creators")
    
    # Check if unlocked
    is_unlocked = await check_creator_unlocked(current_user["id"], creator_id)
    if not is_unlocked:
        raise HTTPException(status_code=403, detail="You need to unlock this creator first")
    
    creator = await db.creator_profiles.find_one({"id": creator_id}, {"_id": 0})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    return CreatorUnlockedResponse(
        id=creator["id"],
        name=creator.get("name", ""),
        bio=creator.get("bio", ""),
        niches=creator.get("niches", []),
        city=creator.get("location", "").split(",")[0] if creator.get("location") else "",
        followersCount=creator.get("followersCount", 0),
        engagementRate=creator.get("engagementRate", 0),
        avgReelViews=creator.get("avgReelViews", 0),
        rates=RateInfo(**creator.get("rates", {})),
        mediaGallery=[MediaItem(**m) for m in creator.get("mediaGallery", [])],
        isOpenToBarter=creator.get("isOpenToBarter", False),
        profilePhotoUrl=creator.get("profilePhotoUrl", "")
    )

@api_router.get("/creators/{creator_id}/full", response_model=CreatorFullAccessResponse)
async def get_full_creator(creator_id: str, current_user: dict = Depends(get_current_user)):
    """Layer 3: Full Access - After escrow payment"""
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only businesses can view creators")
    
    # Check if escrow paid
    has_escrow = await check_escrow_paid(current_user["id"], creator_id)
    if not has_escrow:
        raise HTTPException(status_code=403, detail="Full access requires campaign payment")
    
    creator = await db.creator_profiles.find_one({"id": creator_id}, {"_id": 0})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    return CreatorFullAccessResponse(**creator)

@api_router.post("/creators/{creator_id}/unlock")
async def unlock_creator(creator_id: str, current_user: dict = Depends(get_current_user)):
    """Use an unlock credit to unlock a creator"""
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only businesses can unlock creators")
    
    # Check if already unlocked
    is_unlocked = await check_creator_unlocked(current_user["id"], creator_id)
    if is_unlocked:
        return {"message": "Creator already unlocked", "success": True}
    
    # Check credits
    credits = await get_brand_unlock_credits(current_user["id"])
    if credits["availableCredits"] <= 0:
        raise HTTPException(status_code=402, detail="No unlock credits available. Please purchase an unlock pack.")
    
    # Verify creator exists
    creator = await db.creator_profiles.find_one({"id": creator_id}, {"_id": 0})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    # Use credit
    await db.unlock_credits.update_one(
        {"brandId": current_user["id"]},
        {"$inc": {"usedCredits": 1}}
    )
    
    # Record unlock
    await db.creator_unlocks.insert_one({
        "id": str(uuid.uuid4()),
        "brandId": current_user["id"],
        "creatorId": creator_id,
        "unlockedAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Creator unlocked successfully!", "success": True}

# ============== PAYMENT ROUTES ==============

@payment_router.post("/create-unlock-order", response_model=PaymentOrderResponse)
async def create_unlock_order(current_user: dict = Depends(get_current_user)):
    """Create Razorpay order for unlock pack"""
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only businesses can purchase unlock packs")
    
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Payment service not configured")
    
    try:
        order = razorpay_client.order.create({
            "amount": UNLOCK_PACK_PRICE,
            "currency": "INR",
            "payment_capture": 1,
            "notes": {
                "userId": current_user["id"],
                "type": "unlock_pack"
            }
        })
        
        # Store order
        await db.payments.insert_one({
            "id": str(uuid.uuid4()),
            "orderId": order["id"],
            "userId": current_user["id"],
            "type": "unlock_pack",
            "amount": UNLOCK_PACK_PRICE,
            "status": "created",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        return PaymentOrderResponse(
            orderId=order["id"],
            amount=UNLOCK_PACK_PRICE,
            currency="INR",
            keyId=RAZORPAY_KEY_ID
        )
    except Exception as e:
        logging.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create payment order")

@payment_router.post("/verify-unlock-payment")
async def verify_unlock_payment(payment: PaymentVerifyRequest, current_user: dict = Depends(get_current_user)):
    """Verify Razorpay payment and add unlock credits"""
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Payment service not configured")
    
    try:
        # Verify signature
        params = {
            'razorpay_order_id': payment.razorpay_order_id,
            'razorpay_payment_id': payment.razorpay_payment_id,
            'razorpay_signature': payment.razorpay_signature
        }
        razorpay_client.utility.verify_payment_signature(params)
        
        # Update payment status
        await db.payments.update_one(
            {"orderId": payment.razorpay_order_id},
            {"$set": {
                "paymentId": payment.razorpay_payment_id,
                "status": "paid",
                "paidAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Add unlock credits
        expiry = datetime.now(timezone.utc) + timedelta(days=UNLOCK_CREDIT_VALIDITY_DAYS)
        
        existing_credits = await db.unlock_credits.find_one({"brandId": current_user["id"]})
        if existing_credits:
            # Add to existing credits
            await db.unlock_credits.update_one(
                {"brandId": current_user["id"]},
                {
                    "$inc": {"totalCredits": UNLOCK_PACK_CREDITS},
                    "$set": {"expiryDate": expiry.isoformat()}
                }
            )
        else:
            # Create new credits
            await db.unlock_credits.insert_one({
                "brandId": current_user["id"],
                "totalCredits": UNLOCK_PACK_CREDITS,
                "usedCredits": 0,
                "expiryDate": expiry.isoformat(),
                "createdAt": datetime.now(timezone.utc).isoformat()
            })
        
        return {"message": f"Payment successful! {UNLOCK_PACK_CREDITS} unlock credits added.", "success": True}
    
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Payment verification failed")
    except Exception as e:
        logging.error(f"Payment verification error: {e}")
        raise HTTPException(status_code=500, detail="Payment verification failed")

@payment_router.post("/create-escrow-order")
async def create_escrow_order(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Create Razorpay order for campaign escrow payment"""
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only businesses can make escrow payments")
    
    campaign = await db.campaigns.find_one({"id": campaign_id, "brandId": current_user["id"]}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.get("escrowStatus") == "paid":
        raise HTTPException(status_code=400, detail="Escrow already paid for this campaign")
    
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Payment service not configured")
    
    amount_paise = int(campaign["price"] * 100)
    
    try:
        order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,
            "notes": {
                "userId": current_user["id"],
                "campaignId": campaign_id,
                "type": "escrow"
            }
        })
        
        await db.payments.insert_one({
            "id": str(uuid.uuid4()),
            "orderId": order["id"],
            "userId": current_user["id"],
            "campaignId": campaign_id,
            "type": "escrow",
            "amount": amount_paise,
            "status": "created",
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        
        return PaymentOrderResponse(
            orderId=order["id"],
            amount=amount_paise,
            currency="INR",
            keyId=RAZORPAY_KEY_ID
        )
    except Exception as e:
        logging.error(f"Escrow order creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create payment order")

@payment_router.post("/verify-escrow-payment")
async def verify_escrow_payment(payment: PaymentVerifyRequest, campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Verify escrow payment and update campaign status"""
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Payment service not configured")
    
    try:
        params = {
            'razorpay_order_id': payment.razorpay_order_id,
            'razorpay_payment_id': payment.razorpay_payment_id,
            'razorpay_signature': payment.razorpay_signature
        }
        razorpay_client.utility.verify_payment_signature(params)
        
        # Update payment
        await db.payments.update_one(
            {"orderId": payment.razorpay_order_id},
            {"$set": {
                "paymentId": payment.razorpay_payment_id,
                "status": "paid",
                "paidAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Update campaign escrow status
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": {
                "escrowStatus": "paid",
                "campaignStatus": "in_progress",
                "escrowPaidAt": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {"message": "Escrow payment successful! Full access unlocked.", "success": True}
    
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Payment verification failed")
    except Exception as e:
        logging.error(f"Escrow verification error: {e}")
        raise HTTPException(status_code=500, detail="Payment verification failed")

# ============== CAMPAIGN ROUTES ==============

@api_router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(campaign_data: CampaignCreate, current_user: dict = Depends(get_current_user)):
    """Create a new campaign (proposal)"""
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only businesses can create campaigns")
    
    # Check if creator is unlocked
    is_unlocked = await check_creator_unlocked(current_user["id"], campaign_data.creatorId)
    if not is_unlocked:
        raise HTTPException(status_code=403, detail="You need to unlock this creator first")
    
    creator = await db.creator_profiles.find_one({"id": campaign_data.creatorId}, {"_id": 0})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    business = await db.business_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
    
    now = datetime.now(timezone.utc).isoformat()
    campaign_id = str(uuid.uuid4())
    
    campaign_doc = {
        "id": campaign_id,
        "brandId": current_user["id"],
        "creatorId": campaign_data.creatorId,
        "title": campaign_data.title,
        "brief": campaign_data.brief,
        "deliverables": campaign_data.deliverables,
        "timeline": campaign_data.timeline,
        "price": campaign_data.price,
        "isBarter": campaign_data.isBarter,
        "barterDetails": campaign_data.barterDetails or "",
        "escrowStatus": "pending",
        "campaignStatus": "proposed",
        "createdAt": now,
        "updatedAt": now
    }
    
    await db.campaigns.insert_one(campaign_doc)
    
    return CampaignResponse(
        **campaign_doc,
        creatorName=creator.get("name", ""),
        brandName=business.get("brandName", "") if business else ""
    )

@api_router.get("/campaigns/sent", response_model=List[CampaignResponse])
async def get_sent_campaigns(current_user: dict = Depends(get_current_user)):
    """Get campaigns sent by brand"""
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only businesses can view sent campaigns")
    
    campaigns = await db.campaigns.find({"brandId": current_user["id"]}, {"_id": 0}).to_list(100)
    
    for campaign in campaigns:
        creator = await db.creator_profiles.find_one({"id": campaign["creatorId"]}, {"_id": 0})
        business = await db.business_profiles.find_one({"userId": campaign["brandId"]}, {"_id": 0})
        if creator:
            campaign["creatorName"] = creator.get("name", "")
            # Only show Instagram after escrow paid
            if campaign.get("escrowStatus") in ["paid", "released"]:
                campaign["instagramHandle"] = creator.get("instagramHandle")
                campaign["instagramUrl"] = creator.get("instagramUrl")
        if business:
            campaign["brandName"] = business.get("brandName", "")
    
    return [CampaignResponse(**c) for c in campaigns]

@api_router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Get campaign details"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check access
    creator = await db.creator_profiles.find_one({"id": campaign["creatorId"]}, {"_id": 0})
    if campaign["brandId"] != current_user["id"] and (not creator or creator["userId"] != current_user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    business = await db.business_profiles.find_one({"userId": campaign["brandId"]}, {"_id": 0})
    if creator:
        campaign["creatorName"] = creator.get("name", "")
        if campaign.get("escrowStatus") in ["paid", "released"]:
            campaign["instagramHandle"] = creator.get("instagramHandle")
            campaign["instagramUrl"] = creator.get("instagramUrl")
    if business:
        campaign["brandName"] = business.get("brandName", "")
    
    return CampaignResponse(**campaign)

@api_router.patch("/campaigns/{campaign_id}/status")
async def update_campaign_status(campaign_id: str, status: str = Query(...), current_user: dict = Depends(get_current_user)):
    """Update campaign status (accept/decline by creator, or mark delivered/completed)"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    valid_statuses = ["accepted", "declined", "in_progress", "delivered", "completed", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    # Check permissions
    creator = await db.creator_profiles.find_one({"id": campaign["creatorId"]}, {"_id": 0})
    is_creator = creator and creator["userId"] == current_user["id"]
    is_brand = campaign["brandId"] == current_user["id"]
    
    # Creator can: accept, decline, mark delivered
    # Brand can: mark completed (releases escrow), cancel
    if status in ["accepted", "declined", "delivered"] and not is_creator:
        raise HTTPException(status_code=403, detail="Only creator can perform this action")
    if status in ["completed", "cancelled"] and not is_brand:
        raise HTTPException(status_code=403, detail="Only brand can perform this action")
    
    update_data = {"campaignStatus": status, "updatedAt": datetime.now(timezone.utc).isoformat()}
    
    # If completed, release escrow
    if status == "completed" and campaign.get("escrowStatus") == "paid":
        update_data["escrowStatus"] = "released"
        update_data["escrowReleasedAt"] = datetime.now(timezone.utc).isoformat()
    
    await db.campaigns.update_one({"id": campaign_id}, {"$set": update_data})
    
    return {"message": f"Campaign status updated to {status}", "success": True}

# ============== MESSAGE ROUTES (WITH ANTI-BYPASS) ==============

@message_router.get("/{campaign_id}", response_model=List[MessageResponse])
async def get_messages(campaign_id: str, current_user: dict = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    creator = await db.creator_profiles.find_one({"id": campaign["creatorId"]}, {"_id": 0})
    if campaign["brandId"] != current_user["id"] and (not creator or creator["userId"] != current_user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = await db.messages.find({"requestId": campaign_id}, {"_id": 0}).sort("createdAt", 1).to_list(500)
    return [MessageResponse(**msg) for msg in messages]

@message_router.post("/{campaign_id}", response_model=MessageResponse)
async def send_message(campaign_id: str, msg_data: MessageCreate, current_user: dict = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    creator = await db.creator_profiles.find_one({"id": campaign["creatorId"]}, {"_id": 0})
    if campaign["brandId"] != current_user["id"] and (not creator or creator["userId"] != current_user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check for bypass attempts BEFORE escrow
    is_blocked = False
    block_reason = None
    
    if campaign.get("escrowStatus") != "paid" and campaign.get("escrowStatus") != "released":
        is_blocked, block_reason = check_message_for_bypass(msg_data.text)
        
        if is_blocked:
            # Log bypass attempt
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
    if current_user["role"] == "creator" and creator:
        sender_name = creator.get("name", current_user["email"])
    elif current_user["role"] == "business":
        business = await db.business_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
        if business:
            sender_name = business.get("brandName", current_user["email"])
    
    message_doc = {
        "id": str(uuid.uuid4()),
        "requestId": campaign_id,
        "senderUserId": current_user["id"],
        "senderName": sender_name,
        "text": msg_data.text if not is_blocked else "[Message blocked - external contact sharing not allowed before payment]",
        "isBlocked": is_blocked,
        "blockReason": block_reason,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.messages.insert_one(message_doc)
    
    # Add warning message if blocked
    if is_blocked:
        warning_doc = {
            "id": str(uuid.uuid4()),
            "requestId": campaign_id,
            "senderUserId": "system",
            "senderName": "🍊 Orange",
            "text": "⚠️ Please keep communication inside Orange for safety. External contact sharing is enabled after campaign payment.",
            "isBlocked": False,
            "blockReason": None,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        await db.messages.insert_one(warning_doc)
    
    return MessageResponse(**message_doc)

# ============== ADMIN ROUTES ==============

@admin_router.get("/stats", response_model=AdminStats)
async def get_admin_stats(admin: dict = Depends(get_admin_user)):
    """Get admin dashboard stats"""
    total_users = await db.users.count_documents({})
    total_creators = await db.creator_profiles.count_documents({})
    total_brands = await db.business_profiles.count_documents({})
    total_campaigns = await db.campaigns.count_documents({})
    bypass_attempts = await db.bypass_attempts.count_documents({})
    active_unlocks = await db.unlock_credits.count_documents({"usedCredits": {"$lt": "$totalCredits"}})
    
    # Calculate revenue from paid payments
    payments = await db.payments.find({"status": "paid"}, {"_id": 0, "amount": 1}).to_list(1000)
    total_revenue = sum(p.get("amount", 0) for p in payments) / 100  # Convert paise to rupees
    
    return AdminStats(
        totalUsers=total_users,
        totalCreators=total_creators,
        totalBrands=total_brands,
        totalCampaigns=total_campaigns,
        totalRevenue=total_revenue,
        bypassAttempts=bypass_attempts,
        activeUnlocks=active_unlocks
    )

@admin_router.get("/bypass-attempts", response_model=List[FlaggedChat])
async def get_bypass_attempts(limit: int = 50, admin: dict = Depends(get_admin_user)):
    """Get flagged chat messages"""
    attempts = await db.bypass_attempts.find({}, {"_id": 0}).sort("createdAt", -1).limit(limit).to_list(limit)
    
    result = []
    for attempt in attempts:
        user = await db.users.find_one({"id": attempt["userId"]}, {"_id": 0, "email": 1})
        result.append(FlaggedChat(
            id=attempt["id"],
            campaignId=attempt["campaignId"],
            senderName=user.get("email", "Unknown") if user else "Unknown",
            message=attempt["message"],
            reason=attempt["reason"],
            createdAt=attempt["createdAt"]
        ))
    
    return result

@admin_router.post("/users/{user_id}/ban")
async def ban_user(user_id: str, admin: dict = Depends(get_admin_user)):
    """Ban a user"""
    result = await db.users.update_one({"id": user_id}, {"$set": {"isBanned": True}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User banned successfully"}

@admin_router.post("/users/{user_id}/unban")
async def unban_user(user_id: str, admin: dict = Depends(get_admin_user)):
    """Unban a user"""
    result = await db.users.update_one({"id": user_id}, {"$set": {"isBanned": False}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User unbanned successfully"}

@admin_router.delete("/unlock-credits/{brand_id}")
async def revoke_unlock_credits(brand_id: str, admin: dict = Depends(get_admin_user)):
    """Revoke a brand's unlock credits"""
    result = await db.unlock_credits.delete_one({"brandId": brand_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No credits found for this brand")
    return {"message": "Unlock credits revoked"}

# ============== LEGACY ROUTES (For compatibility) ==============

@api_router.get("/creators", response_model=List[CreatorDiscoveryResponse])
async def get_creators_legacy(
    niche: Optional[str] = Query(None),
    minFollowers: Optional[int] = Query(None),
    maxFollowers: Optional[int] = Query(None),
    location: Optional[str] = Query(None),
    openToBarter: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    skip: int = Query(0),
    current_user: dict = Depends(get_current_user)
):
    """Redirect to discover endpoint"""
    return await discover_creators(niche, minFollowers, maxFollowers, location, openToBarter, limit, skip, current_user)

# ============== SEED DATA ==============

@api_router.post("/seed")
async def seed_data():
    """Seed database with sample data"""
    # Clear existing data
    await db.users.delete_many({})
    await db.creator_profiles.delete_many({})
    await db.business_profiles.delete_many({})
    await db.campaigns.delete_many({})
    await db.messages.delete_many({})
    await db.unlock_credits.delete_many({})
    await db.creator_unlocks.delete_many({})
    await db.payments.delete_many({})
    await db.bypass_attempts.delete_many({})
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create admin user
    admin_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": admin_id,
        "email": "admin@orange.com",
        "passwordHash": get_password_hash("admin123"),
        "role": "business",
        "hasCompletedOnboarding": True,
        "isAdmin": True,
        "createdAt": now
    })
    
    # Create sample creators
    creators_data = [
        {
            "name": "Priya Sharma",
            "bio": "Fashion & lifestyle creator ✨ Making everyday looks pop! 500K+ community of style lovers.",
            "location": "Mumbai, India",
            "instagramHandle": "@priyasharma",
            "instagramUrl": "https://instagram.com/priyasharma",
            "followersCount": 520000,
            "engagementRate": 5.8,
            "avgReelViews": 45000,
            "niches": ["Fashion", "Lifestyle"],
            "isOpenToBarter": True,
            "rates": {"reelPrice": 15000, "storyPrice": 5000, "postPrice": 10000, "bundlePrice": 25000},
            "profilePhotoUrl": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400"
        },
        {
            "name": "Arjun Kapoor",
            "bio": "Fitness enthusiast & sports content creator 💪 Transforming bodies and minds.",
            "location": "Delhi, India",
            "instagramHandle": "@arjunfitness",
            "instagramUrl": "https://instagram.com/arjunfitness",
            "followersCount": 280000,
            "engagementRate": 4.2,
            "avgReelViews": 28000,
            "niches": ["Fitness", "Sports"],
            "isOpenToBarter": False,
            "rates": {"reelPrice": 12000, "storyPrice": 4000, "postPrice": 8000, "bundlePrice": 20000},
            "profilePhotoUrl": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400"
        },
        {
            "name": "Meera Patel",
            "bio": "Beauty guru & skincare addict 💄 Honest reviews and glam tutorials.",
            "location": "Bangalore, India",
            "instagramHandle": "@meerabellebeauty",
            "instagramUrl": "https://instagram.com/meerabellebeauty",
            "followersCount": 150000,
            "engagementRate": 6.5,
            "avgReelViews": 18000,
            "niches": ["Beauty", "Skincare"],
            "isOpenToBarter": True,
            "rates": {"reelPrice": 8000, "storyPrice": 3000, "postPrice": 6000, "bundlePrice": 15000},
            "profilePhotoUrl": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400"
        },
        {
            "name": "Rohan Desai",
            "bio": "Tech reviewer & gadget geek 📱 Unboxing the future, one device at a time.",
            "location": "Pune, India",
            "instagramHandle": "@rohantech",
            "instagramUrl": "https://instagram.com/rohantech",
            "followersCount": 95000,
            "engagementRate": 7.2,
            "avgReelViews": 12000,
            "niches": ["Tech", "Gaming"],
            "isOpenToBarter": False,
            "rates": {"reelPrice": 10000, "storyPrice": 3500, "postPrice": 7000, "bundlePrice": 18000},
            "profilePhotoUrl": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400"
        },
        {
            "name": "Ananya Iyer",
            "bio": "Food blogger & culinary explorer 🍜 From street food to fine dining.",
            "location": "Chennai, India",
            "instagramHandle": "@ananyaeats",
            "instagramUrl": "https://instagram.com/ananyaeats",
            "followersCount": 320000,
            "engagementRate": 5.1,
            "avgReelViews": 35000,
            "niches": ["Food", "Travel"],
            "isOpenToBarter": True,
            "rates": {"reelPrice": 14000, "storyPrice": 4500, "postPrice": 9000, "bundlePrice": 22000},
            "profilePhotoUrl": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400"
        }
    ]
    
    creator_profiles = []
    for i, creator in enumerate(creators_data):
        user_id = str(uuid.uuid4())
        profile_id = str(uuid.uuid4())
        
        await db.users.insert_one({
            "id": user_id,
            "email": f"creator{i+1}@orange.com",
            "passwordHash": get_password_hash("password123"),
            "role": "creator",
            "hasCompletedOnboarding": True,
            "isAdmin": False,
            "createdAt": now
        })
        
        profile_doc = {
            "id": profile_id,
            "userId": user_id,
            **creator,
            "mediaGallery": [],
            "createdAt": now,
            "updatedAt": now
        }
        await db.creator_profiles.insert_one(profile_doc)
        creator_profiles.append(profile_doc)
    
    # Create sample businesses
    businesses_data = [
        {
            "brandName": "Glow Cosmetics",
            "category": "Beauty",
            "bio": "Clean beauty for the modern generation ✨",
            "location": "Mumbai, India",
            "websiteUrl": "https://glowcosmetics.com",
            "instagramHandle": "@glowcosmetics",
            "instagramUrl": "https://instagram.com/glowcosmetics",
            "profilePhotoUrl": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400"
        },
        {
            "brandName": "FitLife Nutrition",
            "category": "Health & Fitness",
            "bio": "Fueling your fitness journey with premium supplements 💪",
            "location": "Delhi, India",
            "websiteUrl": "https://fitlifenutrition.com",
            "instagramHandle": "@fitlifenutrition",
            "instagramUrl": "https://instagram.com/fitlifenutrition",
            "profilePhotoUrl": "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=400"
        }
    ]
    
    business_users = []
    for i, business in enumerate(businesses_data):
        user_id = str(uuid.uuid4())
        profile_id = str(uuid.uuid4())
        
        await db.users.insert_one({
            "id": user_id,
            "email": f"business{i+1}@orange.com",
            "passwordHash": get_password_hash("password123"),
            "role": "business",
            "hasCompletedOnboarding": True,
            "isAdmin": False,
            "createdAt": now
        })
        
        await db.business_profiles.insert_one({
            "id": profile_id,
            "userId": user_id,
            **business,
            "mediaGallery": [],
            "createdAt": now,
            "updatedAt": now
        })
        business_users.append({"userId": user_id, "profileId": profile_id})
        
        # Give first business some unlock credits for testing
        if i == 0:
            expiry = datetime.now(timezone.utc) + timedelta(days=7)
            await db.unlock_credits.insert_one({
                "brandId": user_id,
                "totalCredits": 5,
                "usedCredits": 0,
                "expiryDate": expiry.isoformat(),
                "createdAt": now
            })
    
    return {
        "message": "Seed data created successfully",
        "creators": len(creators_data),
        "businesses": len(businesses_data),
        "admin": "admin@orange.com / admin123"
    }

# ============== ROOT ROUTES ==============

@api_router.get("/")
async def root():
    return {"message": "Welcome to Orange - Creator Marketplace API 🍊"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "service": "orange-marketplace"}

# Include all routers
api_router.include_router(auth_router)
api_router.include_router(creator_router)
api_router.include_router(business_router)
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
