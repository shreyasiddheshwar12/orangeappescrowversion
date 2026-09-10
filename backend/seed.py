from datetime import datetime, timezone
import uuid

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def build_seed_documents():
    now = datetime.now(timezone.utc).isoformat()
    users = []
    creator_profiles = []
    brand_profiles = []

    admin_id = str(uuid.uuid4())
    users.append({
        'id': admin_id,
        'email': 'admin@orange.com',
        'passwordHash': hash_password('admin123'),
        'role': 'business',
        'hasCompletedOnboarding': True,
        'isAdmin': True,
        'instagramVerified': True,
        'instagramUserId': f'ig_{uuid.uuid4().hex[:8]}',
        'instagramUsername': '@orange_admin',
        'isBlacklisted': False,
        'createdAt': now,
    })

    creators = [
        ('Priya Sharma', 'Fashion', 'Hindi', 'Reels', 'Mumbai', 15000, 5000, 8.5),
        ('Arjun Kapoor', 'Fitness', 'English', 'Reels, Stories', 'Delhi', 12000, 4000, 6.2),
        ('Meera Patel', 'Beauty', 'English', 'Reels', 'Bangalore', 8000, 3000, 9.1),
        ('Rahul Verma', 'Tech', 'Hindi', 'Reels, Posts', 'Hyderabad', 10000, 3500, 5.8),
    ]
    for i, (name, niche, language, content_type, location, reel, story, engagement) in enumerate(creators, 1):
        user_id = str(uuid.uuid4())
        profile_id = str(uuid.uuid4())
        ig = f'@{name.lower().replace(" ", "_")}'
        users.append({
            'id': user_id,
            'email': f'creator{i}@orange.com',
            'passwordHash': hash_password('password123'),
            'role': 'creator',
            'hasCompletedOnboarding': True,
            'isAdmin': False,
            'instagramVerified': True,
            'instagramUserId': f'ig_{uuid.uuid4().hex[:8]}',
            'instagramUsername': ig,
            'engagementRate': engagement,
            'isBlacklisted': False,
            'createdAt': now,
        })
        creator_profiles.append({
            'id': profile_id,
            'userId': user_id,
            'name': name,
            'bio': f'Content creator specializing in {niche}',
            'location': location,
            'niche': niche,
            'language': language,
            'contentType': content_type,
            'niches': [niche],
            'reelPrice': reel,
            'storyPrice': story,
            'postPrice': round(reel * 0.8, 2),
            'paidCollabsEnabled': True,
            'barterEnabled': True,
            'instagramVerified': True,
            'instagramUserId': users[-1]['instagramUserId'],
            'instagramUsername': ig,
            'engagementRate': engagement,
            'profilePhotoUrl': '',
            'isBlacklisted': False,
            'isVisible': True,
            'subscriptionActive': True,
            'rating': None,
            'totalCollabs': 0,
            'createdAt': now,
            'updatedAt': now,
        })

    brands = [
        ('Glow Cosmetics', 'Beauty', 'Mumbai', '₹10k-₹50k', 'Reels, Stories'),
        ('FitLife Nutrition', 'Health & Fitness', 'Delhi', '₹15k-₹40k', 'Reels, Posts'),
    ]
    for i, (name, industry, location, budget, deliverables) in enumerate(brands, 1):
        user_id = str(uuid.uuid4())
        profile_id = str(uuid.uuid4())
        ig = f'@{name.lower().replace(" ", "_")}'
        users.append({
            'id': user_id,
            'email': f'brand{i}@orange.com',
            'passwordHash': hash_password('password123'),
            'role': 'business',
            'hasCompletedOnboarding': True,
            'isAdmin': False,
            'instagramVerified': True,
            'instagramUserId': f'ig_{uuid.uuid4().hex[:8]}',
            'instagramUsername': ig,
            'isBlacklisted': False,
            'createdAt': now,
        })
        brand_profiles.append({
            'id': profile_id,
            'userId': user_id,
            'brandName': name,
            'industry': industry,
            'bio': f'Leading brand in {industry}',
            'location': location,
            'deliverables': deliverables,
            'budgetRange': budget,
            'barterEnabled': True,
            'paidCollabsEnabled': True,
            'brandRequirements': 'High-quality content with authentic engagement',
            'instagramVerified': True,
            'instagramUserId': users[-1]['instagramUserId'],
            'instagramUsername': ig,
            'profilePhotoUrl': '',
            'rating': None,
            'createdAt': now,
            'updatedAt': now,
        })

    return users, creator_profiles, brand_profiles
