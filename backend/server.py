from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import random
import hmac
import hashlib
from pathlib import Path
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Literal
import uuid
import secrets
import requests
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

SECRET_KEY = os.environ.get('JWT_SECRET', 'change-me-in-production')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_DAYS = 7
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

PLATFORM_COMMISSION_PERCENT = 10
BARTER_FEE_PERCENT = 10
CREATOR_SUBSCRIPTION_FEE = 5000
AUTO_APPROVE_DAYS = 7
REQUEST_EXPIRY_HOURS = 72

RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
RAZORPAY_API_BASE = 'https://api.razorpay.com/v1'

INSTAGRAM_APP_ID = os.environ.get('INSTAGRAM_APP_ID', '')
INSTAGRAM_APP_SECRET = os.environ.get('INSTAGRAM_APP_SECRET', '')
INSTAGRAM_REDIRECT_URI = os.environ.get('INSTAGRAM_REDIRECT_URI', 'http://localhost:8000/api/auth/instagram/callback')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
INSTAGRAM_SCOPES = 'instagram_business_basic'

COLLAB_STATES = [
    'requested', 'accepted', 'payment_pending', 'paid', 'in_progress',
    'link_submitted', 'link_verified', 'completed', 'disputed', 'cancelled'
]

app = FastAPI(title='Orange - Creator-Brand Collaboration Platform API')
api_router = APIRouter(prefix='/api')
auth_router = APIRouter(prefix='/auth', tags=['Authentication'])
creator_router = APIRouter(prefix='/creator', tags=['Creator'])
business_router = APIRouter(prefix='/business', tags=['Business'])
marketplace_router = APIRouter(prefix='/marketplace', tags=['Marketplace'])
campaign_router = APIRouter(prefix='/campaigns', tags=['Campaigns'])
payment_router = APIRouter(prefix='/payments', tags=['Payments'])
message_router = APIRouter(prefix='/messages', tags=['Messages'])
admin_router = APIRouter(prefix='/admin', tags=['Admin'])
security = HTTPBearer()

BLOCKED_PATTERNS = [
    r'\b(instagram|insta|ig)\b', r'\b(whatsapp|wa)\b', r'\b(telegram|tg)\b',
    r'@[a-zA-Z0-9_]+', r'\b\d{10}\b', r'\b(snapchat|snap)\b',
    r'\b(twitter|x\.com)\b', r'\b(facebook|fb)\b', r'\b(linkedin)\b',
    r'\b(email|mail)\b.*@',
]
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Literal['creator', 'business']
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
    token_type: str = 'bearer'
    user: UserResponse

class CreatorProfileCreate(BaseModel):
    name: str
    bio: Optional[str] = ''
    location: Optional[str] = ''
    niche: Optional[str] = ''
    language: Optional[str] = 'English'
    contentType: Optional[str] = ''
    niches: Optional[List[str]] = []
    reelPrice: Optional[float] = 0
    storyPrice: Optional[float] = 0
    postPrice: Optional[float] = 0
    paidCollabsEnabled: Optional[bool] = True
    barterEnabled: Optional[bool] = True
    profilePhotoUrl: Optional[str] = ''
class CreatorProfileFull(BaseModel):
    id: str; userId: str; name: str; bio: str; location: str; niche: str; language: str
    contentType: str; niches: List[str]; reelPrice: float; storyPrice: float; postPrice: float
    paidCollabsEnabled: bool; barterEnabled: bool; instagramVerified: bool; engagementRate: float
    profilePhotoUrl: str; isBlacklisted: bool = False; isVisible: bool = True
    subscriptionActive: bool = True; rating: Optional[float] = None; totalCollabs: int = 0

class BrandProfileCreate(BaseModel):
    brandName: str
    industry: Optional[str] = ''
    bio: Optional[str] = ''
    location: Optional[str] = ''
    deliverables: Optional[str] = ''
    budgetRange: Optional[str] = ''
    barterEnabled: Optional[bool] = True
    paidCollabsEnabled: Optional[bool] = True
    brandRequirements: Optional[str] = ''
    profilePhotoUrl: Optional[str] = ''
class BrandProfileFull(BaseModel):
    id: str; userId: str; brandName: str; industry: str; bio: str; location: str
    deliverables: str; budgetRange: str; barterEnabled: bool; paidCollabsEnabled: bool
    brandRequirements: str; instagramVerified: bool; profilePhotoUrl: str

class CreatorDiscovery(BaseModel):
    id: str; niche: str; language: str; contentType: str; niches: List[str]
    reelPrice: float; storyPrice: float; postPrice: float; engagementRate: float
    paidCollabsEnabled: bool; barterEnabled: bool; location: str
class BrandDiscovery(BaseModel):
    id: str; industry: str; location: str; deliverables: str; budgetRange: str
    barterEnabled: bool; paidCollabsEnabled: bool; brandRequirements: str

class CampaignCreate(BaseModel):
    receiverId: str
    receiverType: Literal['creator', 'brand']
    campaignType: Literal['paid', 'barter_product', 'barter_service']
    deliverables: str
    budget: Optional[float] = 0
    productValue: Optional[float] = 0
    timeline: Optional[str] = ''
    brief: Optional[str] = ''
    barterDetails: Optional[str] = ''
class CampaignResponse(BaseModel):
    id: str; senderId: str; senderType: str; senderName: str; receiverId: str; receiverType: str
    receiverName: str; campaignType: str; deliverables: str; budget: float; productValue: float
    barterFee: float; timeline: str; brief: str; barterDetails: str; status: str
    paymentStatus: str; escrowAmount: float; platformCommission: float; creatorPayout: float
    identityUnlocked: bool; chatEnabled: bool; contentLink: Optional[str] = None
    linkVerified: bool = False; shippingDetails: Optional[str] = None; productReceived: bool = False
    senderInstagram: Optional[str] = None; receiverInstagram: Optional[str] = None
    createdAt: str; updatedAt: str; expiresAt: Optional[str] = None
class MessageCreate(BaseModel): content: str
class MessageResponse(BaseModel):
    id: str; campaignId: str; senderId: str; senderType: str; content: str
    blocked: bool = False; createdAt: str
class InstagramVerifyRequest(BaseModel): instagramUsername: str
class InstagramVerifyResponse(BaseModel):
    success: bool; instagramUserId: str; followersCount: int; engagementRate: float; message: str
class InstagramStatusResponse(BaseModel):
    connected: bool; instagramUserId: Optional[str] = None; instagramUsername: Optional[str] = None
    followersCount: Optional[int] = None; engagementRate: Optional[float] = None
class InstagramOAuthStartResponse(BaseModel): authorizationUrl: str

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def verify_password(plain_password: str, hashed_password: str) -> bool: return pwd_context.verify(plain_password, hashed_password)
def hash_password(password: str) -> str: return pwd_context.hash(password)
def create_access_token(data: dict) -> str:
    payload = data.copy(); payload['exp'] = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]); user_id = payload.get('sub')
        if not user_id: raise HTTPException(status_code=401, detail='Invalid token')
        user = await db.users.find_one({'id': user_id}, {'_id': 0})
        if not user: raise HTTPException(status_code=401, detail='User not found')
        if user.get('isBlacklisted', False): raise HTTPException(status_code=403, detail='Your account has been blacklisted')
        return user
    except JWTError: raise HTTPException(status_code=401, detail='Invalid token')
def check_blocked_content(message: str) -> bool:
    return any(re.search(pattern, message.lower(), re.IGNORECASE) for pattern in BLOCKED_PATTERNS)
def generate_simulated_engagement_rate() -> float: return round(random.uniform(2.0, 12.0), 2)
def build_instagram_authorization_url(state: str) -> str:
    return f"https://www.instagram.com/oauth/authorize?{urlencode({'client_id': INSTAGRAM_APP_ID, 'redirect_uri': INSTAGRAM_REDIRECT_URI, 'response_type': 'code', 'scope': INSTAGRAM_SCOPES, 'state': state})}"
def razorpay_configured() -> bool: return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)
def razorpay_auth(): return (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
def razorpay_request(method: str, path: str, **kwargs):
    if not razorpay_configured(): raise HTTPException(status_code=503, detail='Razorpay is not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to backend/.env.')
    response = requests.request(method, f'{RAZORPAY_API_BASE}{path}', auth=razorpay_auth(), timeout=20, **kwargs)
    if response.status_code >= 400:
        try: detail = response.json().get('error', {}).get('description', 'Razorpay API error')
        except Exception: detail = 'Razorpay API error'
        raise HTTPException(status_code=502, detail=detail)
    return response.json()
def verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    generated = hmac.new(RAZORPAY_KEY_SECRET.encode(), f'{order_id}|{payment_id}'.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated, signature)

@auth_router.post('/signup', response_model=TokenResponse)
async def signup(user_data: UserCreate):
    if await db.users.find_one({'email': user_data.email}): raise HTTPException(status_code=400, detail='Email already registered')
    if len(user_data.password) < 6: raise HTTPException(status_code=400, detail='Password must be at least 6 characters')
    user_id = str(uuid.uuid4()); now = datetime.now(timezone.utc).isoformat()
    await db.users.insert_one({'id': user_id, 'email': user_data.email, 'passwordHash': hash_password(user_data.password), 'role': user_data.role, 'hasCompletedOnboarding': False, 'isAdmin': False, 'instagramVerified': False, 'isBlacklisted': False, 'createdAt': now})
    return TokenResponse(access_token=create_access_token({'sub': user_id, 'email': user_data.email, 'role': user_data.role}), user=UserResponse(id=user_id,email=user_data.email,role=user_data.role))
@auth_router.post('/login', response_model=TokenResponse)
async def login(user_data: UserLogin):
    user = await db.users.find_one({'email': user_data.email}, {'_id':0})
    if not user or not verify_password(user_data.password, user['passwordHash']): raise HTTPException(status_code=401, detail='Invalid email or password')
    if user.get('isBlacklisted', False): raise HTTPException(status_code=403, detail='Your account has been blacklisted')
    return TokenResponse(access_token=create_access_token({'sub':user['id'],'email':user['email'],'role':user['role']}), user=UserResponse(id=user['id'],email=user['email'],role=user['role'],hasCompletedOnboarding=user.get('hasCompletedOnboarding',False),isAdmin=user.get('isAdmin',False),instagramVerified=user.get('instagramVerified',False),isBlacklisted=user.get('isBlacklisted',False)))
@auth_router.get('/me', response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(id=current_user['id'],email=current_user['email'],role=current_user['role'],hasCompletedOnboarding=current_user.get('hasCompletedOnboarding',False),isAdmin=current_user.get('isAdmin',False),instagramVerified=current_user.get('instagramVerified',False),isBlacklisted=current_user.get('isBlacklisted',False))
@auth_router.post('/logout')
async def logout(): return {'message':'Logged out successfully','success':True}

@auth_router.get('/instagram/connect', response_model=InstagramOAuthStartResponse)
async def connect_instagram(current_user: dict = Depends(get_current_user)):
    if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET: raise HTTPException(status_code=503, detail='Instagram OAuth is not configured.')
    state = secrets.token_urlsafe(32); await db.users.update_one({'id':current_user['id']},{'$set':{'instagramOAuthState':state,'instagramOAuthStateExpiresAt':datetime.now(timezone.utc)+timedelta(minutes=10)}})
    return InstagramOAuthStartResponse(authorizationUrl=build_instagram_authorization_url(state))
@auth_router.get('/instagram/callback')
async def instagram_callback(code: Optional[str]=None,state: Optional[str]=None,error: Optional[str]=None,error_reason: Optional[str]=None):
    if error or not code or not state: return RedirectResponse(f"{FRONTEND_URL}/instagram/callback?instagram=error&{urlencode({'reason': error_reason or error or 'Instagram authorization was cancelled'})}")
    user = await db.users.find_one({'instagramOAuthState':state,'instagramOAuthStateExpiresAt':{'$gt':datetime.now(timezone.utc)}},{'_id':0})
    if not user: return RedirectResponse(f'{FRONTEND_URL}/instagram/callback?instagram=error&reason=Invalid+or+expired+OAuth+state')
    try:
        response = requests.post('https://api.instagram.com/oauth/access_token', data={'client_id':INSTAGRAM_APP_ID,'client_secret':INSTAGRAM_APP_SECRET,'grant_type':'authorization_code','redirect_uri':INSTAGRAM_REDIRECT_URI,'code':code}, timeout=15); response.raise_for_status(); short=response.json()
        long_response = requests.get('https://graph.instagram.com/access_token', params={'grant_type':'ig_exchange_token','client_secret':INSTAGRAM_APP_SECRET,'access_token':short['access_token']}, timeout=15); long_response.raise_for_status(); long=long_response.json(); token=long.get('access_token', short['access_token'])
        profile_response = requests.get('https://graph.instagram.com/me', params={'fields':'user_id,username,account_type,media_count','access_token':token}, timeout=15); profile_response.raise_for_status(); profile=profile_response.json()
    except Exception as exc:
        logger.warning('Instagram OAuth failed: %s', exc); return RedirectResponse(f'{FRONTEND_URL}/instagram/callback?instagram=error&reason=Instagram+authorization+failed')
    await db.users.update_one({'id':user['id']},{'$set':{'instagramVerified':True,'instagramUserId':profile.get('user_id') or profile.get('id'),'instagramUsername':profile.get('username'),'instagramAccessToken':token,'instagramOAuthState':None,'instagramOAuthStateExpiresAt':None}})
    collection='creator_profiles' if user['role']=='creator' else 'brand_profiles'; await db[collection].update_one({'userId':user['id']},{'$set':{'instagramVerified':True,'instagramUserId':profile.get('user_id') or profile.get('id'),'instagramUsername':profile.get('username')}})
    return RedirectResponse(f'{FRONTEND_URL}/instagram/callback?instagram=connected')
@auth_router.get('/instagram/status', response_model=InstagramStatusResponse)
async def instagram_status(current_user: dict = Depends(get_current_user)):
    return InstagramStatusResponse(connected=bool(current_user.get('instagramVerified')),instagramUserId=current_user.get('instagramUserId'),instagramUsername=current_user.get('instagramUsername'),followersCount=current_user.get('followersCount'),engagementRate=current_user.get('engagementRate'))
@auth_router.post('/instagram/disconnect')
async def disconnect_instagram(current_user: dict = Depends(get_current_user)):
    fields={'instagramVerified':False,'instagramUserId':None,'instagramUsername':None,'instagramAccessToken':None,'instagramOAuthState':None,'instagramOAuthStateExpiresAt':None}; await db.users.update_one({'id':current_user['id']},{'$set':fields}); collection='creator_profiles' if current_user['role']=='creator' else 'brand_profiles'; await db[collection].update_one({'userId':current_user['id']},{'$set':fields}); return {'success':True}
@auth_router.post('/instagram/verify', response_model=InstagramVerifyResponse)
async def verify_instagram(request: InstagramVerifyRequest, current_user: dict = Depends(get_current_user)):
    raise HTTPException(status_code=410, detail='Demo Instagram verification has been removed. Use GET /api/auth/instagram/connect.')

@creator_router.post('/profile', response_model=CreatorProfileFull)
async def create_creator_profile(profile: CreatorProfileCreate, current_user: dict = Depends(get_current_user)):
    if current_user['role']!='creator': raise HTTPException(status_code=403,detail='Only creators can create creator profiles')
    existing=await db.creator_profiles.find_one({'userId':current_user['id']}); now=datetime.now(timezone.utc).isoformat(); profile_id=existing['id'] if existing else str(uuid.uuid4())
    doc={'id':profile_id,'userId':current_user['id'],'name':profile.name,'bio':profile.bio or '','location':profile.location or '','niche':profile.niche or (profile.niches[0] if profile.niches else ''),'language':profile.language or 'English','contentType':profile.contentType or '','niches':profile.niches or [],'reelPrice':profile.reelPrice or 0,'storyPrice':profile.storyPrice or 0,'postPrice':profile.postPrice or 0,'paidCollabsEnabled':profile.paidCollabsEnabled if profile.paidCollabsEnabled is not None else True,'barterEnabled':profile.barterEnabled if profile.barterEnabled is not None else True,'instagramVerified':current_user.get('instagramVerified',False),'instagramUserId':current_user.get('instagramUserId'),'instagramUsername':current_user.get('instagramUsername'),'engagementRate':current_user.get('engagementRate',generate_simulated_engagement_rate()),'profilePhotoUrl':profile.profilePhotoUrl or '','isBlacklisted':False,'isVisible':True,'subscriptionActive':True,'rating':existing.get('rating') if existing else None,'totalCollabs':existing.get('totalCollabs',0) if existing else 0,'createdAt':existing.get('createdAt',now) if existing else now,'updatedAt':now}
    if existing: await db.creator_profiles.update_one({'id':profile_id},{'$set':doc})
    else: await db.creator_profiles.insert_one(doc)
    await db.users.update_one({'id':current_user['id']},{'$set':{'hasCompletedOnboarding':True}}); return CreatorProfileFull(**doc)
@creator_router.get('/profile', response_model=CreatorProfileFull)
async def get_creator_profile(current_user: dict = Depends(get_current_user)):
    if current_user['role']!='creator': raise HTTPException(status_code=403,detail='Only creators can access this')
    p=await db.creator_profiles.find_one({'userId':current_user['id']},{'_id':0});
    if not p: raise HTTPException(status_code=404,detail='Profile not found. Complete onboarding first.')
    return CreatorProfileFull(**p)
@creator_router.post('/subscription/toggle')
async def toggle_creator_visibility(visible: bool=Query(...), current_user: dict=Depends(get_current_user)):
    if current_user['role']!='creator': raise HTTPException(status_code=403,detail='Only creators can toggle visibility')
    await db.creator_profiles.update_one({'userId':current_user['id']},{'$set':{'isVisible':visible,'subscriptionActive':visible,'updatedAt':datetime.now(timezone.utc).isoformat()}}); return {'success':True,'isVisible':visible}

@business_router.post('/profile', response_model=BrandProfileFull)
async def create_brand_profile(profile: BrandProfileCreate, current_user: dict=Depends(get_current_user)):
    if current_user['role']!='business': raise HTTPException(status_code=403,detail='Only brands can create brand profiles')
    existing=await db.brand_profiles.find_one({'userId':current_user['id']}); now=datetime.now(timezone.utc).isoformat(); profile_id=existing['id'] if existing else str(uuid.uuid4())
    doc={'id':profile_id,'userId':current_user['id'],'brandName':profile.brandName,'industry':profile.industry or '','bio':profile.bio or '','location':profile.location or '','deliverables':profile.deliverables or '','budgetRange':profile.budgetRange or '','barterEnabled':profile.barterEnabled if profile.barterEnabled is not None else True,'paidCollabsEnabled':profile.paidCollabsEnabled if profile.paidCollabsEnabled is not None else True,'brandRequirements':profile.brandRequirements or '','instagramVerified':current_user.get('instagramVerified',False),'instagramUserId':current_user.get('instagramUserId'),'instagramUsername':current_user.get('instagramUsername'),'profilePhotoUrl':profile.profilePhotoUrl or '','createdAt':existing.get('createdAt',now) if existing else now,'updatedAt':now}
    if existing: await db.brand_profiles.update_one({'id':profile_id},{'$set':doc})
    else: await db.brand_profiles.insert_one(doc)
    await db.users.update_one({'id':current_user['id']},{'$set':{'hasCompletedOnboarding':True}}); return BrandProfileFull(**doc)
@business_router.get('/profile', response_model=BrandProfileFull)
async def get_brand_profile(current_user: dict=Depends(get_current_user)):
    if current_user['role']!='business': raise HTTPException(status_code=403,detail='Only brands can access this')
    p=await db.brand_profiles.find_one({'userId':current_user['id']},{'_id':0});
    if not p: raise HTTPException(status_code=404,detail='Profile not found. Complete onboarding first.')
    return BrandProfileFull(**p)

@marketplace_router.get('/creators', response_model=List[CreatorDiscovery])
async def discover_creators(niche: Optional[str]=Query(None),language: Optional[str]=Query(None),contentType: Optional[str]=Query(None),minPrice: Optional[float]=Query(None),maxPrice: Optional[float]=Query(None),barterOnly: Optional[bool]=Query(None),current_user: dict=Depends(get_current_user)):
    query={'instagramVerified':True,'isBlacklisted':{'$ne':True},'isVisible':{'$ne':False}}; 
    if niche: query['$or']=[{'niche':niche},{'niches':niche}]
    if language: query['language']=language
    if contentType: query['contentType']=contentType
    if barterOnly: query['barterEnabled']=True
    creators=await db.creator_profiles.find(query,{'_id':0}).to_list(100)
    if minPrice is not None: creators=[c for c in creators if c.get('reelPrice',0)>=minPrice]
    if maxPrice is not None: creators=[c for c in creators if c.get('reelPrice',0)<=maxPrice]
    return [CreatorDiscovery(id=c['id'],niche=c.get('niche',''),language=c.get('language','English'),contentType=c.get('contentType',''),niches=c.get('niches',[]),reelPrice=c.get('reelPrice',0),storyPrice=c.get('storyPrice',0),postPrice=c.get('postPrice',0),engagementRate=c.get('engagementRate',0),paidCollabsEnabled=c.get('paidCollabsEnabled',True),barterEnabled=c.get('barterEnabled',True),location=c.get('location','')) for c in creators]
@marketplace_router.get('/brands', response_model=List[BrandDiscovery])
async def discover_brands(industry: Optional[str]=Query(None),location: Optional[str]=Query(None),barterOnly: Optional[bool]=Query(None),current_user: dict=Depends(get_current_user)):
    query={'instagramVerified':True};
    if industry: query['industry']=industry
    if location: query['location']={'$regex':location,'$options':'i'}
    if barterOnly: query['barterEnabled']=True
    brands=await db.brand_profiles.find(query,{'_id':0}).to_list(100)
    return [BrandDiscovery(id=b['id'],industry=b.get('industry',''),location=b.get('location',''),deliverables=b.get('deliverables',''),budgetRange=b.get('budgetRange',''),barterEnabled=b.get('barterEnabled',True),paidCollabsEnabled=b.get('paidCollabsEnabled',True),brandRequirements=b.get('brandRequirements','')) for b in brands]

def mask_campaign_identity(campaign: dict, current_user_id: str) -> dict:
    c={**campaign}
    if not c.get('identityUnlocked',False):
        if c.get('senderUserId')!=current_user_id: c['senderName']='Brand' if c.get('senderType')=='business' else 'Creator'
        if c.get('receiverUserId')!=current_user_id: c['receiverName']='Creator' if c.get('receiverType')=='creator' else 'Brand'
        c['senderInstagram']=None; c['receiverInstagram']=None
    return c

def ensure_campaign_party(campaign,current_user):
    if campaign['senderUserId']!=current_user['id'] and campaign['receiverUserId']!=current_user['id']: raise HTTPException(status_code=403,detail='Access denied')

@campaign_router.post('/', response_model=CampaignResponse, status_code=201)
async def create_campaign(campaign: CampaignCreate, current_user: dict=Depends(get_current_user)):
    now=datetime.now(timezone.utc); sender_type=current_user['role']; sender_collection='brand_profiles' if sender_type=='business' else 'creator_profiles'; sender=await db[sender_collection].find_one({'userId':current_user['id']},{'_id':0});
    if not sender: raise HTTPException(status_code=400,detail='Complete your profile first')
    receiver_collection='creator_profiles' if campaign.receiverType=='creator' else 'brand_profiles'; receiver=await db[receiver_collection].find_one({'id':campaign.receiverId},{'_id':0});
    if not receiver: raise HTTPException(status_code=404,detail='Recipient not found')
    escrow=0; commission=0; payout=0; barter_fee=0; product_value=campaign.productValue or 0
    if campaign.campaignType=='paid':
        if campaign.budget<=0: raise HTTPException(status_code=400,detail='Paid campaign budget must be greater than zero')
        escrow=round(campaign.budget,2); commission=round(escrow*PLATFORM_COMMISSION_PERCENT/100,2); payout=round(escrow-commission,2)
    else:
        if product_value<=0: raise HTTPException(status_code=400,detail='Barter value must be greater than zero')
        barter_fee=round(product_value*BARTER_FEE_PERCENT/100,2)
    sender_name=sender.get('brandName') if sender_type=='business' else sender.get('name'); receiver_name=receiver.get('name') if campaign.receiverType=='creator' else receiver.get('brandName')
    doc={'id':str(uuid.uuid4()),'senderId':sender['id'],'senderUserId':current_user['id'],'senderType':sender_type,'senderName':sender_name,'senderInstagram':sender.get('instagramUsername'),'receiverId':receiver['id'],'receiverUserId':receiver['userId'],'receiverType':campaign.receiverType,'receiverName':receiver_name,'receiverInstagram':receiver.get('instagramUsername'),'campaignType':campaign.campaignType,'deliverables':campaign.deliverables,'budget':campaign.budget or 0,'productValue':product_value,'barterFee':barter_fee,'timeline':campaign.timeline or '','brief':campaign.brief or '','barterDetails':campaign.barterDetails or '','status':'requested','paymentStatus':'pending','escrowAmount':escrow,'platformCommission':commission,'creatorPayout':payout,'identityUnlocked':False,'chatEnabled':False,'contentLink':None,'linkVerified':False,'shippingDetails':None,'productReceived':False,'createdAt':now.isoformat(),'updatedAt':now.isoformat(),'expiresAt':(now+timedelta(hours=REQUEST_EXPIRY_HOURS)).isoformat()}
    await db.campaigns.insert_one(doc); return CampaignResponse(**mask_campaign_identity(doc,current_user['id']))
@campaign_router.get('/incoming',response_model=List[CampaignResponse])
async def get_incoming_campaigns(current_user: dict=Depends(get_current_user)):
    campaigns=await db.campaigns.find({'receiverUserId':current_user['id']},{'_id':0}).sort('createdAt',-1).to_list(100); return [CampaignResponse(**mask_campaign_identity(c,current_user['id'])) for c in campaigns]
@campaign_router.get('/outgoing',response_model=List[CampaignResponse])
async def get_outgoing_campaigns(current_user: dict=Depends(get_current_user)):
    campaigns=await db.campaigns.find({'senderUserId':current_user['id']},{'_id':0}).sort('createdAt',-1).to_list(100); return [CampaignResponse(**mask_campaign_identity(c,current_user['id'])) for c in campaigns]
@campaign_router.get('/{campaign_id}',response_model=CampaignResponse)
async def get_campaign(campaign_id: str,current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    ensure_campaign_party(c,current_user); return CampaignResponse(**mask_campaign_identity(c,current_user['id']))
@campaign_router.patch('/{campaign_id}/respond')
async def respond_to_campaign(campaign_id: str,action: Literal['accept','reject']=Query(...),current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if c['receiverUserId']!=current_user['id']: raise HTTPException(status_code=403,detail='Only the receiver can respond')
    if c['status']!='requested': raise HTTPException(status_code=400,detail='Campaign already responded to')
    new_status='accepted' if action=='accept' else 'cancelled'; await db.campaigns.update_one({'id':campaign_id},{'$set':{'status':new_status,'updatedAt':datetime.now(timezone.utc).isoformat()}}); return {'message':'Request accepted. Payment is now available.' if action=='accept' else 'Request rejected.','status':new_status}

# -------- Real Razorpay payment lifecycle --------
@payment_router.post('/campaigns/{campaign_id}/order')
async def create_campaign_payment_order(campaign_id: str,current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if c['senderUserId']!=current_user['id']: raise HTTPException(status_code=403,detail='Only the sender can pay')
    if c['status']!='accepted': raise HTTPException(status_code=400,detail='Campaign must be accepted before payment')
    if c.get('paymentStatus')=='paid': raise HTTPException(status_code=400,detail='Already paid')
    amount = c['escrowAmount'] if c['campaignType']=='paid' else c['barterFee']
    if amount<=0: raise HTTPException(status_code=400,detail='No payable amount configured')
    receipt=f'orange_{campaign_id[:12]}_{int(datetime.now(timezone.utc).timestamp())}'
    rp_order=razorpay_request('POST','/orders',json={'amount':int(round(amount*100)),'currency':'INR','receipt':receipt,'notes':{'campaign_id':campaign_id,'payment_type':'escrow' if c['campaignType']=='paid' else 'barter_fee'}})
    now=datetime.now(timezone.utc).isoformat()
    await db.payments.update_many({'campaignId':campaign_id,'status':{'$in':['created','pending']}},{'$set':{'status':'superseded','updatedAt':now}})
    await db.payments.insert_one({'id':str(uuid.uuid4()),'campaignId':campaign_id,'userId':current_user['id'],'amount':amount,'amountPaise':rp_order['amount'],'paymentType':'escrow' if c['campaignType']=='paid' else 'barter_fee','status':'created','mode':'razorpay','razorpayOrderId':rp_order['id'],'createdAt':now,'updatedAt':now})
    await db.campaigns.update_one({'id':campaign_id},{'$set':{'status':'payment_pending','razorpayOrderId':rp_order['id'],'updatedAt':now}})
    return {'success':True,'keyId':RAZORPAY_KEY_ID,'orderId':rp_order['id'],'amount':rp_order['amount'],'currency':'INR','campaignId':campaign_id,'name':'Orange','description':'Orange marketplace protected payment','prefill':{'name':current_user.get('email',''),'email':current_user.get('email','')}}

@payment_router.post('/campaigns/{campaign_id}/verify')
async def verify_campaign_payment(campaign_id: str,payment: PaymentVerifyRequest,current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if c['senderUserId']!=current_user['id']: raise HTTPException(status_code=403,detail='Only the sender can verify payment')
    if not verify_razorpay_signature(payment.razorpay_order_id,payment.razorpay_payment_id,payment.razorpay_signature): raise HTTPException(status_code=400,detail='Invalid Razorpay payment signature')
    payment_record=await db.payments.find_one({'campaignId':campaign_id,'razorpayOrderId':payment.razorpay_order_id},{'_id':0});
    if not payment_record: raise HTTPException(status_code=400,detail='Payment order not recognized')
    if payment_record.get('status')=='paid': return {'success':True,'status':'paid','identityUnlocked':c.get('identityUnlocked',False),'chatEnabled':c.get('chatEnabled',False),'message':'Payment already verified'}
    rp_payment=razorpay_request('GET',f"/payments/{payment.razorpay_payment_id}")
    if rp_payment.get('order_id')!=payment.razorpay_order_id: raise HTTPException(status_code=400,detail='Payment does not belong to this order')
    if rp_payment.get('status') not in ('captured','authorized'): raise HTTPException(status_code=400,detail=f"Payment is not successful: {rp_payment.get('status')}")
    expected=int(round(payment_record['amount']*100))
    if int(rp_payment.get('amount',0))!=expected: raise HTTPException(status_code=400,detail='Payment amount mismatch')
    now=datetime.now(timezone.utc).isoformat(); is_paid=c['campaignType']=='paid'; identity=is_paid
    await db.payments.update_one({'id':payment_record['id']},{'$set':{'status':'paid','razorpayPaymentId':payment.razorpay_payment_id,'signatureVerified':True,'razorpayStatus':rp_payment.get('status'),'paidAt':now,'updatedAt':now}})
    await db.campaigns.update_one({'id':campaign_id},{'$set':{'status':'paid','paymentStatus':'paid','identityUnlocked':identity,'chatEnabled':True,'updatedAt':now,'razorpayPaymentId':payment.razorpay_payment_id,'paymentVerifiedAt':now}})
    response={'success':True,'status':'paid','chatEnabled':True,'identityUnlocked':identity,'amountPaid':payment_record['amount'],'paymentType':payment_record['paymentType'],'message':'Payment successful. Escrow is protected and chat is unlocked.' if is_paid else 'Payment successful. Barter fee is paid and chat is unlocked.'}
    if identity:
        sender_collection='brand_profiles' if c['senderType']=='business' else 'creator_profiles'; receiver_collection='creator_profiles' if c['receiverType']=='creator' else 'brand_profiles'; sp=await db[sender_collection].find_one({'id':c['senderId']},{'_id':0}); rp=await db[receiver_collection].find_one({'id':c['receiverId']},{'_id':0}); response['senderInstagram']=sp.get('instagramUsername') if sp else None; response['receiverInstagram']=rp.get('instagramUsername') if rp else None
    return response

@payment_router.post('/razorpay/webhook')
async def razorpay_webhook(request: Request):
    body=await request.body(); signature=request.headers.get('X-Razorpay-Signature','')
    if RAZORPAY_WEBHOOK_SECRET and not hmac.compare_digest(hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(),body,hashlib.sha256).hexdigest(),signature): raise HTTPException(status_code=400,detail='Invalid webhook signature')
    try: event=(await request.json()).get('event','')
    except Exception: raise HTTPException(status_code=400,detail='Invalid JSON')
    payload=(await db.razorpay_events.count_documents({'signature':signature,'event':event}))
    if payload: return {'ok':True,'duplicate':True}
    await db.razorpay_events.insert_one({'id':str(uuid.uuid4()),'event':event,'signature':signature,'receivedAt':datetime.now(timezone.utc).isoformat()})
    payment_entity=(await request.json()).get('payload',{}).get('payment',{}).get('entity',{})
    order_id=payment_entity.get('order_id')
    if order_id:
        status_map={'payment.captured':'paid','order.paid':'paid','payment.failed':'failed'}; new_status=status_map.get(event)
        if new_status:
            await db.payments.update_many({'razorpayOrderId':order_id},{'$set':{'status':new_status,'razorpayStatus':payment_entity.get('status'),'updatedAt':datetime.now(timezone.utc).isoformat()}})
    return {'ok':True}

@campaign_router.post('/{campaign_id}/pay')
async def pay_for_campaign(campaign_id: str,current_user: dict=Depends(get_current_user)):
    # Backwards-compatible endpoint: now creates a real Razorpay order instead of pretending payment happened.
    return await create_campaign_payment_order(campaign_id,current_user)

@campaign_router.post('/{campaign_id}/shipping')
async def add_shipping_details(campaign_id: str,shippingDetails: str=Query(...),current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if c['senderUserId']!=current_user['id']: raise HTTPException(status_code=403,detail='Only sender can add shipping details')
    if c['campaignType'] not in ['barter_product','barter_service']: raise HTTPException(status_code=400,detail='Shipping details only for barter collabs')
    await db.campaigns.update_one({'id':campaign_id},{'$set':{'shippingDetails':shippingDetails,'status':'in_progress','updatedAt':datetime.now(timezone.utc).isoformat()}}); return {'success':True,'message':'Shipping details added'}
@campaign_router.post('/{campaign_id}/product-received')
async def confirm_product_received(campaign_id: str,current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if c['receiverUserId']!=current_user['id']: raise HTTPException(status_code=403,detail='Only receiver can confirm receipt')
    if c['campaignType'] not in ['barter_product','barter_service']: raise HTTPException(status_code=400,detail='Product receipt only for barter collabs')
    await db.campaigns.update_one({'id':campaign_id},{'$set':{'productReceived':True,'status':'in_progress','updatedAt':datetime.now(timezone.utc).isoformat()}}); return {'success':True,'message':'Product receipt confirmed'}
@campaign_router.post('/{campaign_id}/submit-link')
async def submit_content_link(campaign_id: str,contentLink: str=Query(...),current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    is_creator=(c['receiverType']=='creator' and c['receiverUserId']==current_user['id']) or (c['senderType']=='creator' and c['senderUserId']==current_user['id'])
    if not is_creator: raise HTTPException(status_code=403,detail='Only creator can submit content link')
    if c['status'] not in ['paid','in_progress']: raise HTTPException(status_code=400,detail='Campaign must be paid/in_progress')
    if not re.match(r'^https?://',contentLink): raise HTTPException(status_code=400,detail='Please submit a valid URL')
    await db.campaigns.update_one({'id':campaign_id},{'$set':{'contentLink':contentLink,'status':'link_submitted','updatedAt':datetime.now(timezone.utc).isoformat()}}); return {'success':True,'message':'Content link submitted for verification','contentLink':contentLink}
@campaign_router.post('/{campaign_id}/verify-link')
async def verify_content_link(campaign_id: str,current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    is_brand=(c['senderType']=='business' and c['senderUserId']==current_user['id']) or (c['receiverType']=='brand' and c['receiverUserId']==current_user['id'])
    if not is_brand: raise HTTPException(status_code=403,detail='Only brand can verify link')
    if c['status']!='link_submitted' or not c.get('contentLink'): raise HTTPException(status_code=400,detail='No link to verify')
    now=datetime.now(timezone.utc).isoformat(); update={'linkVerified':True,'status':'link_verified','updatedAt':now}; response={'success':True,'message':'Link verified!','status':'link_verified','linkVerified':True,'identityUnlocked':c.get('identityUnlocked',False)}
    if c['campaignType'] in ['barter_product','barter_service'] and not c.get('identityUnlocked',False):
        update['identityUnlocked']=True; sender_collection='brand_profiles' if c['senderType']=='business' else 'creator_profiles'; receiver_collection='creator_profiles' if c['receiverType']=='creator' else 'brand_profiles'; sp=await db[sender_collection].find_one({'id':c['senderId']},{'_id':0}); rp=await db[receiver_collection].find_one({'id':c['receiverId']},{'_id':0}); response['identityUnlocked']=True; response['senderInstagram']=sp.get('instagramUsername') if sp else None; response['receiverInstagram']=rp.get('instagramUsername') if rp else None; response['message']='Link verified! Identity unlocked.'
    await db.campaigns.update_one({'id':campaign_id},{'$set':update}); return response

async def release_creator_escrow(c):
    if c.get('campaignType')!='paid': return {'released':False,'amount':0,'method':'not_applicable'}
    creator_user_id=c['receiverUserId'] if c['receiverType']=='creator' else c['senderUserId']; linked=await db.users.find_one({'id':creator_user_id},{'_id':0}); account_id=linked.get('razorpayLinkedAccountId') if linked else None; amount=c.get('creatorPayout',0)
    if not account_id: return {'released':False,'amount':amount,'method':'pending_linked_account','reason':'Creator has no Razorpay Route linked account configured.'}
    payment_id=c.get('razorpayPaymentId');
    if not payment_id: return {'released':False,'amount':amount,'method':'pending_payment'}
    transfer=razorpay_request('POST',f'/payments/{payment_id}/transfers',json={'transfers':[{'account':account_id,'amount':int(round(amount*100)),'currency':'INR','notes':{'campaign_id':c['id']},'on_hold':False}]}); return {'released':True,'amount':amount,'method':'razorpay_route','transferId':transfer.get('id') or transfer.get('items',[{}])[0].get('id')}

@campaign_router.post('/{campaign_id}/complete')
async def complete_campaign(campaign_id: str,current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    is_brand=(c['senderType']=='business' and c['senderUserId']==current_user['id']) or (c['receiverType']=='brand' and c['receiverUserId']==current_user['id'])
    if not is_brand: raise HTTPException(status_code=403,detail='Only brand can complete')
    if c['status']!='link_verified': raise HTTPException(status_code=400,detail='Link must be verified before completing')
    now=datetime.now(timezone.utc).isoformat(); payout=await release_creator_escrow(c)
    await db.campaigns.update_one({'id':campaign_id},{'$set':{'status':'completed','payoutStatus':'released' if payout.get('released') else 'pending','updatedAt':now}})
    creator_user_id=c['receiverUserId'] if c['receiverType']=='creator' else c['senderUserId']; await db.creator_profiles.update_one({'userId':creator_user_id},{'$inc':{'totalCollabs':1}})
    if payout.get('released'): await db.payouts.insert_one({'id':str(uuid.uuid4()),'campaignId':campaign_id,'creatorUserId':creator_user_id,'amount':payout['amount'],'status':'released','method':payout['method'],'transferId':payout.get('transferId'),'createdAt':now})
    return {'success':True,'message':'Campaign completed! Escrow released.' if payout.get('released') else 'Campaign completed. Creator payout is pending linked-account setup.','status':'completed','payoutAmount':payout.get('amount',0),'payoutStatus':'released' if payout.get('released') else 'pending'}

@campaign_router.post('/{campaign_id}/rate')
async def submit_rating(campaign_id: str,rating:int=Query(...,ge=1,le=5),feedback:str=Query(...,min_length=10),current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if c['status']!='completed': raise HTTPException(status_code=400,detail='Can only rate completed campaigns')
    ensure_campaign_party(c,current_user)
    if await db.ratings.find_one({'campaignId':campaign_id,'raterId':current_user['id']}): raise HTTPException(status_code=400,detail="You've already rated this campaign")
    target_id=c['receiverUserId'] if current_user['id']==c['senderUserId'] else c['senderUserId']; target_type='creator' if ((current_user['id']==c['senderUserId'] and c['receiverType']=='creator') or (current_user['id']==c['receiverUserId'] and c['senderType']=='creator')) else 'brand'; now=datetime.now(timezone.utc).isoformat()
    await db.ratings.insert_one({'id':str(uuid.uuid4()),'campaignId':campaign_id,'raterId':current_user['id'],'raterType':current_user['role'],'targetId':target_id,'targetType':target_type,'rating':rating,'feedback':feedback,'createdAt':now})
    all_ratings=await db.ratings.find({'targetId':target_id},{'_id':0}).to_list(1000); avg=sum(x['rating'] for x in all_ratings)/len(all_ratings); collection='creator_profiles' if target_type=='creator' else 'brand_profiles'; await db[collection].update_one({'userId':target_id},{'$set':{'rating':round(avg,2)}}); return {'success':True,'message':'Rating submitted!','rating':rating}
@campaign_router.post('/{campaign_id}/report')
async def report_campaign_issue(campaign_id: str,reason: str=Query(...),current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    ensure_campaign_party(c,current_user); await db.campaigns.update_one({'id':campaign_id},{'$set':{'status':'disputed','updatedAt':datetime.now(timezone.utc).isoformat()}}); report={'id':str(uuid.uuid4()),'campaignId':campaign_id,'reporterId':current_user['id'],'reason':reason,'status':'pending','createdAt':datetime.now(timezone.utc).isoformat()}; await db.reports.insert_one(report); return {'message':'Report submitted. Admin will review.','success':True,'reportId':report['id']}

@message_router.get('/{campaign_id}',response_model=List[MessageResponse])
async def get_messages(campaign_id: str,current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    ensure_campaign_party(c,current_user)
    if not c.get('chatEnabled',False): raise HTTPException(status_code=403,detail='Chat not enabled. Complete payment first.')
    return [MessageResponse(**m) for m in await db.messages.find({'campaignId':campaign_id},{'_id':0}).sort('createdAt',1).to_list(500)]
@message_router.post('/{campaign_id}',response_model=MessageResponse,status_code=201)
async def send_message(campaign_id: str,message: MessageCreate,current_user: dict=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    ensure_campaign_party(c,current_user)
    if not c.get('chatEnabled',False): raise HTTPException(status_code=403,detail='Chat not enabled. Complete payment first.')
    blocked=check_blocked_content(message.content); now=datetime.now(timezone.utc).isoformat(); doc={'id':str(uuid.uuid4()),'campaignId':campaign_id,'senderId':current_user['id'],'senderType':current_user['role'],'content':message.content if not blocked else '[Message blocked - external contact not allowed]','blocked':blocked,'createdAt':now}
    if blocked: await db.bypass_attempts.insert_one({'id':str(uuid.uuid4()),'campaignId':campaign_id,'userId':current_user['id'],'content':message.content,'createdAt':now})
    await db.messages.insert_one(doc); return MessageResponse(**doc)

@admin_router.get('/stats')
async def get_admin_stats(current_user: dict=Depends(get_current_user)):
    if not current_user.get('isAdmin',False): raise HTTPException(status_code=403,detail='Admin access required')
    return {'totalUsers':await db.users.count_documents({}),'totalCreators':await db.creator_profiles.count_documents({}),'totalBrands':await db.brand_profiles.count_documents({}),'totalCampaigns':await db.campaigns.count_documents({}),'activeCampaigns':await db.campaigns.count_documents({'status':{'$in':['requested','accepted','payment_pending','paid','in_progress','link_submitted','link_verified']}}),'completedCampaigns':await db.campaigns.count_documents({'status':'completed'}),'pendingReports':await db.reports.count_documents({'status':'pending'}),'blacklistedCreators':await db.creator_profiles.count_documents({'isBlacklisted':True}),'bypassAttempts':await db.bypass_attempts.count_documents({}),'escrowValue':(await db.campaigns.aggregate([{'$match':{'campaignType':'paid','paymentStatus':'paid','status':{'$ne':'completed'}}},{'$group':{'_id':None,'total':{'$sum':'$escrowAmount'}}}]).to_list(1))[0]['total'] if await db.campaigns.count_documents({'campaignType':'paid','paymentStatus':'paid','status':{'$ne':'completed'}}) else 0}
@admin_router.get('/reports')
async def get_reports(current_user: dict=Depends(get_current_user)):
    if not current_user.get('isAdmin',False): raise HTTPException(status_code=403,detail='Admin access required')
    return await db.reports.find({'status':'pending'},{'_id':0}).to_list(100)
@admin_router.post('/blacklist/{user_id}')
async def blacklist_user(user_id: str,reason: str=Query(...),current_user: dict=Depends(get_current_user)):
    if not current_user.get('isAdmin',False): raise HTTPException(status_code=403,detail='Admin access required')
    await db.users.update_one({'id':user_id},{'$set':{'isBlacklisted':True}}); await db.creator_profiles.update_one({'userId':user_id},{'$set':{'isBlacklisted':True}}); await db.blacklist_log.insert_one({'id':str(uuid.uuid4()),'userId':user_id,'reason':reason,'adminId':current_user['id'],'createdAt':datetime.now(timezone.utc).isoformat()}); return {'message':'User blacklisted','success':True}

api_router.include_router(auth_router); api_router.include_router(creator_router); api_router.include_router(business_router); api_router.include_router(marketplace_router); api_router.include_router(campaign_router); api_router.include_router(payment_router); api_router.include_router(message_router); api_router.include_router(admin_router); app.include_router(api_router)
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
@app.on_event('startup')
async def startup_db_client(): logger.info('Orange API started - live payment/escrow backend enabled')
@app.on_event('shutdown')
async def shutdown_db_client(): client.close()
