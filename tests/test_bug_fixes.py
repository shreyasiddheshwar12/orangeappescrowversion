"""
Orange Creator Marketplace - Bug Fix Tests
Tests for: Auth redirect bug, Asymmetric marketplace, Profile visibility, Session persistence
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://brand-connect-66.preview.emergentagent.com')

# Test credentials from seed data
BRAND_EMAIL = "brand1@orange.com"
BRAND_PASSWORD = "password123"
CREATOR_EMAIL = "creator1@orange.com"
CREATOR_PASSWORD = "password123"


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


class TestSessionPersistence:
    """Test session persistence - Bug Fix #4"""
    
    def test_brand_session_persists_after_login(self, api_client, brand_token):
        """Test brand session persists - can make multiple authenticated requests"""
        # First request - get profile
        response1 = api_client.get(
            f"{BASE_URL}/api/business/profile",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response1.status_code == 200
        
        # Second request - get credits
        response2 = api_client.get(
            f"{BASE_URL}/api/payments/credits",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response2.status_code == 200
        
        # Third request - get marketplace
        response3 = api_client.get(
            f"{BASE_URL}/api/marketplace/creators",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response3.status_code == 200
        print("✓ Brand session persists across multiple requests")
    
    def test_creator_session_persists_after_login(self, api_client, creator_token):
        """Test creator session persists - can make multiple authenticated requests"""
        # First request - get profile
        response1 = api_client.get(
            f"{BASE_URL}/api/creator/profile",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert response1.status_code == 200
        
        # Second request - get brands
        response2 = api_client.get(
            f"{BASE_URL}/api/marketplace/brands",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert response2.status_code == 200
        
        # Third request - get incoming requests
        response3 = api_client.get(
            f"{BASE_URL}/api/requests/incoming",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert response3.status_code == 200
        print("✓ Creator session persists across multiple requests")
    
    def test_auth_me_returns_correct_user_data(self, api_client, brand_token, creator_token):
        """Test /auth/me returns correct user data for session validation"""
        # Brand
        brand_response = api_client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert brand_response.status_code == 200
        brand_data = brand_response.json()
        assert brand_data["email"] == BRAND_EMAIL
        assert brand_data["role"] == "business"
        assert brand_data["hasCompletedOnboarding"] == True
        
        # Creator
        creator_response = api_client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert creator_response.status_code == 200
        creator_data = creator_response.json()
        assert creator_data["email"] == CREATOR_EMAIL
        assert creator_data["role"] == "creator"
        assert creator_data["hasCompletedOnboarding"] == True
        print("✓ /auth/me returns correct user data for both roles")


class TestAsymmetricMarketplace:
    """Test two-way marketplace - Bug Fix #2 (Creators can unlock brands)"""
    
    def test_creator_can_discover_brands(self, api_client, creator_token):
        """Test creator can see brands in marketplace"""
        response = api_client.get(
            f"{BASE_URL}/api/marketplace/brands",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert response.status_code == 200
        brands = response.json()
        assert isinstance(brands, list)
        assert len(brands) >= 1  # Should have seeded brands
        
        # Verify brand discovery data structure
        brand = brands[0]
        assert "id" in brand
        assert "brandName" in brand
        assert "industry" in brand
        assert "budgetRange" in brand
        assert "isUnlocked" in brand
        print(f"✓ Creator can discover {len(brands)} brands")
    
    def test_creator_can_add_demo_credits(self, api_client, creator_token):
        """Test creator can add demo credits"""
        response = api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print("✓ Creator can add demo credits")
    
    def test_creator_can_unlock_brand(self, api_client, creator_token):
        """Test creator can unlock a brand profile using credits"""
        # First ensure creator has credits
        api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        
        # Get brands
        brands_response = api_client.get(
            f"{BASE_URL}/api/marketplace/brands",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        brands = brands_response.json()
        assert len(brands) > 0
        
        # Find a locked brand
        locked_brand = None
        for b in brands:
            if not b.get("isUnlocked"):
                locked_brand = b
                break
        
        if not locked_brand:
            # All brands already unlocked, try to unlock first one anyway
            locked_brand = brands[0]
        
        brand_id = locked_brand["id"]
        
        # Unlock the brand
        response = api_client.post(
            f"{BASE_URL}/api/marketplace/brand/{brand_id}/unlock",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ Creator unlocked brand {brand_id}")
    
    def test_creator_can_view_unlocked_brand(self, api_client, creator_token):
        """Test creator can view unlocked brand profile"""
        # Get brands
        brands_response = api_client.get(
            f"{BASE_URL}/api/marketplace/brands",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        brands = brands_response.json()
        
        # Find an unlocked brand
        unlocked_brand = None
        for b in brands:
            if b.get("isUnlocked"):
                unlocked_brand = b
                break
        
        if not unlocked_brand:
            pytest.skip("No unlocked brands available")
        
        brand_id = unlocked_brand["id"]
        
        # Get unlocked brand profile
        response = api_client.get(
            f"{BASE_URL}/api/marketplace/brands/{brand_id}/unlocked",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify unlocked brand data
        assert "id" in data
        assert "brandName" in data
        assert "bio" in data
        assert "budgetRange" in data
        assert "preferredNiches" in data
        print(f"✓ Creator can view unlocked brand: {data.get('brandName')}")


class TestBrandUnlockCreator:
    """Test brand can unlock creator - Bug Fix #1 (Auth redirect)"""
    
    def test_brand_can_unlock_creator_with_credits(self, api_client, brand_token):
        """Test brand can unlock creator profile"""
        # Ensure brand has credits
        api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        
        # Get creators
        creators_response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        creators = creators_response.json()
        assert len(creators) > 0
        
        # Find a locked creator
        locked_creator = None
        for c in creators:
            if not c.get("isUnlocked"):
                locked_creator = c
                break
        
        if not locked_creator:
            locked_creator = creators[0]
        
        creator_id = locked_creator["id"]
        
        # Unlock the creator
        response = api_client.post(
            f"{BASE_URL}/api/marketplace/creator/{creator_id}/unlock",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ Brand unlocked creator {creator_id}")
    
    def test_brand_can_view_unlocked_creator(self, api_client, brand_token):
        """Test brand can view unlocked creator profile"""
        # Get creators
        creators_response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        creators = creators_response.json()
        
        # Find an unlocked creator
        unlocked_creator = None
        for c in creators:
            if c.get("isUnlocked"):
                unlocked_creator = c
                break
        
        if not unlocked_creator:
            pytest.skip("No unlocked creators available")
        
        creator_id = unlocked_creator["id"]
        
        # Get unlocked creator profile
        response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators/{creator_id}/unlocked",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify unlocked creator data
        assert "id" in data
        assert "followersCount" in data
        assert "engagementRate" in data
        assert "rates" in data
        assert "bio" in data
        print(f"✓ Brand can view unlocked creator with {data.get('followersCount')} followers")


class TestCreditsDecrement:
    """Test credits decrement correctly after unlock"""
    
    def test_credits_decrement_after_unlock(self, api_client):
        """Test credits decrease by 1 after unlocking a profile"""
        # Create a new user to test fresh credits
        unique_email = f"test_credits_{uuid.uuid4().hex[:8]}@test.com"
        signup_response = api_client.post(f"{BASE_URL}/api/auth/signup", json={
            "email": unique_email,
            "password": "testpass123",
            "role": "business"
        })
        
        if signup_response.status_code != 200:
            pytest.skip("Could not create test user")
        
        new_token = signup_response.json()["access_token"]
        
        # Add demo credits
        api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        
        # Get initial credits
        initial_response = api_client.get(
            f"{BASE_URL}/api/payments/credits",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        initial_credits = initial_response.json()["availableCredits"]
        
        # Get a creator to unlock
        creators_response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        creators = creators_response.json()
        
        if len(creators) == 0:
            pytest.skip("No creators available")
        
        creator_id = creators[0]["id"]
        
        # Unlock the creator
        api_client.post(
            f"{BASE_URL}/api/marketplace/creator/{creator_id}/unlock",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        
        # Get final credits
        final_response = api_client.get(
            f"{BASE_URL}/api/payments/credits",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        final_credits = final_response.json()["availableCredits"]
        
        # Verify credits decreased by 1
        assert final_credits == initial_credits - 1
        print(f"✓ Credits decremented correctly: {initial_credits} -> {final_credits}")


class TestNewProfileVisibility:
    """Test new profiles appear in marketplace - Bug Fix #3"""
    
    def test_new_creator_appears_in_marketplace_after_onboarding(self, api_client, brand_token):
        """Test new creator with Instagram verification appears in marketplace"""
        # Create a new creator
        unique_email = f"test_creator_{uuid.uuid4().hex[:8]}@test.com"
        signup_response = api_client.post(f"{BASE_URL}/api/auth/signup", json={
            "email": unique_email,
            "password": "testpass123",
            "role": "creator"
        })
        
        if signup_response.status_code != 200:
            pytest.skip("Could not create test creator")
        
        new_token = signup_response.json()["access_token"]
        
        # Verify Instagram (simulated)
        verify_response = api_client.post(
            f"{BASE_URL}/api/instagram/verify",
            json={"instagramUsername": f"test_ig_{uuid.uuid4().hex[:6]}"},
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert verify_response.status_code == 200
        ig_data = verify_response.json()
        
        # Complete onboarding with profile
        profile_response = api_client.post(
            f"{BASE_URL}/api/creator/profile",
            json={
                "name": f"Test Creator {uuid.uuid4().hex[:4]}",
                "bio": "Test creator for marketplace visibility",
                "location": "Test City",
                "niches": ["Fashion", "Lifestyle"],
                "isOpenToBarter": True,
                "rates": {
                    "reelPrice": 10000,
                    "storyPrice": 3000,
                    "carouselPrice": 7000,
                    "postPrice": 5000,
                    "bundlePrice": 20000
                },
                "followersCount": ig_data.get("followersCount"),
                "engagementRate": ig_data.get("engagementRate")
            },
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert profile_response.status_code == 200
        new_creator_id = profile_response.json()["id"]
        
        # Check if new creator appears in marketplace (as brand)
        marketplace_response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert marketplace_response.status_code == 200
        creators = marketplace_response.json()
        
        # Find the new creator
        found = False
        for c in creators:
            if c["id"] == new_creator_id:
                found = True
                break
        
        assert found, f"New creator {new_creator_id} not found in marketplace"
        print(f"✓ New creator {new_creator_id} appears in marketplace after onboarding")
    
    def test_new_brand_appears_in_marketplace_after_onboarding(self, api_client, creator_token):
        """Test new brand with Instagram verification appears in marketplace"""
        # Create a new brand
        unique_email = f"test_brand_{uuid.uuid4().hex[:8]}@test.com"
        signup_response = api_client.post(f"{BASE_URL}/api/auth/signup", json={
            "email": unique_email,
            "password": "testpass123",
            "role": "business"
        })
        
        if signup_response.status_code != 200:
            pytest.skip("Could not create test brand")
        
        new_token = signup_response.json()["access_token"]
        
        # Verify Instagram (simulated)
        verify_response = api_client.post(
            f"{BASE_URL}/api/instagram/verify",
            json={"instagramUsername": f"test_brand_ig_{uuid.uuid4().hex[:6]}"},
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert verify_response.status_code == 200
        
        # Complete onboarding with profile
        profile_response = api_client.post(
            f"{BASE_URL}/api/business/profile",
            json={
                "brandName": f"Test Brand {uuid.uuid4().hex[:4]}",
                "industry": "Fashion",
                "bio": "Test brand for marketplace visibility",
                "location": "Test City",
                "budgetRange": "₹10k-₹50k",
                "preferredNiches": ["Fashion", "Lifestyle"],
                "isOpenToBarter": True
            },
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert profile_response.status_code == 200
        new_brand_id = profile_response.json()["id"]
        
        # Check if new brand appears in marketplace (as creator)
        marketplace_response = api_client.get(
            f"{BASE_URL}/api/marketplace/brands",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert marketplace_response.status_code == 200
        brands = marketplace_response.json()
        
        # Find the new brand
        found = False
        for b in brands:
            if b["id"] == new_brand_id:
                found = True
                break
        
        assert found, f"New brand {new_brand_id} not found in marketplace"
        print(f"✓ New brand {new_brand_id} appears in marketplace after onboarding")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
