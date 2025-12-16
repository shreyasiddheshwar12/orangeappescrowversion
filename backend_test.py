#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class OrangeMarketplaceAPITester:
    def __init__(self, base_url="https://creator-connect-62.preview.emergentagent.com"):
        self.base_url = base_url
        self.creator_token = None
        self.business_token = None
        self.creator_profile_id = None
        self.business_profile_id = None
        self.collaboration_request_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, headers=headers, params=data if data else {})

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text}")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "endpoint": endpoint
                })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "error": str(e),
                "endpoint": endpoint
            })
            return False, {}

    def test_health_check(self):
        """Test basic health endpoints"""
        print("\n=== HEALTH CHECK TESTS ===")
        self.run_test("API Root", "GET", "", 200)
        self.run_test("Health Check", "GET", "health", 200)

    def test_auth_flow(self):
        """Test authentication endpoints"""
        print("\n=== AUTHENTICATION TESTS ===")
        
        # Test creator signup
        creator_data = {
            "email": "testcreator@orange.com",
            "password": "testpass123",
            "role": "creator"
        }
        success, response = self.run_test("Creator Signup", "POST", "auth/signup", 200, creator_data)
        if success and 'access_token' in response:
            self.creator_token = response['access_token']
            print(f"   Creator token obtained: {self.creator_token[:20]}...")

        # Test business signup
        business_data = {
            "email": "testbusiness@orange.com", 
            "password": "testpass123",
            "role": "business"
        }
        success, response = self.run_test("Business Signup", "POST", "auth/signup", 200, business_data)
        if success and 'access_token' in response:
            self.business_token = response['access_token']
            print(f"   Business token obtained: {self.business_token[:20]}...")

        # Test demo creator login
        demo_creator_data = {
            "email": "creator1@orange.com",
            "password": "password123"
        }
        success, response = self.run_test("Demo Creator Login", "POST", "auth/login", 200, demo_creator_data)
        if success and 'access_token' in response:
            print(f"   Demo creator login successful")

        # Test demo business login
        demo_business_data = {
            "email": "business1@orange.com",
            "password": "password123"
        }
        success, response = self.run_test("Demo Business Login", "POST", "auth/login", 200, demo_business_data)
        if success and 'access_token' in response:
            print(f"   Demo business login successful")

        # Test invalid login
        invalid_data = {
            "email": "invalid@orange.com",
            "password": "wrongpass"
        }
        self.run_test("Invalid Login", "POST", "auth/login", 401, invalid_data)

        # Test /me endpoint
        if self.creator_token:
            self.run_test("Get Creator Profile", "GET", "auth/me", 200, token=self.creator_token)

    def test_creator_profile(self):
        """Test creator profile endpoints"""
        print("\n=== CREATOR PROFILE TESTS ===")
        
        if not self.creator_token:
            print("❌ Skipping creator tests - no token available")
            return

        # Create creator profile
        profile_data = {
            "name": "Test Creator",
            "bio": "Test bio for creator",
            "location": "Mumbai, India",
            "instagramHandle": "@testcreator",
            "instagramUrl": "https://instagram.com/testcreator",
            "followersCount": 50000,
            "niches": ["Fashion", "Lifestyle"],
            "isOpenToBarter": True,
            "rates": {
                "reelPrice": 10000,
                "storyPrice": 3000,
                "postPrice": 5000,
                "bundlePrice": 15000
            }
        }
        success, response = self.run_test("Create Creator Profile", "POST", "creator/profile", 200, profile_data, self.creator_token)
        if success and 'id' in response:
            self.creator_profile_id = response['id']
            print(f"   Creator profile ID: {self.creator_profile_id}")

        # Get creator profile
        self.run_test("Get Creator Profile", "GET", "creator/profile", 200, token=self.creator_token)

        # Get creator requests (should be empty initially)
        self.run_test("Get Creator Requests", "GET", "creator/requests", 200, token=self.creator_token)

    def test_business_profile(self):
        """Test business profile endpoints"""
        print("\n=== BUSINESS PROFILE TESTS ===")
        
        if not self.business_token:
            print("❌ Skipping business tests - no token available")
            return

        # Create business profile
        profile_data = {
            "brandName": "Test Brand",
            "category": "Fashion",
            "bio": "Test brand for testing",
            "location": "Delhi, India",
            "websiteUrl": "https://testbrand.com",
            "instagramHandle": "@testbrand",
            "instagramUrl": "https://instagram.com/testbrand"
        }
        success, response = self.run_test("Create Business Profile", "POST", "business/profile", 200, profile_data, self.business_token)
        if success and 'id' in response:
            self.business_profile_id = response['id']
            print(f"   Business profile ID: {self.business_profile_id}")

        # Get business profile
        self.run_test("Get Business Profile", "GET", "business/profile", 200, token=self.business_token)

    def test_marketplace(self):
        """Test marketplace endpoints"""
        print("\n=== MARKETPLACE TESTS ===")
        
        # Get all creators (public endpoint)
        self.run_test("Get All Creators", "GET", "creators", 200)
        
        # Get creators with filters
        self.run_test("Get Creators by Niche", "GET", "creators?niche=Fashion", 200)
        self.run_test("Get Creators by Followers", "GET", "creators?minFollowers=10000", 200)
        self.run_test("Get Creators Open to Barter", "GET", "creators?openToBarter=true", 200)
        
        # Get specific creator by ID (using seeded data)
        self.run_test("Get Creator by ID", "GET", "creators/test-creator-id", 404)  # Should fail for non-existent ID

    def test_collaboration_requests(self):
        """Test collaboration request endpoints"""
        print("\n=== COLLABORATION REQUEST TESTS ===")
        
        if not self.business_token or not self.creator_profile_id:
            print("❌ Skipping collaboration tests - missing tokens or profile IDs")
            return

        # Create collaboration request
        request_data = {
            "creatorId": self.creator_profile_id,
            "title": "Test Campaign",
            "brief": "This is a test collaboration request",
            "offerAmount": 25000,
            "deliverables": "2 Reels, 3 Stories",
            "timeline": "1 week"
        }
        success, response = self.run_test("Create Collaboration Request", "POST", "requests/", 200, request_data, self.business_token)
        if success and 'id' in response:
            self.collaboration_request_id = response['id']
            print(f"   Collaboration request ID: {self.collaboration_request_id}")

        # Get sent requests
        self.run_test("Get Sent Requests", "GET", "requests/sent", 200, token=self.business_token)

        # Get specific request
        if self.collaboration_request_id:
            self.run_test("Get Request by ID", "GET", f"requests/{self.collaboration_request_id}", 200, token=self.business_token)

    def test_request_status_update(self):
        """Test request status updates"""
        print("\n=== REQUEST STATUS TESTS ===")
        
        if not self.creator_token or not self.collaboration_request_id:
            print("❌ Skipping status tests - missing tokens or request ID")
            return

        # Accept request
        self.run_test("Accept Request", "PATCH", f"requests/{self.collaboration_request_id}/status?status=accepted", 200, token=self.creator_token)
        
        # Try to decline already accepted request (should fail)
        self.run_test("Decline Accepted Request", "PATCH", f"requests/{self.collaboration_request_id}/status?status=declined", 400, token=self.creator_token)

    def test_messaging(self):
        """Test messaging endpoints"""
        print("\n=== MESSAGING TESTS ===")
        
        if not self.collaboration_request_id:
            print("❌ Skipping messaging tests - no request ID available")
            return

        # Get messages (should be empty initially)
        self.run_test("Get Messages", "GET", f"messages/{self.collaboration_request_id}", 200, token=self.creator_token)

        # Send message from creator
        message_data = {"text": "Hello! Thanks for the collaboration request!"}
        self.run_test("Send Message (Creator)", "POST", f"messages/{self.collaboration_request_id}", 200, message_data, self.creator_token)

        # Send message from business
        if self.business_token:
            message_data = {"text": "Great! Looking forward to working together."}
            self.run_test("Send Message (Business)", "POST", f"messages/{self.collaboration_request_id}", 200, message_data, self.business_token)

    def test_seed_data(self):
        """Test seed data endpoint"""
        print("\n=== SEED DATA TESTS ===")
        self.run_test("Seed Database", "POST", "seed", 200)

    def run_all_tests(self):
        """Run all test suites"""
        print("🍊 Starting Orange Marketplace API Tests...")
        print(f"Testing against: {self.base_url}")
        
        self.test_health_check()
        self.test_seed_data()  # Seed first to have demo data
        self.test_auth_flow()
        self.test_creator_profile()
        self.test_business_profile()
        self.test_marketplace()
        self.test_collaboration_requests()
        self.test_request_status_update()
        self.test_messaging()
        
        # Print final results
        print(f"\n{'='*50}")
        print(f"📊 TEST RESULTS")
        print(f"{'='*50}")
        print(f"✅ Tests passed: {self.tests_passed}/{self.tests_run}")
        print(f"❌ Tests failed: {len(self.failed_tests)}")
        
        if self.failed_tests:
            print(f"\n🚨 FAILED TESTS:")
            for test in self.failed_tests:
                error_msg = test.get('error', f"Expected {test.get('expected')}, got {test.get('actual')}")
                print(f"   - {test['test']}: {error_msg}")
        
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = OrangeMarketplaceAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())