from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import cloudinary
import cloudinary.uploader

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

# Create the main app
app = FastAPI(title="Orange - Creator Marketplace API")

# Create routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
creator_router = APIRouter(prefix="/creator", tags=["Creator"])
business_router = APIRouter(prefix="/business", tags=["Business"])
request_router = APIRouter(prefix="/requests", tags=["Requests"])
message_router = APIRouter(prefix="/messages", tags=["Messages"])

security = HTTPBearer()

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

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class MediaItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # "image" or "video"
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
    niches: List[str]
    isOpenToBarter: bool
    rates: RateInfo
    mediaGallery: List[MediaItem]
    createdAt: str
    updatedAt: str

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

class CollaborationRequestCreate(BaseModel):
    creatorId: str
    title: str
    brief: str
    offerAmount: Optional[float] = 0
    deliverables: Optional[str] = ""
    timeline: Optional[str] = ""

class CollaborationRequestResponse(BaseModel):
    id: str
    creatorId: str
    businessId: str
    title: str
    brief: str
    offerAmount: float
    deliverables: str
    status: str
    timeline: str
    createdAt: str
    updatedAt: str
    creatorName: Optional[str] = ""
    businessName: Optional[str] = ""
    creatorPhoto: Optional[str] = ""
    businessPhoto: Optional[str] = ""

class MessageCreate(BaseModel):
    text: str

class MessageResponse(BaseModel):
    id: str
    requestId: str
    senderUserId: str
    senderName: str
    text: str
    createdAt: str

class UploadResponse(BaseModel):
    url: str
    thumbnailUrl: str
    type: str

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

# ============== AUTH ROUTES ==============

@auth_router.post("/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate):
    # Check if user exists
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
            hasCompletedOnboarding=user.get("hasCompletedOnboarding", False)
        )
    )

@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
        hasCompletedOnboarding=current_user.get("hasCompletedOnboarding", False)
    )

@auth_router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}

# ============== UPLOAD ROUTES ==============

@api_router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    try:
        contents = await file.read()
        
        # Determine resource type
        content_type = file.content_type or ""
        resource_type = "video" if content_type.startswith("video") else "image"
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            contents,
            resource_type=resource_type,
            folder="orange_marketplace",
            public_id=f"{current_user['id']}_{uuid.uuid4()}"
        )
        
        url = result.get("secure_url", result.get("url", ""))
        
        # Generate thumbnail
        if resource_type == "video":
            thumbnail_url = cloudinary.CloudinaryImage(result["public_id"]).build_url(
                resource_type="video",
                format="jpg",
                transformation=[{"start_offset": "2", "width": 400, "height": 400, "crop": "fill"}]
            )
        else:
            thumbnail_url = cloudinary.CloudinaryImage(result["public_id"]).build_url(
                width=400,
                height=400,
                crop="fill"
            )
        
        return UploadResponse(
            url=url,
            thumbnailUrl=thumbnail_url,
            type=resource_type
        )
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# ============== CREATOR ROUTES ==============

@creator_router.post("/profile", response_model=CreatorProfileResponse)
async def create_creator_profile(profile: CreatorProfileCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "creator":
        raise HTTPException(status_code=403, detail="Only creators can create creator profiles")
    
    # Check if profile exists
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
    
    # Mark onboarding complete
    await db.users.update_one({"id": current_user["id"]}, {"$set": {"hasCompletedOnboarding": True}})
    
    return CreatorProfileResponse(**profile_doc)

@creator_router.get("/profile", response_model=CreatorProfileResponse)
async def get_my_creator_profile(current_user: dict = Depends(get_current_user)):
    profile = await db.creator_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return CreatorProfileResponse(**profile)

@creator_router.get("/requests", response_model=List[CollaborationRequestResponse])
async def get_creator_requests(current_user: dict = Depends(get_current_user)):
    profile = await db.creator_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Creator profile not found")
    
    requests = await db.collaboration_requests.find({"creatorId": profile["id"]}, {"_id": 0}).to_list(100)
    
    # Enrich with business info
    for req in requests:
        business = await db.business_profiles.find_one({"userId": req["businessId"]}, {"_id": 0})
        if business:
            req["businessName"] = business.get("brandName", "")
            req["businessPhoto"] = business.get("profilePhotoUrl", "")
        req["creatorName"] = profile.get("name", "")
        req["creatorPhoto"] = profile.get("profilePhotoUrl", "")
    
    return [CollaborationRequestResponse(**req) for req in requests]

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
    
    return BusinessProfileResponse(**profile_doc)

@business_router.get("/profile", response_model=BusinessProfileResponse)
async def get_my_business_profile(current_user: dict = Depends(get_current_user)):
    profile = await db.business_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return BusinessProfileResponse(**profile)

# ============== MARKETPLACE / PUBLIC ROUTES ==============

@api_router.get("/creators", response_model=List[CreatorProfileResponse])
async def get_creators(
    niche: Optional[str] = Query(None),
    minFollowers: Optional[int] = Query(None),
    maxFollowers: Optional[int] = Query(None),
    location: Optional[str] = Query(None),
    openToBarter: Optional[bool] = Query(None),
    limit: int = Query(50, le=100),
    skip: int = Query(0)
):
    query = {}
    
    if niche:
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
    return [CreatorProfileResponse(**c) for c in creators]

@api_router.get("/creators/{creator_id}", response_model=CreatorProfileResponse)
async def get_creator_by_id(creator_id: str):
    creator = await db.creator_profiles.find_one({"id": creator_id}, {"_id": 0})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    return CreatorProfileResponse(**creator)

@api_router.get("/businesses/{business_id}", response_model=BusinessProfileResponse)
async def get_business_by_id(business_id: str):
    business = await db.business_profiles.find_one({"id": business_id}, {"_id": 0})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return BusinessProfileResponse(**business)

# ============== COLLABORATION REQUEST ROUTES ==============

@request_router.post("/", response_model=CollaborationRequestResponse)
async def create_request(req_data: CollaborationRequestCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "business":
        raise HTTPException(status_code=403, detail="Only businesses can send collaboration requests")
    
    # Verify creator exists
    creator = await db.creator_profiles.find_one({"id": req_data.creatorId}, {"_id": 0})
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    business = await db.business_profiles.find_one({"userId": current_user["id"]}, {"_id": 0})
    if not business:
        raise HTTPException(status_code=404, detail="Please complete your business profile first")
    
    now = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())
    
    request_doc = {
        "id": request_id,
        "creatorId": req_data.creatorId,
        "businessId": current_user["id"],
        "title": req_data.title,
        "brief": req_data.brief,
        "offerAmount": req_data.offerAmount or 0,
        "deliverables": req_data.deliverables or "",
        "status": "pending",
        "timeline": req_data.timeline or "",
        "createdAt": now,
        "updatedAt": now
    }
    
    await db.collaboration_requests.insert_one(request_doc)
    
    return CollaborationRequestResponse(
        **request_doc,
        creatorName=creator.get("name", ""),
        businessName=business.get("brandName", ""),
        creatorPhoto=creator.get("profilePhotoUrl", ""),
        businessPhoto=business.get("profilePhotoUrl", "")
    )

@request_router.get("/sent", response_model=List[CollaborationRequestResponse])
async def get_sent_requests(current_user: dict = Depends(get_current_user)):
    requests = await db.collaboration_requests.find({"businessId": current_user["id"]}, {"_id": 0}).to_list(100)
    
    for req in requests:
        creator = await db.creator_profiles.find_one({"id": req["creatorId"]}, {"_id": 0})
        business = await db.business_profiles.find_one({"userId": req["businessId"]}, {"_id": 0})
        if creator:
            req["creatorName"] = creator.get("name", "")
            req["creatorPhoto"] = creator.get("profilePhotoUrl", "")
        if business:
            req["businessName"] = business.get("brandName", "")
            req["businessPhoto"] = business.get("profilePhotoUrl", "")
    
    return [CollaborationRequestResponse(**req) for req in requests]

@request_router.get("/{request_id}", response_model=CollaborationRequestResponse)
async def get_request(request_id: str, current_user: dict = Depends(get_current_user)):
    req = await db.collaboration_requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Check access
    creator = await db.creator_profiles.find_one({"id": req["creatorId"]}, {"_id": 0})
    if req["businessId"] != current_user["id"] and (not creator or creator["userId"] != current_user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    business = await db.business_profiles.find_one({"userId": req["businessId"]}, {"_id": 0})
    if creator:
        req["creatorName"] = creator.get("name", "")
        req["creatorPhoto"] = creator.get("profilePhotoUrl", "")
    if business:
        req["businessName"] = business.get("brandName", "")
        req["businessPhoto"] = business.get("profilePhotoUrl", "")
    
    return CollaborationRequestResponse(**req)

@request_router.patch("/{request_id}/status")
async def update_request_status(request_id: str, status: str = Query(...), current_user: dict = Depends(get_current_user)):
    if status not in ["accepted", "declined"]:
        raise HTTPException(status_code=400, detail="Status must be 'accepted' or 'declined'")
    
    req = await db.collaboration_requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Only creator can update status
    creator = await db.creator_profiles.find_one({"id": req["creatorId"]}, {"_id": 0})
    if not creator or creator["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Only the creator can update request status")
    
    await db.collaboration_requests.update_one(
        {"id": request_id},
        {"$set": {"status": status, "updatedAt": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": f"Request {status} successfully"}

# ============== MESSAGE ROUTES ==============

@message_router.get("/{request_id}", response_model=List[MessageResponse])
async def get_messages(request_id: str, current_user: dict = Depends(get_current_user)):
    req = await db.collaboration_requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Check access
    creator = await db.creator_profiles.find_one({"id": req["creatorId"]}, {"_id": 0})
    if req["businessId"] != current_user["id"] and (not creator or creator["userId"] != current_user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = await db.messages.find({"requestId": request_id}, {"_id": 0}).sort("createdAt", 1).to_list(500)
    return [MessageResponse(**msg) for msg in messages]

@message_router.post("/{request_id}", response_model=MessageResponse)
async def send_message(request_id: str, msg_data: MessageCreate, current_user: dict = Depends(get_current_user)):
    req = await db.collaboration_requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Check access
    creator = await db.creator_profiles.find_one({"id": req["creatorId"]}, {"_id": 0})
    if req["businessId"] != current_user["id"] and (not creator or creator["userId"] != current_user["id"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
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
        "requestId": request_id,
        "senderUserId": current_user["id"],
        "senderName": sender_name,
        "text": msg_data.text,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.messages.insert_one(message_doc)
    
    return MessageResponse(**message_doc)

# ============== SEED DATA ==============

@api_router.post("/seed")
async def seed_data():
    # Clear existing data
    await db.users.delete_many({})
    await db.creator_profiles.delete_many({})
    await db.business_profiles.delete_many({})
    await db.collaboration_requests.delete_many({})
    await db.messages.delete_many({})
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create sample creators
    creators_data = [
        {
            "name": "Priya Sharma",
            "bio": "Fashion & lifestyle creator ✨ Making everyday looks pop! 500K+ community of style lovers.",
            "location": "Mumbai, India",
            "instagramHandle": "@priyasharma",
            "instagramUrl": "https://instagram.com/priyasharma",
            "followersCount": 520000,
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
        
        # Create user
        user_doc = {
            "id": user_id,
            "email": f"creator{i+1}@orange.com",
            "passwordHash": get_password_hash("password123"),
            "role": "creator",
            "hasCompletedOnboarding": True,
            "createdAt": now
        }
        await db.users.insert_one(user_doc)
        
        # Create profile
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
    
    business_profiles = []
    for i, business in enumerate(businesses_data):
        user_id = str(uuid.uuid4())
        profile_id = str(uuid.uuid4())
        
        user_doc = {
            "id": user_id,
            "email": f"business{i+1}@orange.com",
            "passwordHash": get_password_hash("password123"),
            "role": "business",
            "hasCompletedOnboarding": True,
            "createdAt": now
        }
        await db.users.insert_one(user_doc)
        
        profile_doc = {
            "id": profile_id,
            "userId": user_id,
            **business,
            "mediaGallery": [],
            "createdAt": now,
            "updatedAt": now
        }
        await db.business_profiles.insert_one(profile_doc)
        business_profiles.append({"profile": profile_doc, "userId": user_id})
    
    # Create sample collaboration request
    request_doc = {
        "id": str(uuid.uuid4()),
        "creatorId": creator_profiles[0]["id"],
        "businessId": business_profiles[0]["userId"],
        "title": "Summer Collection Campaign",
        "brief": "We'd love to collaborate with you on our new summer collection! Looking for 3 reels and 5 stories showcasing our products.",
        "offerAmount": 30000,
        "deliverables": "3 Reels, 5 Stories",
        "status": "pending",
        "timeline": "2 weeks",
        "createdAt": now,
        "updatedAt": now
    }
    await db.collaboration_requests.insert_one(request_doc)
    
    return {"message": "Seed data created successfully", "creators": len(creators_data), "businesses": len(businesses_data)}

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
api_router.include_router(request_router)
api_router.include_router(message_router)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
