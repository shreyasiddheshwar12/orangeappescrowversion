"""
Orange Creator Marketplace - Iteration 5 Request Flow Tests
Tests for critical end-to-end flow:
1. Brand sends campaign proposal (request) to creator
2. Creator sees incoming requests on dashboard
3. Creator can accept request - status updates
4. Creator can decline request - status updates
5. New brand signup with Instagram verification appears in creator marketplace
6. Request shows brand name, budget, deliverables, timeline
7. Request expires after 72 hours (expiry date shown)
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://creator-market-43.preview.emergentagent.com')

# Test credentials
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
def brand_auth(api_client):
    """Get brand authentication token and user info"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": BRAND_EMAIL,
        "password": BRAND_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return {
            "token": data.get("access_token"),
            "user": data.get("user")
        }
    pytest.skip("Brand authentication failed")


@pytest.fixture(scope="module")
def creator_auth(api_client):
    """Get creator authentication token and user info"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": CREATOR_EMAIL,
        "password": CREATOR_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return {
            "token": data.get("access_token"),
            "user": data.get("user")
        }
    pytest.skip("Creator authentication failed")


@pytest.fixture(scope="module")
def brand_profile(api_client, brand_auth):
    """Get brand profile"""
    response = api_client.get(
        f"{BASE_URL}/api/business/profile",
        headers={"Authorization": f"Bearer {brand_auth['token']}"}
    )
    if response.status_code == 200:
        return response.json()
    pytest.skip("Could not get brand profile")


@pytest.fixture(scope="module")
def creator_profile(api_client, creator_auth):
    """Get creator profile"""
    response = api_client.get(
        f"{BASE_URL}/api/creator/profile",
        headers={"Authorization": f"Bearer {creator_auth['token']}"}
    )
    if response.status_code == 200:
        return response.json()
    pytest.skip("Could not get creator profile")


class TestBrandSendsRequest:
    """Test Feature 1: Brand sends campaign proposal (request) to creator"""
    
    def test_brand_can_get_demo_credits(self, api_client, brand_auth):
        """Test brand can get demo credits for sending requests"""
        response = api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("✓ Brand can get demo credits")
    
    def test_brand_can_unlock_creator(self, api_client, brand_auth, creator_profile):
        """Test brand can unlock creator profile before sending request"""
        response = api_client.post(
            f"{BASE_URL}/api/marketplace/creator/{creator_profile['id']}/unlock",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Brand unlocked creator {creator_profile['id']}")
    
    def test_brand_sends_request_to_creator(self, api_client, brand_auth, creator_profile):
        """Test brand can send campaign proposal (request) to creator"""
        # Ensure brand has credits
        api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        request_data = {
            "receiverId": creator_profile["id"],
            "receiverType": "creator",
            "message": "We'd love to collaborate on our Summer 2025 campaign! Looking for authentic content.",
            "proposedBudget": 15000,
            "deliverables": "3 Reels, 5 Stories"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/requests/",
            json=request_data,
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify request data
        assert data.get("id") is not None
        assert data.get("status") == "pending"
        assert data.get("receiverId") == creator_profile["id"]
        assert data.get("receiverType") == "creator"
        assert data.get("proposedBudget") == 15000
        assert data.get("deliverables") == "3 Reels, 5 Stories"
        assert data.get("senderType") == "business"
        assert data.get("creditState") == "locked"
        
        print(f"✓ Brand sent request {data['id']} to creator")
        return data


class TestCreatorSeesRequests:
    """Test Feature 2: Creator sees incoming requests on dashboard"""
    
    def test_creator_can_fetch_incoming_requests(self, api_client, creator_auth):
        """Test creator can fetch incoming requests via /api/requests/incoming"""
        response = api_client.get(
            f"{BASE_URL}/api/requests/incoming",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Creator fetched {len(data)} incoming requests")
        return data
    
    def test_incoming_requests_have_required_fields(self, api_client, creator_auth):
        """Test incoming requests contain all required fields for display"""
        response = api_client.get(
            f"{BASE_URL}/api/requests/incoming",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        assert response.status_code == 200
        requests_list = response.json()
        
        if len(requests_list) == 0:
            pytest.skip("No incoming requests to verify")
        
        # Check first request has all required fields
        req = requests_list[0]
        required_fields = [
            "id", "senderName", "senderType", "receiverId", "receiverType",
            "message", "proposedBudget", "deliverables", "status", 
            "creditState", "expiresAt", "createdAt"
        ]
        
        for field in required_fields:
            assert field in req, f"Missing required field: {field}"
        
        print(f"✓ Incoming request has all required fields: {required_fields}")


class TestRequestShowsDetails:
    """Test Feature 6: Request shows brand name, budget, deliverables, timeline"""
    
    def test_request_shows_brand_name(self, api_client, creator_auth):
        """Test request shows sender (brand) name"""
        response = api_client.get(
            f"{BASE_URL}/api/requests/incoming",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        assert response.status_code == 200
        requests_list = response.json()
        
        if len(requests_list) == 0:
            pytest.skip("No incoming requests")
        
        req = requests_list[0]
        assert "senderName" in req
        assert req["senderName"] is not None
        assert len(req["senderName"]) > 0
        print(f"✓ Request shows brand name: {req['senderName']}")
    
    def test_request_shows_budget(self, api_client, creator_auth):
        """Test request shows proposed budget"""
        response = api_client.get(
            f"{BASE_URL}/api/requests/incoming",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        assert response.status_code == 200
        requests_list = response.json()
        
        if len(requests_list) == 0:
            pytest.skip("No incoming requests")
        
        req = requests_list[0]
        assert "proposedBudget" in req
        assert isinstance(req["proposedBudget"], (int, float))
        print(f"✓ Request shows budget: ₹{req['proposedBudget']}")
    
    def test_request_shows_deliverables(self, api_client, creator_auth):
        """Test request shows deliverables"""
        response = api_client.get(
            f"{BASE_URL}/api/requests/incoming",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        assert response.status_code == 200
        requests_list = response.json()
        
        if len(requests_list) == 0:
            pytest.skip("No incoming requests")
        
        req = requests_list[0]
        assert "deliverables" in req
        print(f"✓ Request shows deliverables: {req['deliverables']}")


class TestRequestExpiry:
    """Test Feature 7: Request expires after 72 hours (expiry date shown)"""
    
    def test_request_has_expiry_date(self, api_client, creator_auth):
        """Test request has expiresAt field"""
        response = api_client.get(
            f"{BASE_URL}/api/requests/incoming",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        assert response.status_code == 200
        requests_list = response.json()
        
        if len(requests_list) == 0:
            pytest.skip("No incoming requests")
        
        req = requests_list[0]
        assert "expiresAt" in req
        assert req["expiresAt"] is not None
        
        # Verify expiry is approximately 72 hours from creation
        created_at = datetime.fromisoformat(req["createdAt"].replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(req["expiresAt"].replace("Z", "+00:00"))
        
        # Should be approximately 72 hours (allow some tolerance)
        expected_expiry = created_at + timedelta(hours=72)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        
        assert time_diff < 60, f"Expiry should be ~72 hours from creation, diff: {time_diff}s"
        print(f"✓ Request expires at: {req['expiresAt']} (72 hours from creation)")


class TestCreatorAcceptsRequest:
    """Test Feature 3: Creator can accept request - status updates"""
    
    def test_creator_can_accept_request(self, api_client, brand_auth, creator_auth, creator_profile):
        """Test creator can accept a pending request"""
        # First, brand sends a new request
        api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        request_data = {
            "receiverId": creator_profile["id"],
            "receiverType": "creator",
            "message": f"Test accept request {uuid.uuid4().hex[:8]}",
            "proposedBudget": 20000,
            "deliverables": "2 Reels"
        }
        
        create_response = api_client.post(
            f"{BASE_URL}/api/requests/",
            json=request_data,
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        assert create_response.status_code == 201
        request_id = create_response.json()["id"]
        
        # Creator accepts the request
        accept_response = api_client.patch(
            f"{BASE_URL}/api/requests/{request_id}/respond?action=accept",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        assert accept_response.status_code == 200
        data = accept_response.json()
        assert data.get("success") == True
        print(f"✓ Creator accepted request {request_id}")
        
        # Verify status updated
        incoming_response = api_client.get(
            f"{BASE_URL}/api/requests/incoming",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        requests_list = incoming_response.json()
        accepted_req = next((r for r in requests_list if r["id"] == request_id), None)
        
        assert accepted_req is not None
        assert accepted_req["status"] == "accepted"
        assert accepted_req["creditState"] == "consumed"
        print(f"✓ Request status updated to 'accepted', credit consumed")


class TestCreatorDeclinesRequest:
    """Test Feature 4: Creator can decline request - status updates"""
    
    def test_creator_can_decline_request(self, api_client, brand_auth, creator_auth, creator_profile):
        """Test creator can decline a pending request"""
        # First, brand sends a new request
        api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        request_data = {
            "receiverId": creator_profile["id"],
            "receiverType": "creator",
            "message": f"Test decline request {uuid.uuid4().hex[:8]}",
            "proposedBudget": 10000,
            "deliverables": "1 Reel"
        }
        
        create_response = api_client.post(
            f"{BASE_URL}/api/requests/",
            json=request_data,
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        assert create_response.status_code == 201
        request_id = create_response.json()["id"]
        
        # Creator declines the request (using 'reject' action as per API)
        decline_response = api_client.patch(
            f"{BASE_URL}/api/requests/{request_id}/respond?action=reject",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        assert decline_response.status_code == 200
        data = decline_response.json()
        assert data.get("success") == True
        print(f"✓ Creator declined request {request_id}")
        
        # Verify status updated
        incoming_response = api_client.get(
            f"{BASE_URL}/api/requests/incoming",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
        )
        
        requests_list = incoming_response.json()
        declined_req = next((r for r in requests_list if r["id"] == request_id), None)
        
        assert declined_req is not None
        assert declined_req["status"] == "rejected"
        assert declined_req["creditState"] == "refunded"
        print(f"✓ Request status updated to 'rejected', credit refunded")


class TestNewBrandInMarketplace:
    """Test Feature 5: New brand signup with Instagram verification appears in creator marketplace"""
    
    def test_new_brand_appears_in_marketplace_after_instagram_verification(self, api_client, creator_auth):
        """Test new brand with Instagram verification appears in creator marketplace immediately"""
        # Create a new brand
        unique_email = f"test_new_brand_{uuid.uuid4().hex[:8]}@test.com"
        signup_response = api_client.post(f"{BASE_URL}/api/auth/signup", json={
            "email": unique_email,
            "password": "testpass123",
            "role": "business"
        })
        
        assert signup_response.status_code == 200
        new_token = signup_response.json()["access_token"]
        
        # Verify Instagram (simulated) - REQUIRED for marketplace visibility
        verify_response = api_client.post(
            f"{BASE_URL}/api/instagram/verify",
            json={"instagramUsername": f"new_brand_ig_{uuid.uuid4().hex[:6]}"},
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert verify_response.status_code == 200
        print(f"✓ New brand verified Instagram")
        
        # Complete onboarding with profile
        brand_name = f"New Test Brand {uuid.uuid4().hex[:4]}"
        profile_response = api_client.post(
            f"{BASE_URL}/api/business/profile",
            json={
                "brandName": brand_name,
                "industry": "Fashion",
                "bio": "New brand for marketplace visibility testing",
                "location": "Mumbai",
                "budgetRange": "₹15k-₹75k",
                "preferredNiches": ["Fashion", "Beauty"],
                "isOpenToBarter": True
            },
            headers={"Authorization": f"Bearer {new_token}"}
        )
        assert profile_response.status_code == 200
        new_brand_id = profile_response.json()["id"]
        print(f"✓ New brand profile created: {brand_name}")
        
        # Check if new brand appears in marketplace (as creator)
        marketplace_response = api_client.get(
            f"{BASE_URL}/api/marketplace/brands",
            headers={"Authorization": f"Bearer {creator_auth['token']}"}
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
        print(f"✓ New brand appears in creator marketplace immediately after onboarding")


class TestOutgoingRequests:
    """Test brand can see outgoing requests"""
    
    def test_brand_can_see_outgoing_requests(self, api_client, brand_auth):
        """Test brand can fetch outgoing requests"""
        response = api_client.get(
            f"{BASE_URL}/api/requests/outgoing",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Brand can see {len(data)} outgoing requests")
    
    def test_outgoing_requests_have_status(self, api_client, brand_auth):
        """Test outgoing requests show status (pending/accepted/rejected)"""
        response = api_client.get(
            f"{BASE_URL}/api/requests/outgoing",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        assert response.status_code == 200
        requests_list = response.json()
        
        if len(requests_list) == 0:
            pytest.skip("No outgoing requests")
        
        for req in requests_list:
            assert "status" in req
            assert req["status"] in ["pending", "accepted", "rejected", "expired"]
        
        print(f"✓ All outgoing requests have valid status")


class TestCreditsFlow:
    """Test credits are properly managed during request flow"""
    
    def test_credits_locked_when_request_sent(self, api_client, brand_auth, creator_profile):
        """Test credit is locked when request is sent"""
        # Get initial credits
        credits_before = api_client.get(
            f"{BASE_URL}/api/payments/credits",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        ).json()
        
        # Add demo credits
        api_client.post(
            f"{BASE_URL}/api/payments/unlock-pack/demo",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        # Get credits after adding
        credits_after_add = api_client.get(
            f"{BASE_URL}/api/payments/credits",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        ).json()
        
        # Send request
        request_data = {
            "receiverId": creator_profile["id"],
            "receiverType": "creator",
            "message": f"Test credits lock {uuid.uuid4().hex[:8]}",
            "proposedBudget": 5000,
            "deliverables": "1 Story"
        }
        
        create_response = api_client.post(
            f"{BASE_URL}/api/requests/",
            json=request_data,
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        )
        
        assert create_response.status_code == 201
        
        # Get credits after sending request
        credits_after_send = api_client.get(
            f"{BASE_URL}/api/payments/credits",
            headers={"Authorization": f"Bearer {brand_auth['token']}"}
        ).json()
        
        # Verify credit was locked
        assert credits_after_send["lockedCredits"] > credits_after_add.get("lockedCredits", 0)
        print(f"✓ Credit locked when request sent (locked: {credits_after_send['lockedCredits']})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
