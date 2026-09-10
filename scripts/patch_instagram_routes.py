from pathlib import Path

path = Path('backend/server.py')
text = path.read_text(encoding='utf-8')

if "@auth_router.get('/instagram/connect'" in text:
    raise SystemExit(0)

marker = "@creator_router.post('/profile',response_model=CreatorProfileFull)"
if marker not in text:
    raise SystemExit('Could not find auth/profile insertion marker')

block = r'''
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

'''

text = text.replace(marker, block + marker, 1)
path.write_text(text, encoding='utf-8')
print('Instagram OAuth routes restored')
