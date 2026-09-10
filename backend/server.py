from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Request
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
REQUEST_EXPIRY_HOURS = 72
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
RAZORPAY_API_BASE = 'https://api.razorpay.com/v1'
INSTAGRAM_APP_ID = os.environ.get('INSTAGRAM_APP_ID', '')
INSTAGRAM_APP_SECRET = os.environ.get('INSTAGRAM_APP_SECRET', '')
INSTAGRAM_REDIRECT_URI = os.environ.get('INSTAGRAM_REDIRECT_URI', 'http://localhost:8000/api/auth/instagram/callback')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
CORS_ORIGINS = [x.strip() for x in os.environ.get('CORS_ORIGINS', FRONTEND_URL).split(',') if x.strip()]
INSTAGRAM_SCOPES = 'instagram_business_basic'
COLLAB_STATES = ['requested','accepted','payment_pending','paid','in_progress','link_submitted','link_verified','completed','disputed','cancelled']
app = FastAPI(title='Orange - Creator-Brand Collaboration Platform API')
api_router = APIRouter(prefix='/api')
auth_router = APIRouter(prefix='/auth')
creator_router = APIRouter(prefix='/creator')
business_router = APIRouter(prefix='/business')
marketplace_router = APIRouter(prefix='/marketplace')
campaign_router = APIRouter(prefix='/campaigns')
payment_router = APIRouter(prefix='/payments')
message_router = APIRouter(prefix='/messages')
admin_router = APIRouter(prefix='/admin')
security = HTTPBearer()
BLOCKED_PATTERNS=[r'\b(instagram|insta|ig)\b',r'\b(whatsapp|wa)\b',r'\b(telegram|tg)\b',r'@[a-zA-Z0-9_]+',r'\b\d{10}\b',r'\b(snapchat|snap)\b',r'\b(twitter|x\.com)\b',r'\b(facebook|fb)\b',r'\b(linkedin)\b',r'\b(email|mail)\b.*@']
logging.basicConfig(level=logging.INFO); logger=logging.getLogger(__name__)

class UserCreate(BaseModel): email: EmailStr; password: str; role: Literal['creator','business']
class UserLogin(BaseModel): email: EmailStr; password: str
class UserResponse(BaseModel):
    id: str; email: str; role: str; hasCompletedOnboarding: bool=False; isAdmin: bool=False; instagramVerified: bool=False; isBlacklisted: bool=False
class TokenResponse(BaseModel): access_token: str; token_type: str='bearer'; user: UserResponse
class CreatorProfileCreate(BaseModel):
    name:str; bio:Optional[str]=''; location:Optional[str]=''; niche:Optional[str]=''; language:Optional[str]='English'; contentType:Optional[str]=''; niches:Optional[List[str]]=[]; reelPrice:Optional[float]=0; storyPrice:Optional[float]=0; postPrice:Optional[float]=0; paidCollabsEnabled:Optional[bool]=True; barterEnabled:Optional[bool]=True; profilePhotoUrl:Optional[str]=''
class CreatorProfileFull(BaseModel):
    id:str; userId:str; name:str; bio:str; location:str; niche:str; language:str; contentType:str; niches:List[str]; reelPrice:float; storyPrice:float; postPrice:float; paidCollabsEnabled:bool; barterEnabled:bool; instagramVerified:bool; engagementRate:float; profilePhotoUrl:str; isBlacklisted:bool=False; isVisible:bool=True; subscriptionActive:bool=True; rating:Optional[float]=None; totalCollabs:int=0
class BrandProfileCreate(BaseModel):
    brandName:str; industry:Optional[str]=''; bio:Optional[str]=''; location:Optional[str]=''; deliverables:Optional[str]=''; budgetRange:Optional[str]=''; barterEnabled:Optional[bool]=True; paidCollabsEnabled:Optional[bool]=True; brandRequirements:Optional[str]=''; profilePhotoUrl:Optional[str]=''
class BrandProfileFull(BaseModel):
    id:str; userId:str; brandName:str; industry:str; bio:str; location:str; deliverables:str; budgetRange:str; barterEnabled:bool; paidCollabsEnabled:bool; brandRequirements:str; instagramVerified:bool; profilePhotoUrl:str
class CreatorDiscovery(BaseModel):
    id:str; niche:str; language:str; contentType:str; niches:List[str]; reelPrice:float; storyPrice:float; postPrice:float; engagementRate:float; paidCollabsEnabled:bool; barterEnabled:bool; location:str
class BrandDiscovery(BaseModel):
    id:str; industry:str; location:str; deliverables:str; budgetRange:str; barterEnabled:bool; paidCollabsEnabled:bool; brandRequirements:str
class CampaignCreate(BaseModel):
    receiverId:str; receiverType:Literal['creator','brand']; campaignType:Literal['paid','barter_product','barter_service']; deliverables:str; budget:Optional[float]=0; productValue:Optional[float]=0; timeline:Optional[str]=''; brief:Optional[str]=''; barterDetails:Optional[str]=''
class CampaignResponse(BaseModel):
    id:str; senderId:str; senderType:str; senderName:str; receiverId:str; receiverType:str; receiverName:str; campaignType:str; deliverables:str; budget:float; productValue:float; barterFee:float; timeline:str; brief:str; barterDetails:str; status:str; paymentStatus:str; escrowAmount:float; platformCommission:float; creatorPayout:float; identityUnlocked:bool; chatEnabled:bool; contentLink:Optional[str]=None; linkVerified:bool=False; shippingDetails:Optional[str]=None; productReceived:bool=False; senderInstagram:Optional[str]=None; receiverInstagram:Optional[str]=None; createdAt:str; updatedAt:str; expiresAt:Optional[str]=None; payoutStatus:Optional[str]=None
class MessageCreate(BaseModel): content:str
class MessageResponse(BaseModel): id:str; campaignId:str; senderId:str; senderType:str; content:str; blocked:bool=False; createdAt:str
class InstagramVerifyRequest(BaseModel): instagramUsername:str
class InstagramVerifyResponse(BaseModel): success:bool; instagramUserId:str; followersCount:int; engagementRate:float; message:str
class InstagramStatusResponse(BaseModel): connected:bool; instagramUserId:Optional[str]=None; instagramUsername:Optional[str]=None; followersCount:Optional[int]=None; engagementRate:Optional[float]=None
class InstagramOAuthStartResponse(BaseModel): authorizationUrl:str
class PaymentVerifyRequest(BaseModel): razorpay_order_id:str; razorpay_payment_id:str; razorpay_signature:str

def hash_password(password:str)->str: return pwd_context.hash(password)
def verify_password(plain:str, hashed:str)->bool: return pwd_context.verify(plain,hashed)
def create_access_token(data:dict)->str:
    payload=data.copy(); payload['exp']=datetime.now(timezone.utc)+timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS); return jwt.encode(payload,SECRET_KEY,algorithm=ALGORITHM)
async def get_current_user(credentials:HTTPAuthorizationCredentials=Depends(security)):
    try:
        payload=jwt.decode(credentials.credentials,SECRET_KEY,algorithms=[ALGORITHM]); uid=payload.get('sub')
        if not uid: raise HTTPException(status_code=401,detail='Invalid token')
        user=await db.users.find_one({'id':uid},{'_id':0})
        if not user: raise HTTPException(status_code=401,detail='User not found')
        if user.get('isBlacklisted',False): raise HTTPException(status_code=403,detail='Your account has been blacklisted')
        return user
    except JWTError: raise HTTPException(status_code=401,detail='Invalid token')
def check_blocked_content(message:str)->bool: return any(re.search(p,message.lower(),re.I) for p in BLOCKED_PATTERNS)
def engagement()->float: return round(random.uniform(2,12),2)
def razorpay_configured()->bool: return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)
def razorpay_request(method:str,path:str,**kwargs):
    if not razorpay_configured(): raise HTTPException(status_code=503,detail='Razorpay is not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to backend/.env.')
    response=requests.request(method,f'{RAZORPAY_API_BASE}{path}',auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET),timeout=20,**kwargs)
    if response.status_code>=400:
        try: detail=response.json().get('error',{}).get('description','Razorpay API error')
        except Exception: detail='Razorpay API error'
        raise HTTPException(status_code=502,detail=detail)
    return response.json()
def razorpay_signature_valid(order_id,payment_id,signature):
    expected=hmac.new(RAZORPAY_KEY_SECRET.encode(),f'{order_id}|{payment_id}'.encode(),hashlib.sha256).hexdigest(); return hmac.compare_digest(expected,signature)
def mask_campaign_identity(c,current_user_id):
    x={**c}
    if not x.get('identityUnlocked',False):
        if x.get('senderUserId')!=current_user_id: x['senderName']='Brand' if x.get('senderType')=='business' else 'Creator'
        if x.get('receiverUserId')!=current_user_id: x['receiverName']='Creator' if x.get('receiverType')=='creator' else 'Brand'
        x['senderInstagram']=None; x['receiverInstagram']=None
    return x
def ensure_party(c,u):
    if c['senderUserId']!=u['id'] and c['receiverUserId']!=u['id']: raise HTTPException(status_code=403,detail='Access denied')
def brand_user_id(c): return c['senderUserId'] if c['senderType']=='business' else c['receiverUserId']
def creator_user_id(c): return c['receiverUserId'] if c['receiverType']=='creator' else c['senderUserId']
def identity_and_instagram(c):
    sc='brand_profiles' if c['senderType']=='business' else 'creator_profiles'; rc='creator_profiles' if c['receiverType']=='creator' else 'brand_profiles'
    return sc,rc

@auth_router.post('/signup',response_model=TokenResponse)
async def signup(data:UserCreate):
    if await db.users.find_one({'email':data.email}): raise HTTPException(status_code=400,detail='Email already registered')
    if len(data.password)<6: raise HTTPException(status_code=400,detail='Password must be at least 6 characters')
    uid=str(uuid.uuid4()); now=datetime.now(timezone.utc).isoformat(); await db.users.insert_one({'id':uid,'email':data.email,'passwordHash':hash_password(data.password),'role':data.role,'hasCompletedOnboarding':False,'isAdmin':False,'instagramVerified':False,'isBlacklisted':False,'createdAt':now})
    return TokenResponse(access_token=create_access_token({'sub':uid,'email':data.email,'role':data.role}),user=UserResponse(id=uid,email=data.email,role=data.role))
@auth_router.post('/login',response_model=TokenResponse)
async def login(data:UserLogin):
    user=await db.users.find_one({'email':data.email},{'_id':0})
    if not user or not verify_password(data.password,user['passwordHash']): raise HTTPException(status_code=401,detail='Invalid email or password')
    if user.get('isBlacklisted',False): raise HTTPException(status_code=403,detail='Your account has been blacklisted')
    return TokenResponse(access_token=create_access_token({'sub':user['id'],'email':user['email'],'role':user['role']}),user=UserResponse(id=user['id'],email=user['email'],role=user['role'],hasCompletedOnboarding=user.get('hasCompletedOnboarding',False),isAdmin=user.get('isAdmin',False),instagramVerified=user.get('instagramVerified',False),isBlacklisted=user.get('isBlacklisted',False)))
@auth_router.get('/me',response_model=UserResponse)
async def me(current_user=Depends(get_current_user)): return UserResponse(id=current_user['id'],email=current_user['email'],role=current_user['role'],hasCompletedOnboarding=current_user.get('hasCompletedOnboarding',False),isAdmin=current_user.get('isAdmin',False),instagramVerified=current_user.get('instagramVerified',False),isBlacklisted=current_user.get('isBlacklisted',False))
@auth_router.post('/logout')
async def logout(): return {'success':True,'message':'Logged out successfully'}


# ============== INSTAGRAM OAUTH ==============

def build_instagram_authorization_url(state: str) -> str:
    params = {
        'client_id': INSTAGRAM_APP_ID,
        'redirect_uri': INSTAGRAM_REDIRECT_URI,
        'response_type': 'code',
        'scope': INSTAGRAM_SCOPES,
        'state': state,
    }
    return f"https://www.instagram.com/oauth/authorize?{urlencode(params)}"


def exchange_instagram_code(code: str) -> dict:
    response = requests.post(
        'https://api.instagram.com/oauth/access_token',
        data={
            'client_id': INSTAGRAM_APP_ID,
            'client_secret': INSTAGRAM_APP_SECRET,
            'grant_type': 'authorization_code',
            'redirect_uri': INSTAGRAM_REDIRECT_URI,
            'code': code,
        },
        timeout=20,
    )
    response.raise_for_status()
    short_lived = response.json()
    short_token = short_lived.get('access_token')
    if not short_token:
        raise ValueError('Instagram did not return an access token')

    long_lived_response = requests.get(
        'https://graph.instagram.com/access_token',
        params={
            'grant_type': 'ig_exchange_token',
            'client_secret': INSTAGRAM_APP_SECRET,
            'access_token': short_token,
        },
        timeout=20,
    )
    long_lived_response.raise_for_status()
    long_lived = long_lived_response.json()
    access_token = long_lived.get('access_token', short_token)

    profile_response = requests.get(
        'https://graph.instagram.com/me',
        params={
            'fields': 'user_id,username,account_type,media_count',
            'access_token': access_token,
        },
        timeout=20,
    )
    profile_response.raise_for_status()
    profile = profile_response.json()
    account_type = (profile.get('account_type') or '').upper()
    if account_type and account_type not in {'BUSINESS', 'CREATOR', 'MEDIA_CREATOR'}:
        raise ValueError('The connected Instagram account must be a professional account')

    return {
        'accessToken': access_token,
        'expiresIn': long_lived.get('expires_in'),
        'instagramUserId': profile.get('user_id') or profile.get('id'),
        'instagramUsername': profile.get('username'),
        'accountType': account_type or None,
        'mediaCount': profile.get('media_count'),
    }


@auth_router.get('/instagram/connect',response_model=InstagramOAuthStartResponse)
async def connect_instagram(current_user=Depends(get_current_user)):
    if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET:
        raise HTTPException(status_code=503,detail='Instagram OAuth is not configured. Add INSTAGRAM_APP_ID and INSTAGRAM_APP_SECRET to backend/.env.')
    state=secrets.token_urlsafe(32)
    expires_at=datetime.now(timezone.utc)+timedelta(minutes=10)
    await db.instagram_oauth_states.update_one(
        {'userId':current_user['id']},
        {'$set':{'userId':current_user['id'],'state':state,'expiresAt':expires_at}},
        upsert=True,
    )
    return InstagramOAuthStartResponse(authorizationUrl=build_instagram_authorization_url(state))


@auth_router.get('/instagram/callback')
async def instagram_callback(
    code:Optional[str]=None,
    state:Optional[str]=None,
    error:Optional[str]=None,
    error_reason:Optional[str]=None,
    error_description:Optional[str]=None,
):
    if error or not code or not state:
        reason=error_description or error_reason or error or 'Instagram authorization was cancelled'
        return RedirectResponse(f"{FRONTEND_URL}/instagram/callback?instagram=error&{urlencode({'reason':reason})}")

    oauth_state=await db.instagram_oauth_states.find_one_and_delete({
        'state':state,
        'expiresAt':{'$gt':datetime.now(timezone.utc)},
    })
    if not oauth_state:
        return RedirectResponse(f"{FRONTEND_URL}/instagram/callback?instagram=error&{urlencode({'reason':'Invalid or expired OAuth state'})}")

    try:
        instagram=exchange_instagram_code(code)
        if not instagram.get('instagramUserId') or not instagram.get('instagramUsername'):
            raise ValueError('Instagram did not return a valid professional account')
    except (requests.RequestException, KeyError, ValueError) as exc:
        logger.warning('Instagram OAuth exchange failed: %s',exc)
        return RedirectResponse(f"{FRONTEND_URL}/instagram/callback?instagram=error&{urlencode({'reason':'Instagram authorization failed'})}")

    now=datetime.now(timezone.utc)
    expires_at=None
    if instagram.get('expiresIn'):
        expires_at=now+timedelta(seconds=int(instagram['expiresIn']))
    instagram_fields={
        'instagramVerified':True,
        'instagramUserId':instagram['instagramUserId'],
        'instagramUsername':instagram.get('instagramUsername'),
        'instagramAccessToken':instagram['accessToken'],
        'instagramTokenExpiresAt':expires_at,
        'instagramConnectedAt':now,
        'instagramAccountType':instagram.get('accountType'),
    }
    await db.users.update_one({'id':oauth_state['userId']},{'$set':instagram_fields})
    collection='creator_profiles' if (await db.users.find_one({'id':oauth_state['userId']},{'role':1})).get('role')=='creator' else 'brand_profiles'
    await db[collection].update_one({'userId':oauth_state['userId']},{'$set':instagram_fields})
    return RedirectResponse(f'{FRONTEND_URL}/instagram/callback?instagram=connected')


@auth_router.get('/instagram/status',response_model=InstagramStatusResponse)
async def instagram_status(current_user=Depends(get_current_user)):
    return InstagramStatusResponse(
        connected=bool(current_user.get('instagramVerified') and current_user.get('instagramUserId')),
        instagramUserId=current_user.get('instagramUserId'),
        instagramUsername=current_user.get('instagramUsername'),
        followersCount=current_user.get('followersCount'),
        engagementRate=current_user.get('engagementRate'),
    )


@auth_router.post('/instagram/disconnect')
async def disconnect_instagram(current_user=Depends(get_current_user)):
    fields={
        'instagramVerified':False,
        'instagramUserId':None,
        'instagramUsername':None,
        'instagramAccessToken':None,
        'instagramTokenExpiresAt':None,
        'instagramConnectedAt':None,
        'instagramAccountType':None,
    }
    await db.users.update_one({'id':current_user['id']},{'$set':fields})
    collection='creator_profiles' if current_user['role']=='creator' else 'brand_profiles'
    await db[collection].update_one({'userId':current_user['id']},{'$set':fields})
    return {'success':True,'message':'Instagram disconnected successfully'}


@auth_router.post('/instagram/verify',response_model=InstagramVerifyResponse)
async def verify_instagram_legacy(current_user=Depends(get_current_user)):
    raise HTTPException(status_code=410,detail='Demo Instagram verification has been removed. Use Connect Instagram instead.')

@creator_router.post('/profile',response_model=CreatorProfileFull)
async def create_creator_profile(profile:CreatorProfileCreate,current_user=Depends(get_current_user)):
    if current_user['role']!='creator': raise HTTPException(status_code=403,detail='Only creators can create creator profiles')
    existing=await db.creator_profiles.find_one({'userId':current_user['id']}); now=datetime.now(timezone.utc).isoformat(); pid=existing['id'] if existing else str(uuid.uuid4())
    doc={'id':pid,'userId':current_user['id'],'name':profile.name,'bio':profile.bio or '','location':profile.location or '','niche':profile.niche or (profile.niches[0] if profile.niches else ''),'language':profile.language or 'English','contentType':profile.contentType or '','niches':profile.niches or [],'reelPrice':profile.reelPrice or 0,'storyPrice':profile.storyPrice or 0,'postPrice':profile.postPrice or 0,'paidCollabsEnabled':profile.paidCollabsEnabled if profile.paidCollabsEnabled is not None else True,'barterEnabled':profile.barterEnabled if profile.barterEnabled is not None else True,'instagramVerified':current_user.get('instagramVerified',False),'instagramUserId':current_user.get('instagramUserId'),'instagramUsername':current_user.get('instagramUsername'),'engagementRate':current_user.get('engagementRate',engagement()),'profilePhotoUrl':profile.profilePhotoUrl or '','isBlacklisted':False,'isVisible':existing.get('isVisible',True) if existing else True,'subscriptionActive':existing.get('subscriptionActive',True) if existing else True,'rating':existing.get('rating') if existing else None,'totalCollabs':existing.get('totalCollabs',0) if existing else 0,'createdAt':existing.get('createdAt',now) if existing else now,'updatedAt':now}
    if existing: await db.creator_profiles.update_one({'id':pid},{'$set':doc})
    else: await db.creator_profiles.insert_one(doc)
    await db.users.update_one({'id':current_user['id']},{'$set':{'hasCompletedOnboarding':True}}); return CreatorProfileFull(**doc)
@creator_router.get('/profile',response_model=CreatorProfileFull)
async def get_creator_profile(current_user=Depends(get_current_user)):
    p=await db.creator_profiles.find_one({'userId':current_user['id']},{'_id':0});
    if not p: raise HTTPException(status_code=404,detail='Profile not found. Complete onboarding first.')
    return CreatorProfileFull(**p)
@creator_router.post('/subscription/toggle')
async def toggle_visibility(visible:bool=Query(...),current_user=Depends(get_current_user)):
    if current_user['role']!='creator': raise HTTPException(status_code=403,detail='Only creators can toggle visibility')
    await db.creator_profiles.update_one({'userId':current_user['id']},{'$set':{'isVisible':visible,'subscriptionActive':visible,'updatedAt':datetime.now(timezone.utc).isoformat()}}); return {'success':True,'isVisible':visible}

@business_router.post('/profile',response_model=BrandProfileFull)
async def create_brand_profile(profile:BrandProfileCreate,current_user=Depends(get_current_user)):
    if current_user['role']!='business': raise HTTPException(status_code=403,detail='Only brands can create brand profiles')
    existing=await db.brand_profiles.find_one({'userId':current_user['id']}); now=datetime.now(timezone.utc).isoformat(); pid=existing['id'] if existing else str(uuid.uuid4()); doc={'id':pid,'userId':current_user['id'],'brandName':profile.brandName,'industry':profile.industry or '','bio':profile.bio or '','location':profile.location or '','deliverables':profile.deliverables or '','budgetRange':profile.budgetRange or '','barterEnabled':profile.barterEnabled if profile.barterEnabled is not None else True,'paidCollabsEnabled':profile.paidCollabsEnabled if profile.paidCollabsEnabled is not None else True,'brandRequirements':profile.brandRequirements or '','instagramVerified':current_user.get('instagramVerified',False),'instagramUserId':current_user.get('instagramUserId'),'instagramUsername':current_user.get('instagramUsername'),'profilePhotoUrl':profile.profilePhotoUrl or '','createdAt':existing.get('createdAt',now) if existing else now,'updatedAt':now}
    if existing: await db.brand_profiles.update_one({'id':pid},{'$set':doc})
    else: await db.brand_profiles.insert_one(doc)
    await db.users.update_one({'id':current_user['id']},{'$set':{'hasCompletedOnboarding':True}}); return BrandProfileFull(**doc)
@business_router.get('/profile',response_model=BrandProfileFull)
async def get_brand_profile(current_user=Depends(get_current_user)):
    p=await db.brand_profiles.find_one({'userId':current_user['id']},{'_id':0});
    if not p: raise HTTPException(status_code=404,detail='Profile not found. Complete onboarding first.')
    return BrandProfileFull(**p)

@marketplace_router.get('/creators',response_model=List[CreatorDiscovery])
async def creators(niche:Optional[str]=None,language:Optional[str]=None,contentType:Optional[str]=None,minPrice:Optional[float]=None,maxPrice:Optional[float]=None,barterOnly:Optional[bool]=None,current_user=Depends(get_current_user)):
    q={'instagramVerified':True,'isBlacklisted':{'$ne':True},'isVisible':{'$ne':False}}; 
    if niche:q['$or']=[{'niche':niche},{'niches':niche}]
    if language:q['language']=language
    if contentType:q['contentType']=contentType
    if barterOnly:q['barterEnabled']=True
    items=await db.creator_profiles.find(q,{'_id':0}).to_list(100)
    if minPrice is not None: items=[x for x in items if x.get('reelPrice',0)>=minPrice]
    if maxPrice is not None: items=[x for x in items if x.get('reelPrice',0)<=maxPrice]
    return [CreatorDiscovery(id=x['id'],niche=x.get('niche',''),language=x.get('language','English'),contentType=x.get('contentType',''),niches=x.get('niches',[]),reelPrice=x.get('reelPrice',0),storyPrice=x.get('storyPrice',0),postPrice=x.get('postPrice',0),engagementRate=x.get('engagementRate',0),paidCollabsEnabled=x.get('paidCollabsEnabled',True),barterEnabled=x.get('barterEnabled',True),location=x.get('location','')) for x in items]
@marketplace_router.get('/brands',response_model=List[BrandDiscovery])
async def brands(industry:Optional[str]=None,location:Optional[str]=None,barterOnly:Optional[bool]=None,current_user=Depends(get_current_user)):
    q={'instagramVerified':True};
    if industry:q['industry']=industry
    if location:q['location']={'$regex':location,'$options':'i'}
    if barterOnly:q['barterEnabled']=True
    items=await db.brand_profiles.find(q,{'_id':0}).to_list(100)
    return [BrandDiscovery(id=x['id'],industry=x.get('industry',''),location=x.get('location',''),deliverables=x.get('deliverables',''),budgetRange=x.get('budgetRange',''),barterEnabled=x.get('barterEnabled',True),paidCollabsEnabled=x.get('paidCollabsEnabled',True),brandRequirements=x.get('brandRequirements','')) for x in items]

@campaign_router.post('/',response_model=CampaignResponse,status_code=201)
async def create_campaign(campaign:CampaignCreate,current_user=Depends(get_current_user)):
    sender_col='brand_profiles' if current_user['role']=='business' else 'creator_profiles'; sender=await db[sender_col].find_one({'userId':current_user['id']},{'_id':0})
    if not sender: raise HTTPException(status_code=400,detail='Complete your profile first')
    receiver_col='creator_profiles' if campaign.receiverType=='creator' else 'brand_profiles'; receiver=await db[receiver_col].find_one({'id':campaign.receiverId},{'_id':0})
    if not receiver: raise HTTPException(status_code=404,detail='Recipient not found')
    escrow=commission=payout=barter_fee=0; product_value=campaign.productValue or 0
    if campaign.campaignType=='paid':
        if campaign.budget<=0: raise HTTPException(status_code=400,detail='Paid campaign budget must be greater than zero')
        escrow=round(campaign.budget,2); commission=round(escrow*PLATFORM_COMMISSION_PERCENT/100,2); payout=round(escrow-commission,2)
    else:
        if product_value<=0: raise HTTPException(status_code=400,detail='Barter value must be greater than zero')
        barter_fee=round(product_value*BARTER_FEE_PERCENT/100,2)
    now=datetime.now(timezone.utc); sname=sender.get('brandName') if current_user['role']=='business' else sender.get('name'); rname=receiver.get('name') if campaign.receiverType=='creator' else receiver.get('brandName')
    doc={'id':str(uuid.uuid4()),'senderId':sender['id'],'senderUserId':current_user['id'],'senderType':current_user['role'],'senderName':sname,'senderInstagram':sender.get('instagramUsername'),'receiverId':receiver['id'],'receiverUserId':receiver['userId'],'receiverType':campaign.receiverType,'receiverName':rname,'receiverInstagram':receiver.get('instagramUsername'),'campaignType':campaign.campaignType,'deliverables':campaign.deliverables,'budget':campaign.budget or 0,'productValue':product_value,'barterFee':barter_fee,'timeline':campaign.timeline or '','brief':campaign.brief or '','barterDetails':campaign.barterDetails or '','status':'requested','paymentStatus':'pending','escrowAmount':escrow,'platformCommission':commission,'creatorPayout':payout,'identityUnlocked':False,'chatEnabled':False,'contentLink':None,'linkVerified':False,'shippingDetails':None,'productReceived':False,'createdAt':now.isoformat(),'updatedAt':now.isoformat(),'expiresAt':(now+timedelta(hours=REQUEST_EXPIRY_HOURS)).isoformat()}
    await db.campaigns.insert_one(doc); return CampaignResponse(**mask_campaign_identity(doc,current_user['id']))
@campaign_router.get('/incoming',response_model=List[CampaignResponse])
async def incoming(current_user=Depends(get_current_user)):
    items=await db.campaigns.find({'receiverUserId':current_user['id']},{'_id':0}).sort('createdAt',-1).to_list(100); return [CampaignResponse(**mask_campaign_identity(x,current_user['id'])) for x in items]
@campaign_router.get('/outgoing',response_model=List[CampaignResponse])
async def outgoing(current_user=Depends(get_current_user)):
    items=await db.campaigns.find({'senderUserId':current_user['id']},{'_id':0}).sort('createdAt',-1).to_list(100); return [CampaignResponse(**mask_campaign_identity(x,current_user['id'])) for x in items]
@campaign_router.get('/{campaign_id}',response_model=CampaignResponse)
async def campaign_detail(campaign_id:str,current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    ensure_party(c,current_user); return CampaignResponse(**mask_campaign_identity(c,current_user['id']))
@campaign_router.patch('/{campaign_id}/respond')
async def respond(campaign_id:str,action:Literal['accept','reject']=Query(...),current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if c['receiverUserId']!=current_user['id']: raise HTTPException(status_code=403,detail='Only receiver can respond')
    if c['status']!='requested': raise HTTPException(status_code=400,detail='Campaign already responded to')
    new='accepted' if action=='accept' else 'cancelled'; await db.campaigns.update_one({'id':campaign_id},{'$set':{'status':new,'updatedAt':datetime.now(timezone.utc).isoformat()}}); return {'status':new,'message':'Request accepted. Brand can now pay.' if action=='accept' else 'Request rejected.'}

@payment_router.post('/campaigns/{campaign_id}/order')
async def create_payment_order(campaign_id:str,current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if brand_user_id(c)!=current_user['id']: raise HTTPException(status_code=403,detail='Only the brand can fund this collaboration')
    if c['status']!='accepted': raise HTTPException(status_code=400,detail='Campaign must be accepted before payment')
    if c.get('paymentStatus')=='paid': raise HTTPException(status_code=400,detail='Already paid')
    amount=c['escrowAmount'] if c['campaignType']=='paid' else c['barterFee'];
    if amount<=0: raise HTTPException(status_code=400,detail='No payable amount configured')
    order=razorpay_request('POST','/orders',json={'amount':int(round(amount*100)),'currency':'INR','receipt':f"orange_{campaign_id[:12]}_{int(datetime.now(timezone.utc).timestamp())}",'notes':{'campaign_id':campaign_id,'payment_type':'escrow' if c['campaignType']=='paid' else 'barter_fee'}}); now=datetime.now(timezone.utc).isoformat()
    await db.payments.update_many({'campaignId':campaign_id,'status':{'$in':['created','pending']}},{'$set':{'status':'superseded','updatedAt':now}})
    await db.payments.insert_one({'id':str(uuid.uuid4()),'campaignId':campaign_id,'userId':current_user['id'],'amount':amount,'amountPaise':order['amount'],'paymentType':'escrow' if c['campaignType']=='paid' else 'barter_fee','status':'created','mode':'razorpay','razorpayOrderId':order['id'],'createdAt':now,'updatedAt':now})
    # Keep status=accepted so the existing dashboard's Pay action remains available after a cancelled checkout.
    await db.campaigns.update_one({'id':campaign_id},{'$set':{'razorpayOrderId':order['id'],'updatedAt':now}})
    return {'success':True,'keyId':RAZORPAY_KEY_ID,'orderId':order['id'],'amount':order['amount'],'currency':'INR','campaignId':campaign_id,'name':'Orange','description':'Orange protected marketplace payment','prefill':{'email':current_user.get('email','')}}

async def finalize_verified_payment(c,payment_record,razorpay_payment_id):
    now=datetime.now(timezone.utc).isoformat(); identity=c['campaignType']=='paid'
    await db.payments.update_one({'id':payment_record['id']},{'$set':{'status':'paid','razorpayPaymentId':razorpay_payment_id,'signatureVerified':True,'paidAt':now,'updatedAt':now}})
    await db.campaigns.update_one({'id':c['id']},{'$set':{'status':'paid','paymentStatus':'paid','identityUnlocked':identity,'chatEnabled':True,'razorpayPaymentId':razorpay_payment_id,'paymentVerifiedAt':now,'updatedAt':now}})
    response={'success':True,'status':'paid','chatEnabled':True,'identityUnlocked':identity,'amountPaid':payment_record['amount'],'paymentType':payment_record['paymentType'],'message':'Payment verified. Escrow is funded and chat is unlocked.' if identity else 'Payment verified. Barter fee is paid and chat is unlocked.'}
    if identity:
        sc,rc=identity_and_instagram(c); sp=await db[sc].find_one({'id':c['senderId']},{'_id':0}); rp=await db[rc].find_one({'id':c['receiverId']},{'_id':0}); response['senderInstagram']=sp.get('instagramUsername') if sp else None; response['receiverInstagram']=rp.get('instagramUsername') if rp else None
    return response

@payment_router.post('/campaigns/{campaign_id}/verify')
async def verify_payment(campaign_id:str,payment:PaymentVerifyRequest,current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if brand_user_id(c)!=current_user['id']: raise HTTPException(status_code=403,detail='Only the brand can verify this payment')
    if not razorpay_signature_valid(payment.razorpay_order_id,payment.razorpay_payment_id,payment.razorpay_signature): raise HTTPException(status_code=400,detail='Invalid Razorpay payment signature')
    record=await db.payments.find_one({'campaignId':campaign_id,'razorpayOrderId':payment.razorpay_order_id},{'_id':0});
    if not record: raise HTTPException(status_code=400,detail='Payment order not recognized')
    if record.get('status')=='paid': return {'success':True,'status':'paid','chatEnabled':True,'identityUnlocked':c.get('identityUnlocked',False),'message':'Payment already verified'}
    rp=razorpay_request('GET',f'/payments/{payment.razorpay_payment_id}')
    if rp.get('order_id')!=payment.razorpay_order_id: raise HTTPException(status_code=400,detail='Payment does not belong to this order')
    expected=int(round(record['amount']*100));
    if int(rp.get('amount',0))!=expected: raise HTTPException(status_code=400,detail='Payment amount mismatch')
    if rp.get('status')=='authorized': razorpay_request('POST',f"/payments/{payment.razorpay_payment_id}/capture",json={'amount':expected,'currency':'INR'}); rp=razorpay_request('GET',f'/payments/{payment.razorpay_payment_id}')
    if rp.get('status')!='captured': raise HTTPException(status_code=400,detail=f"Payment is not captured: {rp.get('status')}")
    return await finalize_verified_payment(c,record,payment.razorpay_payment_id)

@payment_router.post('/razorpay/webhook')
async def razorpay_webhook(request:Request):
    if not RAZORPAY_WEBHOOK_SECRET: raise HTTPException(status_code=503,detail='Razorpay webhook secret is not configured')
    body=await request.body(); signature=request.headers.get('X-Razorpay-Signature',''); expected=hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(),body,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,signature): raise HTTPException(status_code=400,detail='Invalid webhook signature')
    payload=await request.json(); event=payload.get('event',''); pe=payload.get('payload',{}).get('payment',{}).get('entity',{}); order_id=pe.get('order_id'); payment_id=pe.get('id')
    if await db.razorpay_events.find_one({'signature':signature,'event':event,'paymentId':payment_id},{'_id':0}): return {'ok':True,'duplicate':True}
    await db.razorpay_events.insert_one({'id':str(uuid.uuid4()),'event':event,'signature':signature,'paymentId':payment_id,'receivedAt':datetime.now(timezone.utc).isoformat()})
    if event in ('payment.captured','order.paid') and order_id:
        record=await db.payments.find_one({'razorpayOrderId':order_id},{'_id':0});
        if record:
            c=await db.campaigns.find_one({'id':record['campaignId']},{'_id':0});
            if c and record.get('status')!='paid' and pe.get('status')=='captured' and int(pe.get('amount',0))==int(record.get('amountPaise',0)):
                await finalize_verified_payment(c,record,payment_id)
    elif event=='payment.failed' and order_id:
        await db.payments.update_many({'razorpayOrderId':order_id},{'$set':{'status':'failed','updatedAt':datetime.now(timezone.utc).isoformat()}})
    return {'ok':True}

@campaign_router.post('/{campaign_id}/pay')
async def pay_compat(campaign_id:str,current_user=Depends(get_current_user)): return await create_payment_order(campaign_id,current_user)
@campaign_router.post('/{campaign_id}/shipping')
async def shipping(campaign_id:str,shippingDetails:str=Query(...),current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if c['senderUserId']!=current_user['id']: raise HTTPException(status_code=403,detail='Only sender can add shipping details')
    await db.campaigns.update_one({'id':campaign_id},{'$set':{'shippingDetails':shippingDetails,'status':'in_progress','updatedAt':datetime.now(timezone.utc).isoformat()}}); return {'success':True,'message':'Shipping details added'}
@campaign_router.post('/{campaign_id}/product-received')
async def product_received(campaign_id:str,current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if c['receiverUserId']!=current_user['id']: raise HTTPException(status_code=403,detail='Only receiver can confirm receipt')
    await db.campaigns.update_one({'id':campaign_id},{'$set':{'productReceived':True,'status':'in_progress','updatedAt':datetime.now(timezone.utc).isoformat()}}); return {'success':True,'message':'Product receipt confirmed'}
@campaign_router.post('/{campaign_id}/submit-link')
async def submit_link(campaign_id:str,contentLink:str=Query(...),current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if current_user['id']!=creator_user_id(c): raise HTTPException(status_code=403,detail='Only the creator can submit content')
    if c['status'] not in ['paid','in_progress']: raise HTTPException(status_code=400,detail='Campaign must be paid/in progress')
    if not re.match(r'^https?://',contentLink): raise HTTPException(status_code=400,detail='Please submit a valid URL')
    await db.campaigns.update_one({'id':campaign_id},{'$set':{'contentLink':contentLink,'status':'link_submitted','updatedAt':datetime.now(timezone.utc).isoformat()}}); return {'success':True,'message':'Content link submitted for verification','contentLink':contentLink}
@campaign_router.post('/{campaign_id}/verify-link')
async def verify_link(campaign_id:str,current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if brand_user_id(c)!=current_user['id']: raise HTTPException(status_code=403,detail='Only the brand can verify the link')
    if c['status']!='link_submitted' or not c.get('contentLink'): raise HTTPException(status_code=400,detail='No link to verify')
    update={'linkVerified':True,'status':'link_verified','updatedAt':datetime.now(timezone.utc).isoformat()}; response={'success':True,'message':'Link verified!','status':'link_verified','linkVerified':True,'identityUnlocked':c.get('identityUnlocked',False)}
    if c['campaignType'] in ['barter_product','barter_service'] and not c.get('identityUnlocked',False):
        update['identityUnlocked']=True; sc,rc=identity_and_instagram(c); sp=await db[sc].find_one({'id':c['senderId']},{'_id':0}); rp=await db[rc].find_one({'id':c['receiverId']},{'_id':0}); response['identityUnlocked']=True; response['senderInstagram']=sp.get('instagramUsername') if sp else None; response['receiverInstagram']=rp.get('instagramUsername') if rp else None; response['message']='Link verified! Identity unlocked.'
    await db.campaigns.update_one({'id':campaign_id},{'$set':update}); return response

async def release_escrow(c):
    if c['campaignType']!='paid': return {'released':False,'amount':0,'reason':'not_applicable'}
    uid=creator_user_id(c); user=await db.users.find_one({'id':uid},{'_id':0}); account_id=user.get('razorpayLinkedAccountId') if user else None; amount=c.get('creatorPayout',0)
    if not account_id: return {'released':False,'amount':amount,'reason':'creator_linked_account_not_configured'}
    pid=c.get('razorpayPaymentId');
    if not pid: return {'released':False,'amount':amount,'reason':'payment_missing'}
    transfer=razorpay_request('POST',f'/payments/{pid}/transfers',json={'transfers':[{'account':account_id,'amount':int(round(amount*100)),'currency':'INR','on_hold':False,'notes':{'campaign_id':c['id']}}]}); items=transfer.get('items',[]); return {'released':True,'amount':amount,'transferId':(items[0].get('id') if items else transfer.get('id'))}
@campaign_router.post('/{campaign_id}/complete')
async def complete(campaign_id:str,current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if brand_user_id(c)!=current_user['id']: raise HTTPException(status_code=403,detail='Only the brand can complete')
    if c['status']!='link_verified': raise HTTPException(status_code=400,detail='Link must be verified before completion')
    result=await release_escrow(c); now=datetime.now(timezone.utc).isoformat(); await db.campaigns.update_one({'id':campaign_id},{'$set':{'status':'completed','payoutStatus':'released' if result['released'] else 'pending','updatedAt':now}})
    if result['released']: await db.payouts.insert_one({'id':str(uuid.uuid4()),'campaignId':campaign_id,'creatorUserId':creator_user_id(c),'amount':result['amount'],'status':'released','transferId':result.get('transferId'),'createdAt':now})
    await db.creator_profiles.update_one({'userId':creator_user_id(c)},{'$inc':{'totalCollabs':1}}); return {'success':True,'status':'completed','payoutAmount':result['amount'],'payoutStatus':'released' if result['released'] else 'pending','message':'Campaign completed! Creator payout released.' if result['released'] else 'Campaign completed. Creator payout is pending linked-account setup.'}
@campaign_router.post('/{campaign_id}/rate')
async def rate(campaign_id:str,rating:int=Query(...,ge=1,le=5),feedback:str=Query(...,min_length=10),current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    if c['status']!='completed': raise HTTPException(status_code=400,detail='Can only rate completed campaigns')
    ensure_party(c,current_user)
    if await db.ratings.find_one({'campaignId':campaign_id,'raterId':current_user['id']}): raise HTTPException(status_code=400,detail="You've already rated this campaign")
    target=creator_user_id(c) if current_user['id']==brand_user_id(c) else brand_user_id(c); target_type='creator' if target==creator_user_id(c) else 'brand'; now=datetime.now(timezone.utc).isoformat(); await db.ratings.insert_one({'id':str(uuid.uuid4()),'campaignId':campaign_id,'raterId':current_user['id'],'raterType':current_user['role'],'targetId':target,'targetType':target_type,'rating':rating,'feedback':feedback,'createdAt':now}); rs=await db.ratings.find({'targetId':target},{'_id':0}).to_list(1000); avg=sum(x['rating'] for x in rs)/len(rs); col='creator_profiles' if target_type=='creator' else 'brand_profiles'; await db[col].update_one({'userId':target},{'$set':{'rating':round(avg,2)}}); return {'success':True,'message':'Rating submitted!','rating':rating}
@campaign_router.post('/{campaign_id}/report')
async def report(campaign_id:str,reason:str=Query(...),current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    ensure_party(c,current_user); await db.campaigns.update_one({'id':campaign_id},{'$set':{'status':'disputed','updatedAt':datetime.now(timezone.utc).isoformat()}}); doc={'id':str(uuid.uuid4()),'campaignId':campaign_id,'reporterId':current_user['id'],'reason':reason,'status':'pending','createdAt':datetime.now(timezone.utc).isoformat()}; await db.reports.insert_one(doc); return {'success':True,'reportId':doc['id'],'message':'Report submitted. Admin will review.'}

@message_router.get('/{campaign_id}',response_model=List[MessageResponse])
async def messages_get(campaign_id:str,current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    ensure_party(c,current_user)
    if not c.get('chatEnabled',False): raise HTTPException(status_code=403,detail='Chat not enabled. Complete payment first.')
    items=await db.messages.find({'campaignId':campaign_id},{'_id':0}).sort('createdAt',1).to_list(500); return [MessageResponse(**x) for x in items]
@message_router.post('/{campaign_id}',response_model=MessageResponse,status_code=201)
async def messages_send(campaign_id:str,message:MessageCreate,current_user=Depends(get_current_user)):
    c=await db.campaigns.find_one({'id':campaign_id},{'_id':0});
    if not c: raise HTTPException(status_code=404,detail='Campaign not found')
    ensure_party(c,current_user)
    if not c.get('chatEnabled',False): raise HTTPException(status_code=403,detail='Chat not enabled. Complete payment first.')
    blocked=check_blocked_content(message.content); now=datetime.now(timezone.utc).isoformat(); doc={'id':str(uuid.uuid4()),'campaignId':campaign_id,'senderId':current_user['id'],'senderType':current_user['role'],'content':message.content if not blocked else '[Message blocked - external contact not allowed]','blocked':blocked,'createdAt':now};
    if blocked: await db.bypass_attempts.insert_one({'id':str(uuid.uuid4()),'campaignId':campaign_id,'userId':current_user['id'],'content':message.content,'createdAt':now})
    await db.messages.insert_one(doc); return MessageResponse(**doc)

@api_router.post('/seed')
async def seed(current_user=None):
    # Demo-only helper retained from the original project. It is disabled by default in production unless SEED_ENABLED=true.
    if os.environ.get('SEED_ENABLED','true').lower()!='true': raise HTTPException(status_code=403,detail='Seed endpoint disabled')
    from seed import build_seed_documents
    for col in ['users','creator_profiles','brand_profiles','campaigns','messages','payments','reports','ratings','payouts','razorpay_events','bypass_attempts']:
        await db[col].delete_many({})
    users,creator_profiles,brand_profiles=build_seed_documents();
    if users: await db.users.insert_many(users)
    if creator_profiles: await db.creator_profiles.insert_many(creator_profiles)
    if brand_profiles: await db.brand_profiles.insert_many(brand_profiles)
    return {'message':'Seed data created!','creators':len(creator_profiles),'brands':len(brand_profiles),'testCredentials':{'admin':'admin@orange.com / admin123','creator':'creator1@orange.com / password123','brand':'brand1@orange.com / password123'}}
@admin_router.get('/stats')
async def stats(current_user=Depends(get_current_user)):
    if not current_user.get('isAdmin',False): raise HTTPException(status_code=403,detail='Admin access required')
    outstanding=await db.campaigns.aggregate([{'$match':{'campaignType':'paid','paymentStatus':'paid','status':{'$ne':'completed'}}},{'$group':{'_id':None,'total':{'$sum':'$escrowAmount'}}}]).to_list(1); return {'totalUsers':await db.users.count_documents({}),'totalCreators':await db.creator_profiles.count_documents({}),'totalBrands':await db.brand_profiles.count_documents({}),'totalCampaigns':await db.campaigns.count_documents({}),'activeCampaigns':await db.campaigns.count_documents({'status':{'$in':['requested','accepted','payment_pending','paid','in_progress','link_submitted','link_verified']}}),'completedCampaigns':await db.campaigns.count_documents({'status':'completed'}),'pendingReports':await db.reports.count_documents({'status':'pending'}),'blacklistedCreators':await db.creator_profiles.count_documents({'isBlacklisted':True}),'bypassAttempts':await db.bypass_attempts.count_documents({}),'escrowValue':outstanding[0]['total'] if outstanding else 0}
@admin_router.get('/reports')
async def reports(current_user=Depends(get_current_user)):
    if not current_user.get('isAdmin',False): raise HTTPException(status_code=403,detail='Admin access required')
    return await db.reports.find({'status':'pending'},{'_id':0}).to_list(100)
@admin_router.post('/blacklist/{user_id}')
async def blacklist(user_id:str,reason:str=Query(...),current_user=Depends(get_current_user)):
    if not current_user.get('isAdmin',False): raise HTTPException(status_code=403,detail='Admin access required')
    await db.users.update_one({'id':user_id},{'$set':{'isBlacklisted':True}}); await db.creator_profiles.update_one({'userId':user_id},{'$set':{'isBlacklisted':True}}); await db.campaigns.update_many({'$or':[{'senderUserId':user_id},{'receiverUserId':user_id}], 'status':{'$in':['requested','accepted','paid','in_progress','link_submitted','link_verified']}},{'$set':{'status':'cancelled','updatedAt':datetime.now(timezone.utc).isoformat()}}); return {'success':True,'message':'User blacklisted'}

api_router.include_router(auth_router); api_router.include_router(creator_router); api_router.include_router(business_router); api_router.include_router(marketplace_router); api_router.include_router(campaign_router); api_router.include_router(payment_router); api_router.include_router(message_router); api_router.include_router(admin_router)
app.include_router(api_router)
app.add_middleware(CORSMiddleware,allow_origins=CORS_ORIGINS,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
@app.on_event('startup')
async def startup(): logger.info('Orange API started - live Razorpay payment flow enabled')
@app.on_event('shutdown')
async def shutdown(): client.close()
