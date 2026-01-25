"""
Test Suite for Orange V2 Campaign Flow
Tests the complete collaboration lifecycle:
1. Authentication (brand and creator login)
2. Marketplace discovery (partial data only - no names/Instagram)
3. Campaign request (brand sends to creator)
4. Creator accepts/rejects
5. Payment flow (escrow for paid, barter fee for barter)
6. Identity unlock (paid = after payment, barter = after link verification)
7. Link submission and verification
8. Campaign completion and ratings
9. Chat functionality (only after payment)
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://brand-connect-66.preview.emergentagent.com').rstrip('/')

# Test credentials
BRAND_EMAIL = "brand1@orange.com"
BRAND_PASSWORD = "password123"
CREATOR_EMAIL = "creator1@orange.com"
CREATOR_PASSWORD = "password123"
CREATOR2_EMAIL = "creator2@orange.com"
CREATOR2_PASSWORD = "password123"


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_brand_login(self):
        """Brand can login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND_EMAIL,
            "password": BRAND_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "business"
        assert data["user"]["hasCompletedOnboarding"] == True
        print(f"✓ Brand login successful: {data['user']['email']}")
    
    def test_creator_login(self):
        """Creator can login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR_EMAIL,
            "password": CREATOR_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "creator"
        print(f"✓ Creator login successful: {data['user']['email']}")
    
    def test_invalid_login(self):
        """Invalid credentials return 401"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@email.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid login rejected with 401")
    
    def test_auth_me_endpoint(self):
        """Authenticated user can get their info"""
        # Login first
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND_EMAIL,
            "password": BRAND_PASSWORD
        })
        token = login_res.json()["access_token"]
        
        # Get user info
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == BRAND_EMAIL
        print(f"✓ /auth/me returns correct user: {data['email']}")


class TestMarketplaceDiscovery:
    """Test marketplace discovery - partial data only (no names/Instagram)"""
    
    @pytest.fixture
    def brand_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND_EMAIL,
            "password": BRAND_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def creator_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR_EMAIL,
            "password": CREATOR_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_brand_discovers_creators_partial_data(self, brand_token):
        """Brand sees creators with partial data only - NO names or Instagram"""
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_token}"
        })
        assert response.status_code == 200
        creators = response.json()
        assert len(creators) > 0
        
        # Verify partial data - should have niche, price, location but NO name/instagram
        creator = creators[0]
        assert "id" in creator
        assert "niche" in creator
        assert "reelPrice" in creator
        assert "location" in creator
        assert "engagementRate" in creator
        
        # These should NOT be in discovery response
        assert "name" not in creator, "Name should be hidden in discovery"
        assert "instagramUsername" not in creator, "Instagram should be hidden in discovery"
        assert "instagramHandle" not in creator, "Instagram handle should be hidden"
        
        print(f"✓ Brand discovers {len(creators)} creators with partial data (no names/Instagram)")
    
    def test_creator_discovers_brands_partial_data(self, creator_token):
        """Creator sees brands with partial data only - NO brand names or Instagram"""
        response = requests.get(f"{BASE_URL}/api/marketplace/brands", headers={
            "Authorization": f"Bearer {creator_token}"
        })
        assert response.status_code == 200
        brands = response.json()
        
        if len(brands) > 0:
            brand = brands[0]
            assert "id" in brand
            assert "industry" in brand
            assert "location" in brand
            
            # These should NOT be in discovery response
            assert "brandName" not in brand, "Brand name should be hidden in discovery"
            assert "instagramUsername" not in brand, "Instagram should be hidden"
            
            print(f"✓ Creator discovers {len(brands)} brands with partial data")
        else:
            print("✓ No brands in marketplace (expected if no verified brands)")


class TestCampaignRequestFlow:
    """Test campaign request flow - brand sends request to creator"""
    
    @pytest.fixture
    def brand_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND_EMAIL,
            "password": BRAND_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    @pytest.fixture
    def creator_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR_EMAIL,
            "password": CREATOR_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    @pytest.fixture
    def creator_profile_id(self, brand_auth):
        """Get first creator profile ID from marketplace"""
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        creators = response.json()
        return creators[0]["id"] if creators else None
    
    def test_brand_sends_paid_campaign_request(self, brand_auth, creator_profile_id):
        """Brand can send a paid campaign request to creator"""
        if not creator_profile_id:
            pytest.skip("No creators in marketplace")
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creator_profile_id,
                "receiverType": "creator",
                "campaignType": "paid",
                "deliverables": "1 Reel + 2 Stories",
                "budget": 15000,
                "timeline": "1 week",
                "brief": "Product showcase for our new collection"
            }
        )
        assert response.status_code == 201
        campaign = response.json()
        
        assert campaign["status"] == "requested"
        assert campaign["campaignType"] == "paid"
        assert campaign["budget"] == 15000
        assert campaign["identityUnlocked"] == False
        assert campaign["chatEnabled"] == False
        
        # Verify identity is masked
        assert campaign["receiverName"] == "Creator", "Receiver name should be masked"
        assert campaign["receiverInstagram"] is None, "Instagram should be hidden"
        
        print(f"✓ Brand sent paid campaign request (ID: {campaign['id']})")
        return campaign["id"]
    
    def test_brand_sends_barter_campaign_request(self, brand_auth, creator_profile_id):
        """Brand can send a barter campaign request to creator"""
        if not creator_profile_id:
            pytest.skip("No creators in marketplace")
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creator_profile_id,
                "receiverType": "creator",
                "campaignType": "barter_product",
                "deliverables": "1 Reel",
                "productValue": 5000,
                "barterDetails": "Premium skincare set worth ₹5000",
                "timeline": "2 weeks"
            }
        )
        assert response.status_code == 201
        campaign = response.json()
        
        assert campaign["status"] == "requested"
        assert campaign["campaignType"] == "barter_product"
        assert campaign["productValue"] == 5000
        assert campaign["barterFee"] == 500  # 10% of product value
        
        print(f"✓ Brand sent barter campaign request (ID: {campaign['id']})")
        return campaign["id"]
    
    def test_creator_sees_incoming_requests(self, creator_auth):
        """Creator can see incoming campaign requests"""
        response = requests.get(f"{BASE_URL}/api/campaigns/incoming", headers={
            "Authorization": f"Bearer {creator_auth['token']}"
        })
        assert response.status_code == 200
        campaigns = response.json()
        
        # Should have at least the requests we just created
        print(f"✓ Creator sees {len(campaigns)} incoming requests")
    
    def test_brand_sees_outgoing_requests(self, brand_auth):
        """Brand can see outgoing campaign requests"""
        response = requests.get(f"{BASE_URL}/api/campaigns/outgoing", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        assert response.status_code == 200
        campaigns = response.json()
        
        print(f"✓ Brand sees {len(campaigns)} outgoing requests")


class TestCampaignAcceptRejectFlow:
    """Test creator accepting/rejecting campaign requests"""
    
    @pytest.fixture
    def brand_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND_EMAIL,
            "password": BRAND_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    @pytest.fixture
    def creator_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR_EMAIL,
            "password": CREATOR_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    @pytest.fixture
    def new_campaign(self, brand_auth):
        """Create a fresh campaign for testing"""
        # Get creator ID
        creators_res = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        creators = creators_res.json()
        if not creators:
            pytest.skip("No creators available")
        
        # Create campaign
        response = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creators[0]["id"],
                "receiverType": "creator",
                "campaignType": "paid",
                "deliverables": f"Test campaign {uuid.uuid4().hex[:8]}",
                "budget": 10000,
                "timeline": "1 week"
            }
        )
        return response.json()
    
    def test_creator_accepts_request(self, creator_auth, new_campaign):
        """Creator can accept a campaign request"""
        campaign_id = new_campaign["id"]
        
        response = requests.patch(
            f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        
        print(f"✓ Creator accepted campaign {campaign_id}")
    
    def test_creator_rejects_request(self, brand_auth, creator_auth):
        """Creator can reject a campaign request"""
        # Create a new campaign to reject
        creators_res = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        creators = creators_res.json()
        
        campaign_res = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creators[0]["id"],
                "receiverType": "creator",
                "campaignType": "paid",
                "deliverables": f"Reject test {uuid.uuid4().hex[:8]}",
                "budget": 5000
            }
        )
        campaign_id = campaign_res.json()["id"]
        
        # Reject it
        response = requests.patch(
            f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=reject",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        
        print(f"✓ Creator rejected campaign {campaign_id}")


class TestPaymentAndIdentityUnlock:
    """Test payment flow and identity unlock rules"""
    
    @pytest.fixture
    def brand_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND_EMAIL,
            "password": BRAND_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    @pytest.fixture
    def creator_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR_EMAIL,
            "password": CREATOR_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    def test_paid_collab_identity_unlocks_after_payment(self, brand_auth, creator_auth):
        """For PAID collabs: Identity unlocks immediately after payment"""
        # Get creator
        creators_res = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        creators = creators_res.json()
        
        # Create paid campaign
        campaign_res = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creators[0]["id"],
                "receiverType": "creator",
                "campaignType": "paid",
                "deliverables": f"Paid unlock test {uuid.uuid4().hex[:8]}",
                "budget": 15000
            }
        )
        campaign = campaign_res.json()
        campaign_id = campaign["id"]
        
        # Creator accepts
        requests.patch(
            f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        # Brand pays
        pay_res = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/pay",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        assert pay_res.status_code == 200
        pay_data = pay_res.json()
        
        assert pay_data["success"] == True
        assert pay_data["identityUnlocked"] == True, "Paid collab should unlock identity after payment"
        assert pay_data["chatEnabled"] == True
        
        # Verify campaign shows identity
        campaign_res = requests.get(
            f"{BASE_URL}/api/campaigns/{campaign_id}",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        campaign = campaign_res.json()
        assert campaign["identityUnlocked"] == True
        
        print(f"✓ Paid collab identity unlocked after payment")
    
    def test_barter_collab_identity_locked_after_payment(self, brand_auth, creator_auth):
        """For BARTER collabs: Identity stays locked after payment, unlocks after link verification"""
        # Get creator
        creators_res = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        creators = creators_res.json()
        
        # Create barter campaign
        campaign_res = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creators[0]["id"],
                "receiverType": "creator",
                "campaignType": "barter_product",
                "deliverables": f"Barter unlock test {uuid.uuid4().hex[:8]}",
                "productValue": 5000,
                "barterDetails": "Test product"
            }
        )
        campaign = campaign_res.json()
        campaign_id = campaign["id"]
        
        # Creator accepts
        requests.patch(
            f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        # Brand pays barter fee
        pay_res = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/pay",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        assert pay_res.status_code == 200
        pay_data = pay_res.json()
        
        assert pay_data["success"] == True
        assert pay_data["identityUnlocked"] == False, "Barter collab should NOT unlock identity after payment"
        assert pay_data["chatEnabled"] == True, "Chat should be enabled after payment"
        
        print(f"✓ Barter collab identity stays locked after payment (unlocks after link verification)")


class TestLinkSubmissionAndVerification:
    """Test link submission and verification flow"""
    
    @pytest.fixture
    def brand_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND_EMAIL,
            "password": BRAND_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    @pytest.fixture
    def creator_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR_EMAIL,
            "password": CREATOR_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    def test_creator_submits_link(self, brand_auth, creator_auth):
        """Creator can submit reel/story link after payment"""
        # Create and accept paid campaign
        creators_res = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        creators = creators_res.json()
        
        campaign_res = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creators[0]["id"],
                "receiverType": "creator",
                "campaignType": "paid",
                "deliverables": f"Link test {uuid.uuid4().hex[:8]}",
                "budget": 10000
            }
        )
        campaign_id = campaign_res.json()["id"]
        
        # Accept and pay
        requests.patch(
            f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/pay",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        # Creator submits link
        link_res = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/submit-link?contentLink=https://instagram.com/reel/test123",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        assert link_res.status_code == 200
        data = link_res.json()
        assert data["success"] == True
        
        # Verify campaign status
        campaign_res = requests.get(
            f"{BASE_URL}/api/campaigns/{campaign_id}",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        campaign = campaign_res.json()
        assert campaign["status"] == "link_submitted"
        assert campaign["contentLink"] == "https://instagram.com/reel/test123"
        
        print(f"✓ Creator submitted link successfully")
    
    def test_brand_verifies_link(self, brand_auth, creator_auth):
        """Brand can verify submitted link"""
        # Create full flow campaign
        creators_res = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        creators = creators_res.json()
        
        campaign_res = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creators[0]["id"],
                "receiverType": "creator",
                "campaignType": "paid",
                "deliverables": f"Verify test {uuid.uuid4().hex[:8]}",
                "budget": 10000
            }
        )
        campaign_id = campaign_res.json()["id"]
        
        # Accept, pay, submit link
        requests.patch(
            f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/pay",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/submit-link?contentLink=https://instagram.com/reel/verify123",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        # Brand verifies
        verify_res = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/verify-link",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        assert verify_res.status_code == 200
        data = verify_res.json()
        assert data["success"] == True
        assert data["linkVerified"] == True
        
        # Verify campaign status
        campaign_res = requests.get(
            f"{BASE_URL}/api/campaigns/{campaign_id}",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        campaign = campaign_res.json()
        assert campaign["status"] == "link_verified"
        
        print(f"✓ Brand verified link successfully")
    
    def test_barter_identity_unlocks_after_link_verification(self, brand_auth, creator_auth):
        """For BARTER: Identity unlocks after link verification"""
        # Create barter campaign
        creators_res = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        creators = creators_res.json()
        
        campaign_res = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creators[0]["id"],
                "receiverType": "creator",
                "campaignType": "barter_product",
                "deliverables": f"Barter verify test {uuid.uuid4().hex[:8]}",
                "productValue": 5000,
                "barterDetails": "Test product"
            }
        )
        campaign_id = campaign_res.json()["id"]
        
        # Accept, pay, submit link
        requests.patch(
            f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/pay",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/submit-link?contentLink=https://instagram.com/reel/barter123",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        # Brand verifies - this should unlock identity for barter
        verify_res = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/verify-link",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        assert verify_res.status_code == 200
        data = verify_res.json()
        assert data["identityUnlocked"] == True, "Barter identity should unlock after link verification"
        
        print(f"✓ Barter identity unlocked after link verification")


class TestCampaignCompletion:
    """Test campaign completion and ratings"""
    
    @pytest.fixture
    def brand_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND_EMAIL,
            "password": BRAND_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    @pytest.fixture
    def creator_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR_EMAIL,
            "password": CREATOR_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    def test_brand_completes_campaign(self, brand_auth, creator_auth):
        """Brand can mark campaign as complete after link verification"""
        # Create full flow campaign
        creators_res = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        creators = creators_res.json()
        
        campaign_res = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creators[0]["id"],
                "receiverType": "creator",
                "campaignType": "paid",
                "deliverables": f"Complete test {uuid.uuid4().hex[:8]}",
                "budget": 10000
            }
        )
        campaign_id = campaign_res.json()["id"]
        
        # Full flow: accept -> pay -> submit link -> verify
        requests.patch(
            f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/pay",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/submit-link?contentLink=https://instagram.com/reel/complete123",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/verify-link",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        # Complete campaign
        complete_res = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/complete",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        assert complete_res.status_code == 200
        data = complete_res.json()
        assert data["success"] == True
        
        # Verify status
        campaign_res = requests.get(
            f"{BASE_URL}/api/campaigns/{campaign_id}",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        campaign = campaign_res.json()
        assert campaign["status"] == "completed"
        
        print(f"✓ Campaign completed successfully")
    
    def test_rating_submission(self, brand_auth, creator_auth):
        """Both parties can submit ratings after completion"""
        # Create and complete campaign
        creators_res = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        creators = creators_res.json()
        
        campaign_res = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creators[0]["id"],
                "receiverType": "creator",
                "campaignType": "paid",
                "deliverables": f"Rating test {uuid.uuid4().hex[:8]}",
                "budget": 10000
            }
        )
        campaign_id = campaign_res.json()["id"]
        
        # Full flow
        requests.patch(
            f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/pay",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/submit-link?contentLink=https://instagram.com/reel/rate123",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/verify-link",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/complete",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        # Brand rates creator (uses query params, not JSON body)
        rate_res = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/rate?rating=5&feedback=Excellent%20work%21%20Great%20content%20quality%20and%20timely%20delivery.",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        assert rate_res.status_code == 200
        
        # Creator rates brand
        rate_res2 = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/rate?rating=4&feedback=Good%20collaboration%2C%20clear%20brief%20and%20prompt%20payment.",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        assert rate_res2.status_code == 200
        
        print(f"✓ Both parties submitted ratings successfully")


class TestChatFunctionality:
    """Test chat functionality - only available after payment"""
    
    @pytest.fixture
    def brand_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND_EMAIL,
            "password": BRAND_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    @pytest.fixture
    def creator_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR_EMAIL,
            "password": CREATOR_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    def test_chat_disabled_before_payment(self, brand_auth, creator_auth):
        """Chat should be disabled before payment"""
        # Create campaign
        creators_res = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        creators = creators_res.json()
        
        campaign_res = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creators[0]["id"],
                "receiverType": "creator",
                "campaignType": "paid",
                "deliverables": f"Chat test {uuid.uuid4().hex[:8]}",
                "budget": 10000
            }
        )
        campaign = campaign_res.json()
        assert campaign["chatEnabled"] == False
        
        # Accept but don't pay
        requests.patch(
            f"{BASE_URL}/api/campaigns/{campaign['id']}/respond?action=accept",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        # Try to send message - should fail
        msg_res = requests.post(
            f"{BASE_URL}/api/messages/{campaign['id']}",
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={"content": "Hello!"}
        )
        assert msg_res.status_code in [400, 403], "Chat should be disabled before payment"
        
        print(f"✓ Chat correctly disabled before payment")
    
    def test_chat_enabled_after_payment(self, brand_auth, creator_auth):
        """Chat should be enabled after payment"""
        # Create and pay for campaign
        creators_res = requests.get(f"{BASE_URL}/api/marketplace/creators", headers={
            "Authorization": f"Bearer {brand_auth['token']}"
        })
        creators = creators_res.json()
        
        campaign_res = requests.post(f"{BASE_URL}/api/campaigns/", 
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={
                "receiverId": creators[0]["id"],
                "receiverType": "creator",
                "campaignType": "paid",
                "deliverables": f"Chat enabled test {uuid.uuid4().hex[:8]}",
                "budget": 10000
            }
        )
        campaign_id = campaign_res.json()["id"]
        
        # Accept and pay
        requests.patch(
            f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        pay_res = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/pay",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        assert pay_res.json()["chatEnabled"] == True
        
        # Send message - should work (201 Created is correct)
        msg_res = requests.post(
            f"{BASE_URL}/api/messages/{campaign_id}",
            headers={"Authorization": f"Bearer {brand_auth['token']}"},
            json={"content": "Hello! Looking forward to working with you."}
        )
        assert msg_res.status_code in [200, 201], f"Expected 200 or 201, got {msg_res.status_code}"
        
        # Get messages
        get_msg_res = requests.get(
            f"{BASE_URL}/api/messages/{campaign_id}",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        assert get_msg_res.status_code == 200
        messages = get_msg_res.json()
        assert len(messages) > 0
        
        print(f"✓ Chat enabled and working after payment")


class TestCreatorVisibilityToggle:
    """Test creator visibility toggle (subscription mock)"""
    
    @pytest.fixture
    def creator_auth(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR_EMAIL,
            "password": CREATOR_PASSWORD
        })
        data = response.json()
        return {"token": data["access_token"], "user": data["user"]}
    
    def test_toggle_visibility_off(self, creator_auth):
        """Creator can toggle visibility off"""
        response = requests.post(
            f"{BASE_URL}/api/creator/subscription/toggle?visible=false",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["isVisible"] == False
        
        print(f"✓ Creator visibility toggled OFF")
    
    def test_toggle_visibility_on(self, creator_auth):
        """Creator can toggle visibility on"""
        response = requests.post(
            f"{BASE_URL}/api/creator/subscription/toggle?visible=true",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["isVisible"] == True
        
        print(f"✓ Creator visibility toggled ON")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
