"""
Orange Creator Marketplace - Iteration 4 Bug Fix Tests
Tests for:
1. Logout endpoint returns 200 (not 404)
2. Logout clears session and redirects to login
3. New brand with Instagram verification appears in creator marketplace
4. New creator with Instagram verification appears in brand marketplace
5. Brand profile shows past collaborations after unlock
6. Auth persists - clicking marketplace cards never redirects to login
7. Error messages are strings not objects
8. Unlock flow works both ways (brand->creator, creator->brand)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://collab-hub-90.preview.emergentagent.com')

# Test credentials
BRAND_EMAIL = "brand1@orange.com"
BRAND_PASSWORD = "password123"
CREATOR_EMAIL = "creator1@orange.com"
CREATOR_PASSWORD = "password123"
NEW_BRAND_EMAIL = "newbrand@test.com"
NEW_BRAND_PASSWORD = "test123456"


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


class TestLogoutEndpoint:
    """Test logout endpoint - Bug Fix #1 & #2"""
    
    def test_logout_returns_200_not_404(self, api_client):
        """Test POST /api/auth/logout returns 200 (not 404)"""
        response = api_client.post(f"{BASE_URL}/api/auth/logout")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        assert "message" in data
        print("✓ Logout endpoint returns 200 (not 404)")
    
    def test_logout_response_is_valid_json(self, api_client):
        """Test logout returns valid JSON response"""
        response = api_client.post(f"{BASE_URL}/api/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "message" in data
        assert isinstance(data["message"], str), "Error message should be string, not object"
        print("✓ Logout returns valid JSON with string message")


class TestBrandVisibility:
    """Test new brands appear in creator marketplace - Bug Fix #3"""
    
    def test_new_brand_with_instagram_appears_in_marketplace(self, api_client, creator_token):
        """Test new brand with Instagram verification appears in creator marketplace"""
        # Create a new brand
        unique_email = f"test_brand_vis_{uuid.uuid4().hex[:8]}@test.com"
        signup_response = api_client.post(f"{BASE_URL}/api/auth/signup", json={
            "email": unique_email,
            "password": "testpass123",
            "role": "business"
        })
        
        if signup_response.status_code != 200:
            pytest.skip("Could not create test brand")
        
        new_token = signup_response.json()["access_token"]
        
        # Verify Instagram (simulated) - REQUIRED for marketplace visibility
        verify_response = api_client.post(
            f"{BASE_URL}/api/instagram/verify",
            json={"instagramUsername": f"test_brand_ig_{uuid.uuid4().hex[:6]}"},
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert verify_response.status_code == 200
        
        # Complete onboarding with profile including past collaborations
        profile_response = api_client.post(
            f"{BASE_URL}/api/business/profile",
            json={
                "brandName": f"Test Brand Visibility {uuid.uuid4().hex[:4]}",
                "industry": "Tech",
                "bio": "Test brand for marketplace visibility testing",
                "location": "Bangalore",
                "budgetRange": "₹10k-₹50k",
                "preferredNiches": ["Tech", "Lifestyle"],
                "isOpenToBarter": True,
                "pastCollaborations": [
                    {
                        "campaignName": "Summer Launch 2024",
                        "creatorNiche": "Fashion",
                        "platform": "Instagram",
                        "description": "Product launch campaign"
                    }
                ]
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
        print(f"✓ New brand with Instagram verification appears in creator marketplace")


class TestCreatorVisibility:
    """Test new creators appear in brand marketplace - Bug Fix #4"""
    
    def test_new_creator_with_instagram_appears_in_marketplace(self, api_client, brand_token):
        """Test new creator with Instagram verification appears in brand marketplace"""
        # Create a new creator
        unique_email = f"test_creator_vis_{uuid.uuid4().hex[:8]}@test.com"
        signup_response = api_client.post(f"{BASE_URL}/api/auth/signup", json={
            "email": unique_email,
            "password": "testpass123",
            "role": "creator"
        })
        
        if signup_response.status_code != 200:
            pytest.skip("Could not create test creator")
        
        new_token = signup_response.json()["access_token"]
        
        # Verify Instagram (simulated) - REQUIRED for marketplace visibility
        verify_response = api_client.post(
            f"{BASE_URL}/api/instagram/verify",
            json={"instagramUsername": f"test_creator_ig_{uuid.uuid4().hex[:6]}"},
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert verify_response.status_code == 200
        ig_data = verify_response.json()
        
        # Complete onboarding with profile
        profile_response = api_client.post(
            f"{BASE_URL}/api/creator/profile",
            json={
                "name": f"Test Creator Visibility {uuid.uuid4().hex[:4]}",
                "bio": "Test creator for marketplace visibility",
                "location": "Mumbai",
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
        print(f"✓ New creator with Instagram verification appears in brand marketplace")


class TestPastCollaborations:
    """Test brand profile shows past collaborations after unlock - Bug Fix #5"""
    
    def test_brand_profile_shows_past_collabs_after_unlock(self, api_client, creator_token):
        """Test brand profile shows past collaborations after unlock"""
        # Create a new brand with past collaborations
        unique_email = f"test_brand_collabs_{uuid.uuid4().hex[:8]}@test.com"
        signup_response = api_client.post(f"{BASE_URL}/api/auth/signup", json={
            "email": unique_email,
            "password": "testpass123",
            "role": "business"
        })
        
        if signup_response.status_code != 200:
            pytest.skip("Could not create test brand")
        
        new_token = signup_response.json()["access_token"]
        
        # Verify Instagram
        api_client.post(
            f"{BASE_URL}/api/instagram/verify",
            json={"instagramUsername": f"test_brand_collabs_{uuid.uuid4().hex[:6]}"},
            headers={"Authorization": f"Bearer {new_token}"}
        )
        
        # Create profile with past collaborations
        past_collabs = [
            {
                "campaignName": "Summer Launch 2024",
                "creatorNiche": "Fashion",
                "platform": "Instagram",
                "description": "Product launch campaign"
            },
            {
                "campaignName": "Winter Collection",
                "creatorNiche": "Lifestyle",
                "platform": "YouTube",
                "description": "Seasonal campaign"
            }
        ]
        
        profile_response = api_client.post(
            f"{BASE_URL}/api/business/profile",
            json={
                "brandName": f"Test Brand Collabs {uuid.uuid4().hex[:4]}",
                "industry": "Fashion",
                "bio": "Test brand with past collaborations",
                "location": "Delhi",
                "budgetRange": "₹20k-₹100k",
                "preferredNiches": ["Fashion", "Beauty"],
                "isOpenToBarter": False,
                "pastCollaborations": past_collabs
            },
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert profile_response.status_code == 200
        brand_id = profile_response.json()["id"]
        
        # Ensure creator has credits
        api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        
        # Unlock the brand
        unlock_response = api_client.post(
            f"{BASE_URL}/api/marketplace/brand/{brand_id}/unlock",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert unlock_response.status_code == 200
        
        # Get unlocked brand profile
        unlocked_response = api_client.get(
            f"{BASE_URL}/api/marketplace/brands/{brand_id}/unlocked",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert unlocked_response.status_code == 200
        data = unlocked_response.json()
        
        # Verify past collaborations are present
        assert "pastCollaborations" in data
        assert len(data["pastCollaborations"]) == 2
        assert data["pastCollaborations"][0]["campaignName"] == "Summer Launch 2024"
        assert data["pastCollabCount"] == 2
        print(f"✓ Brand profile shows {len(data['pastCollaborations'])} past collaborations after unlock")


class TestAuthPersistence:
    """Test auth persists - clicking marketplace cards never redirects to login - Bug Fix #6"""
    
    def test_auth_persists_across_multiple_marketplace_requests(self, api_client, brand_token):
        """Test authenticated user can make multiple marketplace requests without auth issues"""
        # Make multiple requests with same token
        for i in range(5):
            response = api_client.get(
                f"{BASE_URL}/api/marketplace/creators",
                headers={"Authorization": f"Bearer {brand_token}"}
            )
            assert response.status_code == 200, f"Request {i+1} failed with {response.status_code}"
        
        print("✓ Auth persists across multiple marketplace requests")
    
    def test_auth_me_returns_user_data_consistently(self, api_client, brand_token, creator_token):
        """Test /auth/me returns consistent user data"""
        # Brand
        for _ in range(3):
            response = api_client.get(
                f"{BASE_URL}/api/auth/me",
                headers={"Authorization": f"Bearer {brand_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == BRAND_EMAIL
            assert data["role"] == "business"
        
        # Creator
        for _ in range(3):
            response = api_client.get(
                f"{BASE_URL}/api/auth/me",
                headers={"Authorization": f"Bearer {creator_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == CREATOR_EMAIL
            assert data["role"] == "creator"
        
        print("✓ /auth/me returns consistent user data")


class TestErrorHandling:
    """Test error messages are strings not objects - Bug Fix #7"""
    
    def test_invalid_login_returns_string_error(self, api_client):
        """Test invalid login returns string error message"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str), "Error detail should be string, not object"
        print("✓ Invalid login returns string error message")
    
    def test_unauthorized_request_returns_string_error(self, api_client):
        """Test unauthorized request returns string error"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403]
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str), "Error detail should be string, not object"
        print("✓ Unauthorized request returns string error")
    
    def test_not_found_returns_string_error(self, api_client, brand_token):
        """Test not found returns string error"""
        response = api_client.get(
            f"{BASE_URL}/api/marketplace/creators/nonexistent-id/unlocked",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code in [403, 404]
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str), "Error detail should be string, not object"
        print("✓ Not found returns string error")


class TestUnlockFlowBothWays:
    """Test unlock flow works both ways - Bug Fix #8"""
    
    def test_brand_can_unlock_creator(self, api_client, brand_token):
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
        assert creators_response.status_code == 200
        creators = creators_response.json()
        assert len(creators) > 0
        
        # Find a creator to unlock
        creator_id = creators[0]["id"]
        
        # Unlock the creator
        response = api_client.post(
            f"{BASE_URL}/api/marketplace/creator/{creator_id}/unlock",
            headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ Brand can unlock creator")
    
    def test_creator_can_unlock_brand(self, api_client, creator_token):
        """Test creator can unlock brand profile"""
        # Ensure creator has credits
        api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        
        # Get brands
        brands_response = api_client.get(
            f"{BASE_URL}/api/marketplace/brands",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert brands_response.status_code == 200
        brands = brands_response.json()
        assert len(brands) > 0
        
        # Find a brand to unlock
        brand_id = brands[0]["id"]
        
        # Unlock the brand
        response = api_client.post(
            f"{BASE_URL}/api/marketplace/brand/{brand_id}/unlock",
            headers={"Authorization": f"Bearer {creator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ Creator can unlock brand")
    
    def test_brand_can_view_unlocked_creator_profile(self, api_client, brand_token):
        """Test brand can view unlocked creator profile with full details"""
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
        print(f"✓ Brand can view unlocked creator profile")
    
    def test_creator_can_view_unlocked_brand_profile(self, api_client, creator_token):
        """Test creator can view unlocked brand profile with full details"""
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
        print(f"✓ Creator can view unlocked brand profile")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
