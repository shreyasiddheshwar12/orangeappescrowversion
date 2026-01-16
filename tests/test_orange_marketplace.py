"""
Orange Creator Marketplace - Backend API Tests
Tests for: Auth, Marketplace, Credits, Unlocks, Payments
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://creator-market-43.preview.emergentagent.com')

# Test credentials from seed data
BRAND_EMAIL = "brand1@orange.com"
BRAND_PASSWORD = "password123"
CREATOR_EMAIL = "creator1@orange.com"
CREATOR_PASSWORD = "password123"
ADMIN_EMAIL = "admin@orange.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def brand_token(api_client):
    """Get brand authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": BRAND_EMAIL,
        "password": BRAND_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Brand authentication failed")


@pytest.fixture(scope="module")
def creator_token(api_client):
    """Get creator authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": CREATOR_EMAIL,
        "password": CREATOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Creator authentication failed")


@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin authentication failed")


class TestHealthAndRoot:
    """Health check and root endpoint tests"""
    
    def test_health_endpoint(self, api_client):
        """Test /api/health returns healthy status"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["testMode"] == True
        print("✓ Health endpoint working")
    
    def test_root_endpoint(self, api_client):
        """Test /api/ returns API info"""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "Orange" in data["message"]
        print("✓ Root endpoint working")


class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_brand_login_success(self, api_client):
        """Test brand login with seeded credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND_EMAIL,
            "password": BRAND_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == BRAND_EMAIL
        assert data["user"]["role"] == "business"
        assert data["user"]["hasCompletedOnboarding"] == True
        print(f"✓ Brand login successful: {BRAND_EMAIL}")
    
    def test_creator_login_success(self, api_client):
        """Test creator login with seeded credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR_EMAIL,
            "password": CREATOR_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == CREATOR_EMAIL
        assert data["user"]["role"] == "creator"
        assert data["user"]["hasCompletedOnboarding"] == True
        print(f"✓ Creator login successful: {CREATOR_EMAIL}")
    
    def test_admin_login_success(self, api_client):
        """Test admin login with seeded credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["isAdmin"] == True
        print(f"✓ Admin login successful: {ADMIN_EMAIL}")
    
    def test_login_invalid_credentials(self, api_client):
        """Test login with wrong password"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials rejected correctly")
    
    def test_get_me_authenticated(self, api_client, brand_token):
        """Test /auth/me returns current user"""
        response = api_client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == BRAND_EMAIL
        assert data["role"] == "business"
        print("✓ /auth/me returns correct user")
    
    def test_get_me_unauthenticated(self, api_client):
        """Test /auth/me without token returns 401/403"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403]
        print("✓ /auth/me rejects unauthenticated requests")


class TestCreditsAPI:
    """Credits API tests - critical for unlock flow"""
    
    def test_get_credits_brand(self, api_client, brand_token):
        """Test brand can get their credit balance"""
        response = api_client.get(
            f"{BASE_URL}/api/payments/credits",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "totalCredits" in data
        assert "availableCredits" in data
        assert "lockedCredits" in data
        assert "usedCredits" in data
        # Brand1 should have 5 credits from seed
        assert data["totalCredits"] >= 0
        print(f"✓ Brand credits: {data['availableCredits']} available / {data['totalCredits']} total")
    
    def test_add_demo_credits(self, api_client, brand_token):
        """Test demo credits addition flow"""
        # Get initial credits
        initial_response = api_client.get(
            f"{BASE_URL}/api/payments/credits",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        initial_credits = initial_response.json()["totalCredits"]
        
        # Add demo credits
        response = api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "5 credits" in data["message"].lower() or "demo" in data["message"].lower()
        
        # Verify credits increased
        final_response = api_client.get(
            f"{BASE_URL}/api/payments/credits",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        final_credits = final_response.json()["totalCredits"]
        assert final_credits == initial_credits + 5
        print(f"✓ Demo credits added: {initial_credits} -> {final_credits}")


class TestMarketplace:
    """Marketplace discovery tests"""
    
    def test_discover_creators_as_brand(self, api_client, brand_token):
        """Test brand can discover creators in marketplace"""
        response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # Should have seeded creators
        
        # Verify discovery data structure (Layer 1 - no identity)
        if len(data) > 0:
            creator = data[0]
            assert "id" in creator
            assert "niches" in creator
            assert "followersDisplay" in creator
            assert "engagementRateDisplay" in creator
            assert "rateRange" in creator
            assert "isUnlocked" in creator
            # Should NOT have identity info in discovery
            assert "instagramUsername" not in creator
            print(f"✓ Found {len(data)} creators in marketplace")
    
    def test_discover_creators_with_niche_filter(self, api_client, brand_token):
        """Test marketplace filtering by niche"""
        response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators?niche=Fashion",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # All returned creators should have Fashion niche
        for creator in data:
            assert "Fashion" in creator.get("niches", [])
        print(f"✓ Niche filter working: {len(data)} Fashion creators")
    
    def test_discover_creators_with_barter_filter(self, api_client, brand_token):
        """Test marketplace filtering by barter availability"""
        response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators?openToBarter=true",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        for creator in data:
            assert creator.get("isOpenToBarter") == True
        print(f"✓ Barter filter working: {len(data)} barter-friendly creators")
    
    def test_discover_brands_as_creator(self, api_client, creator_token):
        """Test creator can discover brands"""
        response = api_client.get(
            f"{BASE_URL}/api/marketplace/brands",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            brand = data[0]
            assert "id" in brand
            assert "brandName" in brand
            assert "industry" in brand
            assert "budgetRange" in brand
        print(f"✓ Found {len(data)} brands in marketplace")


class TestUnlockFlow:
    """Profile unlock flow tests - critical feature"""
    
    def test_unlock_creator_profile(self, api_client, brand_token):
        """Test brand can unlock a creator profile using credits"""
        # First get a creator from marketplace
        creators_response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert creators_response.status_code == 200
        creators = creators_response.json()
        assert len(creators) > 0
        
        # Find a locked creator
        locked_creator = None
        for c in creators:
            if not c.get("isUnlocked"):
                locked_creator = c
                break
        
        if not locked_creator:
            # All creators already unlocked, skip
            pytest.skip("All creators already unlocked")
        
        creator_id = locked_creator["id"]
        
        # Ensure we have credits
        api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        
        # Unlock the creator
        response = api_client.post(
            f"{BASE_URL}/api/marketplace/creator/{creator_id}/unlock",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ Creator {creator_id} unlocked successfully")
    
    def test_view_unlocked_creator_profile(self, api_client, brand_token):
        """Test brand can view unlocked creator profile with full context"""
        # Get creators and find an unlocked one
        creators_response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        creators = creators_response.json()
        
        unlocked_creator = None
        for c in creators:
            if c.get("isUnlocked"):
                unlocked_creator = c
                break
        
        if not unlocked_creator:
            pytest.skip("No unlocked creators available")
        
        creator_id = unlocked_creator["id"]
        
        # Get unlocked profile
        response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators/{creator_id}/unlocked",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify unlocked data structure (Layer 2 - context, no identity)
        assert "id" in data
        assert "followersCount" in data  # Exact count, not display
        assert "engagementRate" in data  # Exact rate
        assert "rates" in data  # Full rate card
        assert "bio" in data
        assert "profilePhotoUrl" in data
        # Should still NOT have Instagram (that's Layer 3)
        print(f"✓ Unlocked profile has: {data.get('followersCount')} followers, {data.get('engagementRate')}% engagement")
    
    def test_view_locked_creator_returns_403(self, api_client):
        """Test viewing locked creator without unlock returns 403"""
        # Create a new user to ensure no unlocks
        signup_response = api_client.post(f"{BASE_URL}/api/auth/signup", json={
            "email": f"test_new_brand_{os.urandom(4).hex()}@test.com",
            "password": "testpass123",
            "role": "business"
        })
        
        if signup_response.status_code != 200:
            pytest.skip("Could not create test user")
        
        new_token = signup_response.json()["access_token"]
        
        # Get a creator
        creators_response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        creators = creators_response.json()
        
        if len(creators) == 0:
            pytest.skip("No creators available")
        
        creator_id = creators[0]["id"]
        
        # Try to view unlocked profile without unlocking
        response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators/{creator_id}/unlocked",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert response.status_code == 403
        print("✓ Locked profile correctly returns 403")


class TestCreatorProfile:
    """Creator profile management tests"""
    
    def test_get_creator_profile(self, api_client, creator_token):
        """Test creator can get their own profile"""
        response = api_client.get(
            f"{BASE_URL}/api/creator/profile",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "rates" in data
        assert "niches" in data
        assert "followersCount" in data
        assert "engagementRate" in data
        print(f"✓ Creator profile: {data.get('name')}, {data.get('followersCount')} followers")


class TestBusinessProfile:
    """Business profile management tests"""
    
    def test_get_business_profile(self, api_client, brand_token):
        """Test brand can get their own profile"""
        response = api_client.get(
            f"{BASE_URL}/api/business/profile",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "brandName" in data
        assert "industry" in data
        assert "budgetRange" in data
        print(f"✓ Business profile: {data.get('brandName')}, {data.get('industry')}")


class TestInstagramVerification:
    """Instagram verification (simulated) tests"""
    
    def test_instagram_verify_simulated(self, api_client, creator_token):
        """Test simulated Instagram verification"""
        response = api_client.post(
            f"{BASE_URL}/api/instagram/verify",
            json={"instagramUsername": "test_creator_ig"},
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "instagramUserId" in data
        assert "followersCount" in data
        assert "engagementRate" in data
        assert "Demo" in data.get("message", "")
        print(f"✓ Instagram verification (MOCKED): {data.get('followersCount')} followers, {data.get('engagementRate')}% engagement")


class TestPaymentsAPI:
    """Payments API tests"""
    
    def test_create_unlock_order(self, api_client, brand_token):
        """Test creating unlock pack order"""
        response = api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/order",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "orderId" in data
        assert "amount" in data
        assert data["amount"] == 20000  # ₹200 in paise
        assert data["currency"] == "INR"
        assert data["testMode"] == True
        print(f"✓ Unlock order created: {data.get('orderId')}, ₹{data.get('amount')/100}")


class TestAdminAPI:
    """Admin API tests"""
    
    def test_admin_stats(self, api_client, admin_token):
        """Test admin can get platform stats"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "totalUsers" in data
        assert "totalCreators" in data
        assert "totalBrands" in data
        assert "verifiedCreators" in data
        print(f"✓ Admin stats: {data.get('totalUsers')} users, {data.get('totalCreators')} creators, {data.get('totalBrands')} brands")
    
    def test_admin_stats_requires_admin(self, api_client, brand_token):
        """Test non-admin cannot access admin stats"""
        response = api_client.get(
            f"{BASE_URL}/api/admin/stats",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 403
        print("✓ Admin stats correctly restricted to admins")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
