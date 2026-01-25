"""
Orange V2 - Creator-Brand Marketplace Campaign Flow Tests
Tests bidirectional collaboration flows: Brand→Creator and Creator→Brand
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://brand-connect-66.preview.emergentagent.com').rstrip('/')

# Test credentials from seed data
BRAND1_EMAIL = "brand1@orange.com"
BRAND1_PASSWORD = "password123"
CREATOR1_EMAIL = "creator1@orange.com"
CREATOR1_PASSWORD = "password123"
CREATOR2_EMAIL = "creator2@orange.com"
CREATOR2_PASSWORD = "password123"


class TestSetup:
    """Setup tests - seed database and verify basic connectivity"""
    
    def test_seed_database(self):
        """Seed database with test data"""
        response = requests.post(f"{BASE_URL}/api/seed")
        assert response.status_code == 200
        data = response.json()
        assert "creators" in data
        assert "brands" in data
        print(f"Seeded: {data['creators']} creators, {data['brands']} brands")
    
    def test_health_check(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/")
        # May return 404 if no root endpoint, but server should respond
        assert response.status_code in [200, 404, 405]


class TestAuthentication:
    """Authentication tests"""
    
    def test_brand_login(self):
        """Brand can login with seeded credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND1_EMAIL,
            "password": BRAND1_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "business"
        print(f"Brand logged in: {data['user']['email']}")
    
    def test_creator_login(self):
        """Creator can login with seeded credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR1_EMAIL,
            "password": CREATOR1_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "creator"
        print(f"Creator logged in: {data['user']['email']}")


class TestMarketplaceDiscovery:
    """Marketplace discovery tests - both directions"""
    
    @pytest.fixture
    def brand_token(self):
        """Get brand auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND1_EMAIL,
            "password": BRAND1_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def creator_token(self):
        """Get creator auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR1_EMAIL,
            "password": CREATOR1_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_brand_discovers_creators(self, brand_token):
        """Brand can see creators in marketplace (anonymous - no names/Instagram)"""
        headers = {"Authorization": f"Bearer {brand_token}"}
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers=headers)
        assert response.status_code == 200
        creators = response.json()
        assert isinstance(creators, list)
        assert len(creators) > 0
        
        # Verify anonymous - no name or Instagram shown
        for creator in creators:
            assert "id" in creator
            assert "niche" in creator
            assert "reelPrice" in creator
            # Should NOT have name or Instagram in discovery
            assert "name" not in creator or creator.get("name") is None
            assert "instagramUsername" not in creator or creator.get("instagramUsername") is None
        
        print(f"Brand found {len(creators)} creators in marketplace")
        return creators
    
    def test_creator_discovers_brands(self, creator_token):
        """Creator can see brands in marketplace (anonymous - industry only)"""
        headers = {"Authorization": f"Bearer {creator_token}"}
        response = requests.get(f"{BASE_URL}/api/marketplace/brands", headers=headers)
        assert response.status_code == 200
        brands = response.json()
        assert isinstance(brands, list)
        assert len(brands) > 0
        
        # Verify anonymous - no brand name or Instagram shown
        for brand in brands:
            assert "id" in brand
            assert "industry" in brand
            # Should NOT have brandName or Instagram in discovery
            assert "brandName" not in brand or brand.get("brandName") is None
            assert "instagramUsername" not in brand or brand.get("instagramUsername") is None
        
        print(f"Creator found {len(brands)} brands in marketplace")
        return brands


class TestBrandToCreatorFlow:
    """Test Brand→Creator collaboration flow"""
    
    @pytest.fixture
    def brand_session(self):
        """Get brand auth token and profile"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND1_EMAIL,
            "password": BRAND1_PASSWORD
        })
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        return {"token": token, "headers": headers}
    
    @pytest.fixture
    def creator_session(self):
        """Get creator auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR1_EMAIL,
            "password": CREATOR1_PASSWORD
        })
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        return {"token": token, "headers": headers}
    
    def test_brand_sends_request_to_creator(self, brand_session, creator_session):
        """Brand can click on creator card and send paid collaboration request"""
        # Step 1: Brand discovers creators
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers=brand_session["headers"])
        assert response.status_code == 200
        creators = response.json()
        assert len(creators) > 0
        
        target_creator = creators[0]
        creator_id = target_creator["id"]
        print(f"Brand targeting creator: {creator_id}")
        
        # Step 2: Brand sends collaboration request
        campaign_data = {
            "receiverId": creator_id,
            "receiverType": "creator",
            "campaignType": "paid",
            "deliverables": "1 Reel + 2 Stories",
            "budget": 15000,
            "timeline": "7 days",
            "brief": "Product showcase for our new collection"
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=brand_session["headers"])
        assert response.status_code == 201
        campaign = response.json()
        
        assert campaign["status"] == "requested"
        assert campaign["senderType"] == "business"
        assert campaign["receiverType"] == "creator"
        assert campaign["budget"] == 15000
        assert campaign["identityUnlocked"] == False
        
        print(f"Campaign created: {campaign['id']}, status: {campaign['status']}")
        return campaign
    
    def test_creator_receives_incoming_request(self, brand_session, creator_session):
        """Creator receives incoming request from brand"""
        # First create a campaign
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers=brand_session["headers"])
        creators = response.json()
        creator_id = creators[0]["id"]
        
        campaign_data = {
            "receiverId": creator_id,
            "receiverType": "creator",
            "campaignType": "paid",
            "deliverables": "Test deliverables",
            "budget": 10000,
            "timeline": "5 days"
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=brand_session["headers"])
        assert response.status_code == 201
        
        # Creator checks incoming requests
        response = requests.get(f"{BASE_URL}/api/campaigns/incoming", headers=creator_session["headers"])
        assert response.status_code == 200
        incoming = response.json()
        
        # Should have at least one incoming request
        assert len(incoming) > 0
        print(f"Creator has {len(incoming)} incoming requests")
        
        # Verify request details
        latest = incoming[0]
        assert latest["status"] == "requested"
        assert latest["receiverType"] == "creator"
        return incoming
    
    def test_creator_accepts_request(self, brand_session, creator_session):
        """Creator can accept collaboration request"""
        # Create campaign
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers=brand_session["headers"])
        creators = response.json()
        creator_id = creators[0]["id"]
        
        campaign_data = {
            "receiverId": creator_id,
            "receiverType": "creator",
            "campaignType": "paid",
            "deliverables": "Accept test",
            "budget": 12000
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=brand_session["headers"])
        campaign = response.json()
        campaign_id = campaign["id"]
        
        # Creator accepts
        response = requests.patch(f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept", headers=creator_session["headers"])
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "accepted"
        print(f"Creator accepted campaign: {campaign_id}")
        return campaign_id
    
    def test_brand_pays_after_acceptance(self, brand_session, creator_session):
        """After acceptance, brand can pay and proceed"""
        # Create and accept campaign
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers=brand_session["headers"])
        creators = response.json()
        creator_id = creators[0]["id"]
        
        campaign_data = {
            "receiverId": creator_id,
            "receiverType": "creator",
            "campaignType": "paid",
            "deliverables": "Payment test",
            "budget": 20000
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=brand_session["headers"])
        campaign = response.json()
        campaign_id = campaign["id"]
        
        # Creator accepts
        requests.patch(f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept", headers=creator_session["headers"])
        
        # Brand pays
        response = requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/pay", headers=brand_session["headers"])
        assert response.status_code == 200
        result = response.json()
        
        assert result["success"] == True
        assert result["status"] == "paid"
        assert result["chatEnabled"] == True
        # For paid collabs, identity should unlock after payment
        assert result["identityUnlocked"] == True
        
        print(f"Brand paid for campaign: {campaign_id}, identity unlocked: {result['identityUnlocked']}")
        return campaign_id
    
    def test_creator_submits_link(self, brand_session, creator_session):
        """After payment, creator can submit reel/story link"""
        # Create, accept, and pay for campaign
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers=brand_session["headers"])
        creators = response.json()
        creator_id = creators[0]["id"]
        
        campaign_data = {
            "receiverId": creator_id,
            "receiverType": "creator",
            "campaignType": "paid",
            "deliverables": "Link submission test",
            "budget": 15000
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=brand_session["headers"])
        campaign = response.json()
        campaign_id = campaign["id"]
        
        requests.patch(f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept", headers=creator_session["headers"])
        requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/pay", headers=brand_session["headers"])
        
        # Creator submits link
        content_link = "https://instagram.com/reel/test123"
        response = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/submit-link?contentLink={content_link}",
            headers=creator_session["headers"]
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        assert result["contentLink"] == content_link
        
        print(f"Creator submitted link: {content_link}")
        return campaign_id
    
    def test_brand_verifies_link(self, brand_session, creator_session):
        """Brand can verify link"""
        # Full flow up to link submission
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers=brand_session["headers"])
        creators = response.json()
        creator_id = creators[0]["id"]
        
        campaign_data = {
            "receiverId": creator_id,
            "receiverType": "creator",
            "campaignType": "paid",
            "deliverables": "Verify link test",
            "budget": 18000
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=brand_session["headers"])
        campaign = response.json()
        campaign_id = campaign["id"]
        
        requests.patch(f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept", headers=creator_session["headers"])
        requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/pay", headers=brand_session["headers"])
        requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/submit-link?contentLink=https://instagram.com/reel/verify123", headers=creator_session["headers"])
        
        # Brand verifies link
        response = requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/verify-link", headers=brand_session["headers"])
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        assert result["linkVerified"] == True
        
        print(f"Brand verified link for campaign: {campaign_id}")
        return campaign_id
    
    def test_brand_completes_campaign(self, brand_session, creator_session):
        """Brand can complete campaign after verification"""
        # Full flow up to link verification
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers=brand_session["headers"])
        creators = response.json()
        creator_id = creators[0]["id"]
        
        campaign_data = {
            "receiverId": creator_id,
            "receiverType": "creator",
            "campaignType": "paid",
            "deliverables": "Complete campaign test",
            "budget": 25000
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=brand_session["headers"])
        campaign = response.json()
        campaign_id = campaign["id"]
        
        requests.patch(f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept", headers=creator_session["headers"])
        requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/pay", headers=brand_session["headers"])
        requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/submit-link?contentLink=https://instagram.com/reel/complete123", headers=creator_session["headers"])
        requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/verify-link", headers=brand_session["headers"])
        
        # Brand completes campaign
        response = requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/complete", headers=brand_session["headers"])
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        assert result["status"] == "completed"
        
        print(f"Campaign completed: {campaign_id}")
        return campaign_id
    
    def test_both_parties_can_rate(self, brand_session, creator_session):
        """Both parties can rate after completion"""
        # Full flow to completion
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers=brand_session["headers"])
        creators = response.json()
        creator_id = creators[0]["id"]
        
        campaign_data = {
            "receiverId": creator_id,
            "receiverType": "creator",
            "campaignType": "paid",
            "deliverables": "Rating test",
            "budget": 22000
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=brand_session["headers"])
        campaign = response.json()
        campaign_id = campaign["id"]
        
        requests.patch(f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept", headers=creator_session["headers"])
        requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/pay", headers=brand_session["headers"])
        requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/submit-link?contentLink=https://instagram.com/reel/rate123", headers=creator_session["headers"])
        requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/verify-link", headers=brand_session["headers"])
        requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/complete", headers=brand_session["headers"])
        
        # Brand rates creator
        response = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/rate?rating=5&feedback=Excellent%20work%20by%20the%20creator",
            headers=brand_session["headers"]
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        print(f"Brand rated creator: 5 stars")
        
        # Creator rates brand
        response = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/rate?rating=4&feedback=Great%20brand%20to%20work%20with",
            headers=creator_session["headers"]
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] == True
        print(f"Creator rated brand: 4 stars")


class TestCreatorToBrandFlow:
    """Test Creator→Brand collaboration flow"""
    
    @pytest.fixture
    def brand_session(self):
        """Get brand auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND1_EMAIL,
            "password": BRAND1_PASSWORD
        })
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        return {"token": token, "headers": headers}
    
    @pytest.fixture
    def creator_session(self):
        """Get creator auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR1_EMAIL,
            "password": CREATOR1_PASSWORD
        })
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        return {"token": token, "headers": headers}
    
    def test_creator_sends_request_to_brand(self, creator_session, brand_session):
        """Creator can click on brand card and send paid collaboration request"""
        # Step 1: Creator discovers brands
        response = requests.get(f"{BASE_URL}/api/marketplace/brands", headers=creator_session["headers"])
        assert response.status_code == 200
        brands = response.json()
        assert len(brands) > 0
        
        target_brand = brands[0]
        brand_id = target_brand["id"]
        print(f"Creator targeting brand: {brand_id}")
        
        # Step 2: Creator sends collaboration request
        campaign_data = {
            "receiverId": brand_id,
            "receiverType": "brand",
            "campaignType": "paid",
            "deliverables": "I will create 2 reels and 3 stories",
            "budget": 20000,
            "timeline": "10 days",
            "brief": "Looking to collaborate on your products"
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=creator_session["headers"])
        assert response.status_code == 201
        campaign = response.json()
        
        assert campaign["status"] == "requested"
        assert campaign["senderType"] == "creator"
        assert campaign["receiverType"] == "brand"
        assert campaign["budget"] == 20000
        
        print(f"Creator sent request to brand: {campaign['id']}")
        return campaign
    
    def test_brand_receives_incoming_request_from_creator(self, creator_session, brand_session):
        """Brand receives incoming request from creator"""
        # Creator sends request
        response = requests.get(f"{BASE_URL}/api/marketplace/brands", headers=creator_session["headers"])
        brands = response.json()
        brand_id = brands[0]["id"]
        
        campaign_data = {
            "receiverId": brand_id,
            "receiverType": "brand",
            "campaignType": "paid",
            "deliverables": "Creator to brand test",
            "budget": 15000
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=creator_session["headers"])
        assert response.status_code == 201
        
        # Brand checks incoming requests
        response = requests.get(f"{BASE_URL}/api/campaigns/incoming", headers=brand_session["headers"])
        assert response.status_code == 200
        incoming = response.json()
        
        # Should have incoming requests from creators
        creator_requests = [c for c in incoming if c["senderType"] == "creator"]
        assert len(creator_requests) > 0
        print(f"Brand has {len(creator_requests)} incoming requests from creators")
        return incoming
    
    def test_brand_accepts_creator_request(self, creator_session, brand_session):
        """Brand can accept collaboration request from creator"""
        # Creator sends request
        response = requests.get(f"{BASE_URL}/api/marketplace/brands", headers=creator_session["headers"])
        brands = response.json()
        brand_id = brands[0]["id"]
        
        campaign_data = {
            "receiverId": brand_id,
            "receiverType": "brand",
            "campaignType": "paid",
            "deliverables": "Brand accept test",
            "budget": 18000
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=creator_session["headers"])
        campaign = response.json()
        campaign_id = campaign["id"]
        
        # Brand accepts
        response = requests.patch(f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept", headers=brand_session["headers"])
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "accepted"
        print(f"Brand accepted creator's request: {campaign_id}")
        return campaign_id
    
    def test_creator_pays_after_brand_accepts(self, creator_session, brand_session):
        """After brand accepts, creator (sender) pays"""
        # Creator sends request
        response = requests.get(f"{BASE_URL}/api/marketplace/brands", headers=creator_session["headers"])
        brands = response.json()
        brand_id = brands[0]["id"]
        
        campaign_data = {
            "receiverId": brand_id,
            "receiverType": "brand",
            "campaignType": "paid",
            "deliverables": "Creator pays test",
            "budget": 25000
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=creator_session["headers"])
        campaign = response.json()
        campaign_id = campaign["id"]
        
        # Brand accepts
        requests.patch(f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept", headers=brand_session["headers"])
        
        # Creator (sender) pays
        response = requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/pay", headers=creator_session["headers"])
        assert response.status_code == 200
        result = response.json()
        
        assert result["success"] == True
        assert result["status"] == "paid"
        assert result["chatEnabled"] == True
        
        print(f"Creator paid for campaign: {campaign_id}")
        return campaign_id
    
    def test_full_creator_to_brand_flow(self, creator_session, brand_session):
        """Complete Creator→Brand flow: request → accept → pay → submit → verify → complete → rate"""
        # 1. Creator discovers brands
        response = requests.get(f"{BASE_URL}/api/marketplace/brands", headers=creator_session["headers"])
        brands = response.json()
        brand_id = brands[0]["id"]
        
        # 2. Creator sends request
        campaign_data = {
            "receiverId": brand_id,
            "receiverType": "brand",
            "campaignType": "paid",
            "deliverables": "Full flow test - 2 reels",
            "budget": 30000,
            "timeline": "14 days"
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=creator_session["headers"])
        assert response.status_code == 201
        campaign = response.json()
        campaign_id = campaign["id"]
        print(f"Step 1: Creator sent request - {campaign_id}")
        
        # 3. Brand accepts
        response = requests.patch(f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept", headers=brand_session["headers"])
        assert response.status_code == 200
        print("Step 2: Brand accepted")
        
        # 4. Creator pays
        response = requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/pay", headers=creator_session["headers"])
        assert response.status_code == 200
        print("Step 3: Creator paid")
        
        # 5. Creator submits link
        response = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/submit-link?contentLink=https://instagram.com/reel/fullflow123",
            headers=creator_session["headers"]
        )
        assert response.status_code == 200
        print("Step 4: Creator submitted link")
        
        # 6. Brand verifies link
        response = requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/verify-link", headers=brand_session["headers"])
        assert response.status_code == 200
        print("Step 5: Brand verified link")
        
        # 7. Brand completes
        response = requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/complete", headers=brand_session["headers"])
        assert response.status_code == 200
        print("Step 6: Brand completed campaign")
        
        # 8. Both rate
        response = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/rate?rating=5&feedback=Amazing%20collaboration%20experience",
            headers=creator_session["headers"]
        )
        assert response.status_code == 200
        print("Step 7: Creator rated brand")
        
        response = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/rate?rating=5&feedback=Professional%20creator%20highly%20recommend",
            headers=brand_session["headers"]
        )
        assert response.status_code == 200
        print("Step 8: Brand rated creator")
        
        print(f"FULL CREATOR→BRAND FLOW COMPLETED: {campaign_id}")


class TestBarterFlow:
    """Test barter collaboration flow"""
    
    @pytest.fixture
    def brand_session(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND1_EMAIL,
            "password": BRAND1_PASSWORD
        })
        token = response.json()["access_token"]
        return {"headers": {"Authorization": f"Bearer {token}"}}
    
    @pytest.fixture
    def creator_session(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR1_EMAIL,
            "password": CREATOR1_PASSWORD
        })
        token = response.json()["access_token"]
        return {"headers": {"Authorization": f"Bearer {token}"}}
    
    def test_barter_product_flow(self, brand_session, creator_session):
        """Test barter product collaboration"""
        # Get creator
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers=brand_session["headers"])
        creators = response.json()
        creator_id = creators[0]["id"]
        
        # Brand sends barter request
        campaign_data = {
            "receiverId": creator_id,
            "receiverType": "creator",
            "campaignType": "barter_product",
            "deliverables": "1 Reel featuring our product",
            "productValue": 5000,
            "barterDetails": "Premium skincare set worth ₹5000",
            "timeline": "14 days"
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=brand_session["headers"])
        assert response.status_code == 201
        campaign = response.json()
        campaign_id = campaign["id"]
        
        assert campaign["campaignType"] == "barter_product"
        assert campaign["productValue"] == 5000
        assert campaign["barterFee"] == 500  # 10% of product value
        
        print(f"Barter campaign created: {campaign_id}, fee: {campaign['barterFee']}")
        
        # Creator accepts
        requests.patch(f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=accept", headers=creator_session["headers"])
        
        # Brand pays barter fee
        response = requests.post(f"{BASE_URL}/api/campaigns/{campaign_id}/pay", headers=brand_session["headers"])
        assert response.status_code == 200
        result = response.json()
        
        # For barter, identity should NOT unlock until link verification
        assert result["identityUnlocked"] == False
        assert result["chatEnabled"] == True
        
        print(f"Barter fee paid, identity locked until verification")
        return campaign_id


class TestRejectFlow:
    """Test rejection scenarios"""
    
    @pytest.fixture
    def brand_session(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND1_EMAIL,
            "password": BRAND1_PASSWORD
        })
        token = response.json()["access_token"]
        return {"headers": {"Authorization": f"Bearer {token}"}}
    
    @pytest.fixture
    def creator_session(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR1_EMAIL,
            "password": CREATOR1_PASSWORD
        })
        token = response.json()["access_token"]
        return {"headers": {"Authorization": f"Bearer {token}"}}
    
    def test_creator_rejects_brand_request(self, brand_session, creator_session):
        """Creator can reject brand's request"""
        # Brand sends request
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers=brand_session["headers"])
        creators = response.json()
        creator_id = creators[0]["id"]
        
        campaign_data = {
            "receiverId": creator_id,
            "receiverType": "creator",
            "campaignType": "paid",
            "deliverables": "Reject test",
            "budget": 10000
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=brand_session["headers"])
        campaign = response.json()
        campaign_id = campaign["id"]
        
        # Creator rejects
        response = requests.patch(f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=reject", headers=creator_session["headers"])
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "cancelled"
        
        print(f"Creator rejected request: {campaign_id}")
    
    def test_brand_rejects_creator_request(self, brand_session, creator_session):
        """Brand can reject creator's request"""
        # Creator sends request
        response = requests.get(f"{BASE_URL}/api/marketplace/brands", headers=creator_session["headers"])
        brands = response.json()
        brand_id = brands[0]["id"]
        
        campaign_data = {
            "receiverId": brand_id,
            "receiverType": "brand",
            "campaignType": "paid",
            "deliverables": "Brand reject test",
            "budget": 12000
        }
        
        response = requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=creator_session["headers"])
        campaign = response.json()
        campaign_id = campaign["id"]
        
        # Brand rejects
        response = requests.patch(f"{BASE_URL}/api/campaigns/{campaign_id}/respond?action=reject", headers=brand_session["headers"])
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "cancelled"
        
        print(f"Brand rejected creator's request: {campaign_id}")


class TestOutgoingCampaigns:
    """Test outgoing campaigns tracking"""
    
    @pytest.fixture
    def brand_session(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BRAND1_EMAIL,
            "password": BRAND1_PASSWORD
        })
        token = response.json()["access_token"]
        return {"headers": {"Authorization": f"Bearer {token}"}}
    
    @pytest.fixture
    def creator_session(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR1_EMAIL,
            "password": CREATOR1_PASSWORD
        })
        token = response.json()["access_token"]
        return {"headers": {"Authorization": f"Bearer {token}"}}
    
    def test_brand_sees_outgoing_campaigns(self, brand_session, creator_session):
        """Brand can see their sent campaigns"""
        # Create a campaign
        response = requests.get(f"{BASE_URL}/api/marketplace/creators", headers=brand_session["headers"])
        creators = response.json()
        creator_id = creators[0]["id"]
        
        campaign_data = {
            "receiverId": creator_id,
            "receiverType": "creator",
            "campaignType": "paid",
            "deliverables": "Outgoing test",
            "budget": 15000
        }
        
        requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=brand_session["headers"])
        
        # Check outgoing
        response = requests.get(f"{BASE_URL}/api/campaigns/outgoing", headers=brand_session["headers"])
        assert response.status_code == 200
        outgoing = response.json()
        assert len(outgoing) > 0
        print(f"Brand has {len(outgoing)} outgoing campaigns")
    
    def test_creator_sees_outgoing_campaigns(self, brand_session, creator_session):
        """Creator can see their sent campaigns"""
        # Create a campaign
        response = requests.get(f"{BASE_URL}/api/marketplace/brands", headers=creator_session["headers"])
        brands = response.json()
        brand_id = brands[0]["id"]
        
        campaign_data = {
            "receiverId": brand_id,
            "receiverType": "brand",
            "campaignType": "paid",
            "deliverables": "Creator outgoing test",
            "budget": 20000
        }
        
        requests.post(f"{BASE_URL}/api/campaigns/", json=campaign_data, headers=creator_session["headers"])
        
        # Check outgoing
        response = requests.get(f"{BASE_URL}/api/campaigns/outgoing", headers=creator_session["headers"])
        assert response.status_code == 200
        outgoing = response.json()
        assert len(outgoing) > 0
        print(f"Creator has {len(outgoing)} outgoing campaigns")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
