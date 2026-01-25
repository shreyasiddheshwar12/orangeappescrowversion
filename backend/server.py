from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, status
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

# Platform Configuration
PLATFORM_COMMISSION_PERCENT = 10  # 10% commission on paid collabs
BARTER_FEE_PERCENT = 10  # 10% of declared product/service value for barter
CREATOR_SUBSCRIPTION_FEE = 5000  # ₹50/month in paise (MOCKED for MVP)
AUTO_APPROVE_DAYS = 7  # Auto-approve content after 7 days
REQUEST_EXPIRY_HOURS = 72

# Collaboration States
COLLAB_STATES = [
    "requested",      # Initial request sent
    "accepted",       # Receiver accepted
    "payment_pending", # Waiting for payment (escrow or barter fee)
    "paid",           # Payment received, identities revealed
    "in_progress",    # Work being done
    "link_submitted", # Creator submitted reel/story link
    "link_verified",  # Brand verified the link
    "completed",      # Fully completed with ratings
    "disputed",       # Issue reported
    "cancelled"       # Cancelled by either party
]

# Create the main app
app = FastAPI(title="Orange - Creator-Brand Collaboration Platform API")

# Create routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
creator_router = APIRouter(prefix="/creator", tags=["Creator"])
business_router = APIRouter(prefix="/business", tags=["Business"])
marketplace_router = APIRouter(prefix="/marketplace", tags=["Marketplace"])
campaign_router = APIRouter(prefix="/campaigns", tags=["Campaigns"])
message_router = APIRouter(prefix="/messages", tags=["Messages"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])

security = HTTPBearer()

# ============== BLOCKED KEYWORDS FOR CHAT ==============
BLOCKED_PATTERNS = [
    r'\b(instagram|insta|ig)\b',
    r'\b(whatsapp|wa)\b',
    r'\b(telegram|tg)\b',
    r'@[a-zA-Z0-9_]+',
    r'\b\d{10}\b',
    r'\b(snapchat|snap)\b',
    r'\b(twitter|x\.com)\b',
    r'\b(facebook|fb)\b',
    r'\b(linkedin)\b',
    r'\b(email|mail)\b.*@',
]

# ============== LOGGING ==============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============== PYDANTIC MODELS ==============

# Auth Models
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
    isBlacklisted: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Creator Models
class CreatorProfileCreate(BaseModel):
    name: str
    bio: Optional[str] = ""
    location: Optional[str] = ""
    niche: Optional[str] = ""
    language: Optional[str] = "English"
    contentType: Optional[str] = ""  # Reels, Stories, Posts
    niches: Optional[List[str]] = []
    reelPrice: Optional[float] = 0
    storyPrice: Optional[float] = 0
    postPrice: Optional[float] = 0
    paidCollabsEnabled: Optional[bool] = True
    barterEnabled: Optional[bool] = True
    profilePhotoUrl: Optional[str] = ""

class CreatorProfileFull(BaseModel):
    id: str
    userId: str
    name: str
    bio: str
    location: str
    niche: str
    language: str
    contentType: str
    niches: List[str]
    reelPrice: float
    storyPrice: float
    postPrice: float
    paidCollabsEnabled: bool
    barterEnabled: bool
    instagramVerified: bool
    engagementRate: float
    profilePhotoUrl: str
    isBlacklisted: bool = False
    isVisible: bool = True  # Subscription-based visibility (MOCKED for MVP)
    subscriptionActive: bool = True  # For ₹50/month visibility subscription
    rating: Optional[float] = None
    totalCollabs: int = 0

# Brand Models
class BrandProfileCreate(BaseModel):
    brandName: str
    industry: Optional[str] = ""
    bio: Optional[str] = ""
    location: Optional[str] = ""
    deliverables: Optional[str] = ""  # What they typically need
    budgetRange: Optional[str] = ""
    barterEnabled: Optional[bool] = True
    paidCollabsEnabled: Optional[bool] = True
    brandRequirements: Optional[str] = ""
    profilePhotoUrl: Optional[str] = ""

class BrandProfileFull(BaseModel):
    id: str
    userId: str
    brandName: str
    industry: str
    bio: str
    location: str
    deliverables: str
    budgetRange: str
    barterEnabled: bool
    paidCollabsEnabled: bool
    brandRequirements: str
    instagramVerified: bool
    profilePhotoUrl: str

# Discovery Models (Partial - No Identity)
class CreatorDiscovery(BaseModel):
    id: str
    niche: str
    language: str
    contentType: str
    niches: List[str]
    reelPrice: float
    storyPrice: float
    postPrice: float
    engagementRate: float
    paidCollabsEnabled: bool
    barterEnabled: bool
    location: str
    # NO: name, instagramHandle, profilePhotoUrl

class BrandDiscovery(BaseModel):
    id: str
    industry: str
    location: str
    deliverables: str
    budgetRange: str
    barterEnabled: bool
    paidCollabsEnabled: bool
    brandRequirements: str
    # NO: brandName, instagramHandle

# Campaign Models
class CampaignCreate(BaseModel):
    receiverId: str  # Creator or Brand profile ID
    receiverType: Literal["creator", "brand"]
    campaignType: Literal["paid", "barter_product", "barter_service"]
    deliverables: str
    budget: Optional[float] = 0  # For paid collabs
    productValue: Optional[float] = 0  # For barter - declared product/service value
    timeline: Optional[str] = ""
    brief: Optional[str] = ""
    barterDetails: Optional[str] = ""  # Product/service description for barter

class CampaignResponse(BaseModel):
    id: str
    senderId: str
    senderType: str
    senderName: str  # Hidden until payment
    receiverId: str
    receiverType: str
    receiverName: str  # Hidden until payment
    campaignType: str  # paid, barter_product, barter_service
    deliverables: str
    budget: float
    productValue: float  # For barter
    barterFee: float  # 10% of productValue
    timeline: str
    brief: str
    barterDetails: str
    status: str  # requested, accepted, payment_pending, paid, in_progress, link_submitted, link_verified, completed, disputed, cancelled
    paymentStatus: str  # pending, paid
    escrowAmount: float
    platformCommission: float
    creatorPayout: float
    identityUnlocked: bool
    chatEnabled: bool
    contentLink: Optional[str] = None
    linkVerified: bool = False
    shippingDetails: Optional[str] = None
    productReceived: bool = False
    # Instagram handles - only shown after unlock
    senderInstagram: Optional[str] = None
    receiverInstagram: Optional[str] = None
    createdAt: str
    updatedAt: str
    expiresAt: Optional[str] = None

# Rating Models
class RatingCreate(BaseModel):
    campaignId: str
    rating: int  # 1-5 stars
    feedback: str  # Mandatory feedback

class RatingResponse(BaseModel):
    id: str
    campaignId: str
    raterId: str
    raterType: str
    targetId: str
    targetType: str
    rating: int
    feedback: str
    createdAt: str

# Message Models
class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: str
    campaignId: str
    senderId: str
    senderType: str
    content: str
    blocked: bool = False
    createdAt: str

# Instagram Verification (Simulated)
class InstagramVerifyRequest(BaseModel):
    instagramUsername: str

class InstagramVerifyResponse(BaseModel):
    success: bool
    instagramUserId: str
    engagementRate: float
    message: str

# ============== HELPER FUNCTIONS ==============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
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
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Check if blacklisted
        if user.get("isBlacklisted", False):
            raise HTTPException(status_code=403, detail="Your account has been blacklisted")
        
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def check_blocked_content(message: str) -> bool:
    """Check if message contains blocked patterns (external contact info)"""
    message_lower = message.lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return True
    return False

def generate_simulated_engagement_rate() -> float:
    """Generate a realistic engagement rate between 2% and 12%"""
    return round(random.uniform(2.0, 12.0), 2)

# ============== AUTH ENDPOINTS ==============

@auth_router.post("/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "passwordHash": hash_password(user_data.password),
        "role": user_data.role,
        "hasCompletedOnboarding": False,
        "isAdmin": False,
        "instagramVerified": False,
        "isBlacklisted": False,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    token = create_access_token({"sub": user_id, "email": user_data.email, "role": user_data.role})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user_data.email,
            role=user_data.role,
            hasCompletedOnboarding=False,
            isAdmin=False,
            instagramVerified=False,
            isBlacklisted=False
        )
    )

@auth_router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if not user or not verify_password(user_data.password, user["passwordHash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user.get("isBlacklisted", False):
        raise HTTPException(status_code=403, detail="Your account has been blacklisted")
    
    token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            role=user["role"],
            hasCompletedOnboarding=user.get("hasCompletedOnboarding", False),
            isAdmin=user.get("isAdmin", False),
            instagramVerified=user.get("instagramVerified", False),
            isBlacklisted=user.get("isBlacklisted", False)
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
        instagramVerified=current_user.get("instagramVerified", False),
        isBlacklisted=current_user.get("isBlacklisted", False)
    )

@auth_router.post("/logout")
async def logout():
    return {"message": "Logged out successfully", "success": True}

# ============== INSTAGRAM VERIFICATION (SIMULATED) ==============

@auth_router.post("/instagram/verify", response_model=InstagramVerifyResponse)
async def verify_instagram(
    request: InstagramVerifyRequest,
    current_user: dict = Depends(get_current_user)
):
    """Simulated Instagram OAuth verification for MVP"""
    username = request.instagramUsername.replace("@", "").strip()
    
    if not username:
        raise HTTPException(status_code=400, detail="Instagram username is required")
    
    # Simulate Instagram API response
    simulated_user_id = f"ig_{uuid.uuid4().hex[:12]}"
    engagement_rate = generate_simulated_engagement_rate()
    
    # Update user record
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {
            "instagramVerified": True,
            "instagramUserId": simulated_user_id,
            "instagramUsername": username,
            "engagementRate": engagement_rate
        }}
    )
    
    # Update profile if exists
    collection = "creator_profiles" if current_user["role"] == "creator" else "brand_profiles"
    await db[collection].update_one(
        {"userId": current_user["id"]},
        {"$set": {
            "instagramVerified": True,
            "instagramUserId": simulated_user_id,
            "instagramUsername": username,
            "engagementRate": engagement_rate
        }}
    )
    
    return InstagramVerifyResponse(
        success=True,
        instagramUserId=simulated_user_id,
        engagementRate=engagement_rate,
        message="Instagram verified successfully! (Demo Mode)"
    )

# ============== CREATOR PROFILE ENDPOINTS ==============

@creator_router.post("/profile", response_model=CreatorProfileFull)
async def create_creator_profile(profile: CreatorProfileCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "creator":
        raise HTTPException(status_code=403, detail="Only creators can create creator profiles")
    
    existing = await db.creator_profiles.find_one({"userId": current_user["id"]})
    now = datetime.now(timezone.utc).isoformat()
    profile_id = existing["id"] if existing else str(uuid.uuid4())
    
    # Get Instagram data from user record
    instagram_verified = current_user.get("instagramVerified", False)
    engagement_rate = current_user.get("engagementRate", generate_simulated_engagement_rate())
    
    profile_doc = {
        "id": profile_id,
        "userId": current_user["id"],
        "name": profile.name,
        "bio": profile.bio or "",
        "location": profile.location or "",
        "niche": profile.niche or (profile.niches[0] if profile.niches else ""),
        "language": profile.language or "English",
        "contentType": profile.contentType or "",
        "niches": profile.niches or [],
        "reelPrice": profile.reelPrice or 0,
        "storyPrice": profile.storyPrice or 0,
        "postPrice": profile.postPrice or 0,
        "paidCollabsEnabled": profile.paidCollabsEnabled if profile.paidCollabsEnabled is not None else True,
        "barterEnabled": profile.barterEnabled if profile.barterEnabled is not None else True,
        "instagramVerified": instagram_verified,
        "instagramUserId": current_user.get("instagramUserId"),
        "instagramUsername": current_user.get("instagramUsername"),
        "engagementRate": engagement_rate,
        "profilePhotoUrl": profile.profilePhotoUrl or "",
        "isBlacklisted": False,
        "createdAt": existing["createdAt"] if existing else now,
        "updatedAt": now
    }
    
    if existing:
        await db.creator_profiles.update_one({"id": profile_id}, {"$set": profile_doc})
    else:
        await db.creator_profiles.insert_one(profile_doc)
    
    await db.users.update_one({"id": current_user["id"]}, {"$set": {"hasCompletedOnboarding": True}})
    
    return CreatorProfileFull(**{k: v for k, v in profile_doc.items() if k != "_id"})

@creator_router.get("/profile", response_model=CreatorProfileFull)
async def get_creator_profile(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "creator":
        raise HTTPException(status_code=403, detail="Only creators can access this")
    
    profile = await db.creator_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Complete onboarding first.")
    
    return CreatorProfileFull(**profile)

# ============== BRAND PROFILE ENDPOINTS ==============

@business_router.post("/profile", response_model=BrandProfileFull)
async def create_brand_profile(profile: BrandProfileCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only brands can create brand profiles")
    
    existing = await db.brand_profiles.find_one({"userId": current_user["id"]})
    now = datetime.now(timezone.utc).isoformat()
    profile_id = existing["id"] if existing else str(uuid.uuid4())
    
    instagram_verified = current_user.get("instagramVerified", False)
    
    profile_doc = {
        "id": profile_id,
        "userId": current_user["id"],
        "brandName": profile.brandName,
        "industry": profile.industry or "",
        "bio": profile.bio or "",
        "location": profile.location or "",
        "deliverables": profile.deliverables or "",
        "budgetRange": profile.budgetRange or "",
        "barterEnabled": profile.barterEnabled if profile.barterEnabled is not None else True,
        "paidCollabsEnabled": profile.paidCollabsEnabled if profile.paidCollabsEnabled is not None else True,
        "brandRequirements": profile.brandRequirements or "",
        "instagramVerified": instagram_verified,
        "instagramUserId": current_user.get("instagramUserId"),
        "instagramUsername": current_user.get("instagramUsername"),
        "profilePhotoUrl": profile.profilePhotoUrl or "",
        "createdAt": existing["createdAt"] if existing else now,
        "updatedAt": now
    }
    
    if existing:
        await db.brand_profiles.update_one({"id": profile_id}, {"$set": profile_doc})
    else:
        await db.brand_profiles.insert_one(profile_doc)
    
    await db.users.update_one({"id": current_user["id"]}, {"$set": {"hasCompletedOnboarding": True}})
    
    return BrandProfileFull(**{k: v for k, v in profile_doc.items() if k != "_id"})

@business_router.get("/profile", response_model=BrandProfileFull)
async def get_brand_profile(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only brands can access this")
    
    profile = await db.brand_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Complete onboarding first.")
    
    return BrandProfileFull(**profile)

# ============== FREE MARKETPLACE DISCOVERY ==============

@marketplace_router.get("/creators", response_model=List[CreatorDiscovery])
async def discover_creators(
    niche: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    contentType: Optional[str] = Query(None),
    minPrice: Optional[float] = Query(None),
    maxPrice: Optional[float] = Query(None),
    barterOnly: Optional[bool] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    FREE discovery of creators - shows PARTIAL info only.
    No identity (name, Instagram) revealed until payment.
    Only shows creators with active subscription (isVisible=True).
    """
    # Build query - only show verified, non-blacklisted, VISIBLE creators
    query = {
        "instagramVerified": True,
        "isBlacklisted": {"$ne": True},
        "isVisible": {"$ne": False}  # Must be visible (subscription active)
    }
    
    if niche:
        query["$or"] = [{"niche": niche}, {"niches": niche}]
    if language:
        query["language"] = language
    if contentType:
        query["contentType"] = contentType
    if barterOnly:
        query["barterEnabled"] = True
    
    creators = await db.creator_profiles.find(query, {"_id": 0}).to_list(100)
    
    # Filter by price if specified
    if minPrice is not None:
        creators = [c for c in creators if c.get("reelPrice", 0) >= minPrice]
    if maxPrice is not None:
        creators = [c for c in creators if c.get("reelPrice", 0) <= maxPrice]
    
    # Return PARTIAL data only - no identity (name, instagram NEVER shown here)
    discovery_list = []
    for c in creators:
        discovery_list.append(CreatorDiscovery(
            id=c["id"],
            niche=c.get("niche", ""),
            language=c.get("language", "English"),
            contentType=c.get("contentType", ""),
            niches=c.get("niches", []),
            reelPrice=c.get("reelPrice", 0),
            storyPrice=c.get("storyPrice", 0),
            postPrice=c.get("postPrice", 0),
            engagementRate=c.get("engagementRate", 0),
            paidCollabsEnabled=c.get("paidCollabsEnabled", True),
            barterEnabled=c.get("barterEnabled", True),
            location=c.get("location", "")
        ))
    
    return discovery_list

@marketplace_router.get("/brands", response_model=List[BrandDiscovery])
async def discover_brands(
    industry: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    barterOnly: Optional[bool] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    FREE discovery of brands - shows PARTIAL info only.
    No identity (brand name, Instagram) revealed until payment.
    """
    query = {"instagramVerified": True}
    
    if industry:
        query["industry"] = industry
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if barterOnly:
        query["barterEnabled"] = True
    
    brands = await db.brand_profiles.find(query, {"_id": 0}).to_list(100)
    
    discovery_list = []
    for b in brands:
        discovery_list.append(BrandDiscovery(
            id=b["id"],
            industry=b.get("industry", ""),
            location=b.get("location", ""),
            deliverables=b.get("deliverables", ""),
            budgetRange=b.get("budgetRange", ""),
            barterEnabled=b.get("barterEnabled", True),
            paidCollabsEnabled=b.get("paidCollabsEnabled", True),
            brandRequirements=b.get("brandRequirements", "")
        ))
    
    return discovery_list

# ============== CAMPAIGN FLOW ==============

@campaign_router.post("/", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    campaign: CampaignCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Send a campaign request to a creator or brand.
    This is the START of the collaboration flow.
    """
    now = datetime.now(timezone.utc)
    campaign_id = str(uuid.uuid4())
    
    # Determine sender info
    sender_type = current_user["role"]
    sender_collection = "brand_profiles" if sender_type == "business" else "creator_profiles"
    sender_profile = await db[sender_collection].find_one({"userId": current_user["id"]}, {"_id": 0})
    
    if not sender_profile:
        raise HTTPException(status_code=400, detail="Complete your profile first")
    
    sender_name = sender_profile.get("brandName") if sender_type == "business" else sender_profile.get("name")
    
    # Get receiver info
    receiver_collection = "creator_profiles" if campaign.receiverType == "creator" else "brand_profiles"
    receiver_profile = await db[receiver_collection].find_one({"id": campaign.receiverId}, {"_id": 0})
    
    if not receiver_profile:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    if receiver_profile.get("isBlacklisted"):
        raise HTTPException(status_code=400, detail="This creator is no longer available")
    
    receiver_name = receiver_profile.get("name") if campaign.receiverType == "creator" else receiver_profile.get("brandName")
    receiver_user_id = receiver_profile.get("userId")
    
    # Calculate amounts for paid collabs
    escrow_amount = 0
    platform_commission = 0
    creator_payout = 0
    
    if campaign.campaignType == "paid" and campaign.budget > 0:
        escrow_amount = campaign.budget
        platform_commission = round(escrow_amount * (PLATFORM_COMMISSION_PERCENT / 100), 2)
        creator_payout = escrow_amount - platform_commission
    
    campaign_doc = {
        "id": campaign_id,
        "senderId": sender_profile["id"],
        "senderUserId": current_user["id"],
        "senderType": sender_type,
        "senderName": sender_name,
        "receiverId": campaign.receiverId,
        "receiverUserId": receiver_user_id,
        "receiverType": campaign.receiverType,
        "receiverName": receiver_name,
        "campaignType": campaign.campaignType,
        "deliverables": campaign.deliverables,
        "budget": campaign.budget or 0,
        "timeline": campaign.timeline or "",
        "brief": campaign.brief or "",
        "barterDetails": campaign.barterDetails or "",
        "status": "pending",  # pending -> accepted -> awaiting_payment -> active -> content_submitted -> completed
        "paymentStatus": "pending",
        "escrowAmount": escrow_amount,
        "platformCommission": platform_commission,
        "creatorPayout": creator_payout,
        "identityUnlocked": False,
        "chatEnabled": False,
        "contentLink": None,
        "shippingDetails": None,
        "productReceived": False,
        "createdAt": now.isoformat(),
        "updatedAt": now.isoformat(),
        "expiresAt": (now + timedelta(hours=REQUEST_EXPIRY_HOURS)).isoformat()
    }
    
    await db.campaigns.insert_one(campaign_doc)
    
    return CampaignResponse(**{k: v for k, v in campaign_doc.items() if k != "_id"})

@campaign_router.get("/incoming", response_model=List[CampaignResponse])
async def get_incoming_campaigns(current_user: dict = Depends(get_current_user)):
    """Get campaigns where current user is the receiver"""
    campaigns = await db.campaigns.find(
        {"receiverUserId": current_user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(100)
    
    # Mask identity for campaigns where payment not made
    result = []
    for c in campaigns:
        if not c.get("identityUnlocked", False):
            c["senderName"] = "Brand" if c["senderType"] == "business" else "Creator"
        result.append(CampaignResponse(**c))
    
    return result

@campaign_router.get("/outgoing", response_model=List[CampaignResponse])
async def get_outgoing_campaigns(current_user: dict = Depends(get_current_user)):
    """Get campaigns sent by current user"""
    campaigns = await db.campaigns.find(
        {"senderUserId": current_user["id"]},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(100)
    
    result = []
    for c in campaigns:
        if not c.get("identityUnlocked", False):
            c["receiverName"] = "Creator" if c["receiverType"] == "creator" else "Brand"
        result.append(CampaignResponse(**c))
    
    return result

@campaign_router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Get campaign details"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check user is part of this campaign
    if campaign["senderUserId"] != current_user["id"] and campaign["receiverUserId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Mask identity if payment not made
    if not campaign.get("identityUnlocked", False):
        if campaign["senderUserId"] != current_user["id"]:
            campaign["senderName"] = "Brand" if campaign["senderType"] == "business" else "Creator"
        if campaign["receiverUserId"] != current_user["id"]:
            campaign["receiverName"] = "Creator" if campaign["receiverType"] == "creator" else "Brand"
    
    return CampaignResponse(**campaign)

@campaign_router.patch("/{campaign_id}/respond")
async def respond_to_campaign(
    campaign_id: str,
    action: Literal["accept", "reject"] = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Accept or reject a campaign request"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["receiverUserId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the receiver can respond")
    
    if campaign["status"] != "pending":
        raise HTTPException(status_code=400, detail="Campaign already responded to")
    
    now = datetime.now(timezone.utc).isoformat()
    
    if action == "accept":
        new_status = "awaiting_payment"
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": {"status": new_status, "updatedAt": now}}
        )
        return {"message": "Campaign accepted! Waiting for payment commitment.", "status": new_status}
    else:
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": {"status": "rejected", "updatedAt": now}}
        )
        return {"message": "Campaign rejected.", "status": "rejected"}

@campaign_router.post("/{campaign_id}/pay")
async def pay_for_campaign(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """
    Pay for campaign - unlocks identity and chat.
    - Paid collab: Full escrow amount
    - Barter collab: Facilitation fee (₹149)
    """
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["senderUserId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the sender can pay")
    
    if campaign["status"] != "awaiting_payment":
        raise HTTPException(status_code=400, detail="Campaign not in awaiting_payment status")
    
    if campaign["paymentStatus"] == "paid":
        raise HTTPException(status_code=400, detail="Already paid")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Calculate payment amount
    if campaign["campaignType"] == "paid":
        amount = campaign["escrowAmount"]
        payment_type = "escrow"
    else:  # barter
        amount = BARTER_FACILITATION_FEE / 100  # Convert paise to rupees
        payment_type = "facilitation_fee"
    
    # In TEST MODE, simulate successful payment
    payment_record = {
        "id": str(uuid.uuid4()),
        "campaignId": campaign_id,
        "userId": current_user["id"],
        "amount": amount,
        "paymentType": payment_type,
        "status": "success",
        "mode": "test",
        "createdAt": now
    }
    await db.payments.insert_one(payment_record)
    
    # Update campaign - UNLOCK IDENTITY AND CHAT
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": "active",
            "paymentStatus": "paid",
            "identityUnlocked": True,
            "chatEnabled": True,
            "updatedAt": now
        }}
    )
    
    # Get actual names for response
    sender_profile_collection = "brand_profiles" if campaign["senderType"] == "business" else "creator_profiles"
    receiver_profile_collection = "creator_profiles" if campaign["receiverType"] == "creator" else "brand_profiles"
    
    sender_profile = await db[sender_profile_collection].find_one({"id": campaign["senderId"]}, {"_id": 0})
    receiver_profile = await db[receiver_profile_collection].find_one({"id": campaign["receiverId"]}, {"_id": 0})
    
    sender_instagram = sender_profile.get("instagramUsername") if sender_profile else None
    receiver_instagram = receiver_profile.get("instagramUsername") if receiver_profile else None
    
    return {
        "success": True,
        "message": f"Payment successful! Identity and chat unlocked.",
        "status": "active",
        "identityUnlocked": True,
        "chatEnabled": True,
        "senderInstagram": sender_instagram,
        "receiverInstagram": receiver_instagram,
        "amountPaid": amount,
        "paymentType": payment_type
    }

@campaign_router.post("/{campaign_id}/shipping")
async def add_shipping_details(
    campaign_id: str,
    shippingDetails: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Brand adds shipping details for barter collab"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["senderUserId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the sender can add shipping details")
    
    if campaign["campaignType"] != "barter":
        raise HTTPException(status_code=400, detail="Shipping details only for barter collabs")
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "shippingDetails": shippingDetails,
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Shipping details added", "success": True}

@campaign_router.post("/{campaign_id}/product-received")
async def confirm_product_received(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Creator confirms product received for barter collab"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["receiverUserId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the receiver can confirm receipt")
    
    if campaign["campaignType"] != "barter":
        raise HTTPException(status_code=400, detail="Product receipt only for barter collabs")
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "productReceived": True,
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Product receipt confirmed", "success": True}

@campaign_router.post("/{campaign_id}/submit-content")
async def submit_content(
    campaign_id: str,
    contentLink: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Creator submits content link for review"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Determine who is the creator in this campaign
    if campaign["receiverType"] == "creator" and campaign["receiverUserId"] == current_user["id"]:
        pass  # Creator is receiver
    elif campaign["senderType"] == "creator" and campaign["senderUserId"] == current_user["id"]:
        pass  # Creator is sender
    else:
        raise HTTPException(status_code=403, detail="Only the creator can submit content")
    
    if campaign["status"] != "active":
        raise HTTPException(status_code=400, detail="Campaign must be active to submit content")
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "contentLink": contentLink,
            "status": "content_submitted",
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Content submitted for review", "success": True}

@campaign_router.post("/{campaign_id}/approve")
async def approve_content(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Brand approves content and releases escrow"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Determine who is the brand in this campaign
    if campaign["senderType"] == "business" and campaign["senderUserId"] == current_user["id"]:
        pass  # Brand is sender
    elif campaign["receiverType"] == "brand" and campaign["receiverUserId"] == current_user["id"]:
        pass  # Brand is receiver (rare case)
    else:
        raise HTTPException(status_code=403, detail="Only the brand can approve content")
    
    if campaign["status"] != "content_submitted":
        raise HTTPException(status_code=400, detail="No content to approve")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Complete the campaign
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {
            "status": "completed",
            "updatedAt": now
        }}
    )
    
    # For paid collabs, record payout (simulated)
    if campaign["campaignType"] == "paid":
        payout_record = {
            "id": str(uuid.uuid4()),
            "campaignId": campaign_id,
            "creatorUserId": campaign["receiverUserId"] if campaign["receiverType"] == "creator" else campaign["senderUserId"],
            "amount": campaign["creatorPayout"],
            "status": "released",
            "mode": "test",
            "createdAt": now
        }
        await db.payouts.insert_one(payout_record)
    
    return {
        "message": "Content approved! Campaign completed.",
        "success": True,
        "status": "completed",
        "payoutAmount": campaign.get("creatorPayout", 0) if campaign["campaignType"] == "paid" else 0
    }

@campaign_router.post("/{campaign_id}/report")
async def report_campaign_issue(
    campaign_id: str,
    reason: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Report an issue with a campaign (identity leak, no content, etc.)"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["senderUserId"] != current_user["id"] and campaign["receiverUserId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="You're not part of this campaign")
    
    report = {
        "id": str(uuid.uuid4()),
        "campaignId": campaign_id,
        "reporterId": current_user["id"],
        "reason": reason,
        "status": "pending",
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    await db.reports.insert_one(report)
    
    return {"message": "Report submitted. Admin will review.", "success": True, "reportId": report["id"]}

# ============== MESSAGING (CHAT) ==============

@message_router.get("/{campaign_id}", response_model=List[MessageResponse])
async def get_messages(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Get messages for a campaign - only if chat is enabled"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["senderUserId"] != current_user["id"] and campaign["receiverUserId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not campaign.get("chatEnabled", False):
        raise HTTPException(status_code=403, detail="Chat not enabled. Complete payment first.")
    
    messages = await db.messages.find({"campaignId": campaign_id}, {"_id": 0}).sort("createdAt", 1).to_list(500)
    
    return [MessageResponse(**m) for m in messages]

@message_router.post("/{campaign_id}", response_model=MessageResponse, status_code=201)
async def send_message(
    campaign_id: str,
    message: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Send a message in a campaign chat"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["senderUserId"] != current_user["id"] and campaign["receiverUserId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not campaign.get("chatEnabled", False):
        raise HTTPException(status_code=403, detail="Chat not enabled. Complete payment first.")
    
    # Check for blocked content
    is_blocked = check_blocked_content(message.content)
    
    if is_blocked:
        # Log bypass attempt
        await db.bypass_attempts.insert_one({
            "id": str(uuid.uuid4()),
            "campaignId": campaign_id,
            "userId": current_user["id"],
            "content": message.content,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
    
    message_doc = {
        "id": str(uuid.uuid4()),
        "campaignId": campaign_id,
        "senderId": current_user["id"],
        "senderType": current_user["role"],
        "content": message.content if not is_blocked else "[Message blocked - external contact not allowed]",
        "blocked": is_blocked,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.messages.insert_one(message_doc)
    
    return MessageResponse(**{k: v for k, v in message_doc.items() if k != "_id"})

# ============== ADMIN ENDPOINTS ==============

@admin_router.get("/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """Get platform statistics"""
    if not current_user.get("isAdmin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    stats = {
        "totalUsers": await db.users.count_documents({}),
        "totalCreators": await db.creator_profiles.count_documents({}),
        "totalBrands": await db.brand_profiles.count_documents({}),
        "totalCampaigns": await db.campaigns.count_documents({}),
        "activeCampaigns": await db.campaigns.count_documents({"status": "active"}),
        "completedCampaigns": await db.campaigns.count_documents({"status": "completed"}),
        "pendingReports": await db.reports.count_documents({"status": "pending"}),
        "blacklistedCreators": await db.creator_profiles.count_documents({"isBlacklisted": True}),
        "bypassAttempts": await db.bypass_attempts.count_documents({})
    }
    
    return stats

@admin_router.get("/reports")
async def get_reports(current_user: dict = Depends(get_current_user)):
    """Get all pending reports"""
    if not current_user.get("isAdmin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    reports = await db.reports.find({"status": "pending"}, {"_id": 0}).to_list(100)
    return reports

@admin_router.post("/blacklist/{user_id}")
async def blacklist_user(user_id: str, reason: str = Query(...), current_user: dict = Depends(get_current_user)):
    """Blacklist a creator"""
    if not current_user.get("isAdmin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Update user
    await db.users.update_one({"id": user_id}, {"$set": {"isBlacklisted": True}})
    
    # Update creator profile
    await db.creator_profiles.update_one({"userId": user_id}, {"$set": {"isBlacklisted": True}})
    
    # Cancel active campaigns
    await db.campaigns.update_many(
        {"$or": [{"senderUserId": user_id}, {"receiverUserId": user_id}], "status": {"$in": ["pending", "awaiting_payment", "active"]}},
        {"$set": {"status": "cancelled"}}
    )
    
    # Log blacklist
    await db.blacklist_log.insert_one({
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "reason": reason,
        "adminId": current_user["id"],
        "createdAt": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": f"User {user_id} has been blacklisted", "success": True}

# ============== SEED DATA ==============

@api_router.post("/seed")
async def seed_database():
    """Create demo data for testing"""
    # Clear existing data
    for collection in ["users", "creator_profiles", "brand_profiles", "campaigns", "messages", "payments", "reports"]:
        await db[collection].delete_many({})
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create admin
    admin_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": admin_id,
        "email": "admin@orange.com",
        "passwordHash": hash_password("admin123"),
        "role": "business",
        "hasCompletedOnboarding": True,
        "isAdmin": True,
        "instagramVerified": True,
        "isBlacklisted": False,
        "createdAt": now
    })
    
    # Create sample creators
    creators = [
        {"name": "Priya Sharma", "niche": "Fashion", "language": "Hindi", "contentType": "Reels", "location": "Mumbai", "reelPrice": 15000, "storyPrice": 5000, "engagement": 8.5},
        {"name": "Arjun Kapoor", "niche": "Fitness", "language": "English", "contentType": "Reels, Stories", "location": "Delhi", "reelPrice": 12000, "storyPrice": 4000, "engagement": 6.2},
        {"name": "Meera Patel", "niche": "Beauty", "language": "English", "contentType": "Reels", "location": "Bangalore", "reelPrice": 8000, "storyPrice": 3000, "engagement": 9.1},
        {"name": "Rahul Verma", "niche": "Tech", "language": "Hindi", "contentType": "Reels, Posts", "location": "Hyderabad", "reelPrice": 10000, "storyPrice": 3500, "engagement": 5.8},
    ]
    
    for i, c in enumerate(creators):
        user_id = str(uuid.uuid4())
        profile_id = str(uuid.uuid4())
        
        await db.users.insert_one({
            "id": user_id,
            "email": f"creator{i+1}@orange.com",
            "passwordHash": hash_password("password123"),
            "role": "creator",
            "hasCompletedOnboarding": True,
            "isAdmin": False,
            "instagramVerified": True,
            "instagramUserId": f"ig_{uuid.uuid4().hex[:8]}",
            "instagramUsername": f"@{c['name'].lower().replace(' ', '_')}",
            "engagementRate": c["engagement"],
            "isBlacklisted": False,
            "createdAt": now
        })
        
        await db.creator_profiles.insert_one({
            "id": profile_id,
            "userId": user_id,
            "name": c["name"],
            "bio": f"Content creator specializing in {c['niche']}",
            "location": c["location"],
            "niche": c["niche"],
            "language": c["language"],
            "contentType": c["contentType"],
            "niches": [c["niche"]],
            "reelPrice": c["reelPrice"],
            "storyPrice": c["storyPrice"],
            "postPrice": c["reelPrice"] * 0.8,
            "paidCollabsEnabled": True,
            "barterEnabled": True,
            "instagramVerified": True,
            "instagramUserId": f"ig_{uuid.uuid4().hex[:8]}",
            "instagramUsername": f"@{c['name'].lower().replace(' ', '_')}",
            "engagementRate": c["engagement"],
            "profilePhotoUrl": "",
            "isBlacklisted": False,
            "createdAt": now,
            "updatedAt": now
        })
    
    # Create sample brands
    brands = [
        {"name": "Glow Cosmetics", "industry": "Beauty", "location": "Mumbai", "budget": "₹10k-₹50k", "deliverables": "Reels, Stories"},
        {"name": "FitLife Nutrition", "industry": "Health & Fitness", "location": "Delhi", "budget": "₹15k-₹40k", "deliverables": "Reels, Posts"},
    ]
    
    for i, b in enumerate(brands):
        user_id = str(uuid.uuid4())
        profile_id = str(uuid.uuid4())
        
        await db.users.insert_one({
            "id": user_id,
            "email": f"brand{i+1}@orange.com",
            "passwordHash": hash_password("password123"),
            "role": "business",
            "hasCompletedOnboarding": True,
            "isAdmin": False,
            "instagramVerified": True,
            "instagramUserId": f"ig_{uuid.uuid4().hex[:8]}",
            "instagramUsername": f"@{b['name'].lower().replace(' ', '_')}",
            "isBlacklisted": False,
            "createdAt": now
        })
        
        await db.brand_profiles.insert_one({
            "id": profile_id,
            "userId": user_id,
            "brandName": b["name"],
            "industry": b["industry"],
            "bio": f"Leading brand in {b['industry']}",
            "location": b["location"],
            "deliverables": b["deliverables"],
            "budgetRange": b["budget"],
            "barterEnabled": True,
            "paidCollabsEnabled": True,
            "brandRequirements": "High-quality content with authentic engagement",
            "instagramVerified": True,
            "instagramUserId": f"ig_{uuid.uuid4().hex[:8]}",
            "instagramUsername": f"@{b['name'].lower().replace(' ', '_')}",
            "profilePhotoUrl": "",
            "createdAt": now,
            "updatedAt": now
        })
    
    return {
        "message": "Seed data created!",
        "creators": len(creators),
        "brands": len(brands),
        "testCredentials": {
            "admin": "admin@orange.com / admin123",
            "creator": "creator1@orange.com / password123",
            "brand": "brand1@orange.com / password123"
        }
    }

# ============== ROUTER REGISTRATION ==============

api_router.include_router(auth_router)
api_router.include_router(creator_router)
api_router.include_router(business_router)
api_router.include_router(marketplace_router)
api_router.include_router(campaign_router)
api_router.include_router(message_router)
api_router.include_router(admin_router)
app.include_router(api_router)

# ============== CORS ==============

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== STARTUP/SHUTDOWN ==============

@app.on_event("startup")
async def startup_db_client():
    logger.info("Orange API started - Two-Sided Creator-Brand Collaboration Platform")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
