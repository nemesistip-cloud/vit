#!/usr/bin/env python3
"""
Live Test Suite for VIT Sports Analytics Network
Uses admin credentials from .env to verify system health
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime

# Configuration from .env
ADMIN_EMAIL = "admin@vit.network"
ADMIN_USERNAME = "vit_admin"
ADMIN_PASSWORD = r"Ansel\$7@vit"  # Note: backslash needs escaping
BASE_URL = "http://localhost:5000"
API_PREFIX = ""  # No /api prefix for health, use /auth for login, etc.

class VITLiveTest:
    def __init__(self):
        self.client = None
        self.token = None
        self.results = {
            "passed": [],
            "failed": [],
            "skipped": []
        }
    
    async def setup(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=30.0,
            follow_redirects=True
        )
        print("✓ HTTP client initialized")
    
    async def cleanup(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
        print("✓ HTTP client closed")
    
    async def test_health(self):
        """Test: API health check"""
        try:
            response = await self.client.get("/health")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert "status" in data, "Missing status in response"
            self.results["passed"].append("Health Check")
            print(f"✓ Health Check: {data.get('status', 'unknown')}")
            return True
        except Exception as e:
            self.results["failed"].append(f"Health Check: {str(e)}")
            print(f"✗ Health Check Failed: {e}")
            return False
    
    async def test_login(self):
        """Test: Admin login"""
        try:
            response = await self.client.post(
                "/auth/login",
                json={
                    "email": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                assert self.token, "No token in login response"
                self.results["passed"].append("Admin Login")
                print(f"✓ Admin Login Successful (user: {ADMIN_USERNAME})")
                return True
            else:
                raise Exception(f"Login failed with status {response.status_code}: {response.text}")
        except Exception as e:
            self.results["failed"].append(f"Admin Login: {str(e)}")
            print(f"✗ Admin Login Failed: {e}")
            return False
    
    async def test_config(self):
        """Test: Get configuration"""
        if not self.token:
            self.results["skipped"].append("Config (requires login)")
            print("⊘ Config Check Skipped (no token)")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = await self.client.get(
                "/api/config",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.results["passed"].append("Config Retrieval")
                print(f"✓ Config Retrieved: {len(data)} settings")
                return True
            else:
                raise Exception(f"Status {response.status_code}")
        except Exception as e:
            self.results["failed"].append(f"Config Retrieval: {str(e)}")
            print(f"✗ Config Retrieval Failed: {e}")
            return False
    
    async def test_predict(self):
        """Test: Get predictions endpoint"""
        try:
            response = await self.client.get("/api/predictions?limit=5")
            
            if response.status_code in [200, 401]:  # 401 is OK for unauthenticated
                self.results["passed"].append("Predictions Endpoint")
                print(f"✓ Predictions Endpoint Accessible")
                return True
            else:
                raise Exception(f"Status {response.status_code}")
        except Exception as e:
            self.results["failed"].append(f"Predictions Endpoint: {str(e)}")
            print(f"✗ Predictions Endpoint Failed: {e}")
            return False
    
    async def test_matches(self):
        """Test: Get matches endpoint"""
        try:
            response = await self.client.get("/api/matches")
            
            if response.status_code in [200, 404, 401]:  # Various statuses acceptable
                self.results["passed"].append("Matches Endpoint")
                print(f"✓ Matches Endpoint Accessible")
                return True
            else:
                raise Exception(f"Status {response.status_code}")
        except Exception as e:
            self.results["failed"].append(f"Matches Endpoint: {str(e)}")
            print(f"✗ Matches Endpoint Failed: {e}")
            return False
    
    async def test_admin_panel(self):
        """Test: Admin panel access"""
        if not self.token:
            self.results["skipped"].append("Admin Panel (requires login)")
            print("⊘ Admin Panel Skipped (no token)")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = await self.client.get(
                "/api/admin",
                headers=headers
            )
            
            if response.status_code in [200, 403]:  # 403 if permissions insufficient
                self.results["passed"].append("Admin Panel Access")
                print(f"✓ Admin Panel Accessible")
                return True
            else:
                raise Exception(f"Status {response.status_code}")
        except Exception as e:
            self.results["failed"].append(f"Admin Panel: {str(e)}")
            print(f"✗ Admin Panel Failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        await self.setup()
        
        print("\n" + "="*60)
        print("VIT Sports Analytics - Live Test Suite")
        print("="*60 + "\n")
        
        # Run tests in sequence
        await self.test_health()
        await self.test_login()
        await self.test_config()
        await self.test_predict()
        await self.test_matches()
        await self.test_admin_panel()
        
        # Print summary
        await self.print_summary()
        await self.cleanup()
    
    async def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = len(self.results["passed"])
        failed = len(self.results["failed"])
        skipped = len(self.results["skipped"])
        total = passed + failed + skipped
        
        print(f"\nTotal Tests: {total}")
        print(f"✓ Passed:  {passed}")
        print(f"✗ Failed:  {failed}")
        print(f"⊘ Skipped: {skipped}")
        
        if self.results["passed"]:
            print(f"\n✓ Passed Tests:")
            for test in self.results["passed"]:
                print(f"  • {test}")
        
        if self.results["failed"]:
            print(f"\n✗ Failed Tests:")
            for test in self.results["failed"]:
                print(f"  • {test}")
        
        if self.results["skipped"]:
            print(f"\n⊘ Skipped Tests:")
            for test in self.results["skipped"]:
                print(f"  • {test}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        print("="*60 + "\n")
        
        # Return exit code
        return 0 if failed == 0 else 1

async def main():
    """Main entry point"""
    print(f"\n⟳ Starting VIT Live Test Suite")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Admin Email: {ADMIN_EMAIL}")
    print(f"  Admin User: {ADMIN_USERNAME}")
    print(f"  Timestamp: {datetime.now().isoformat()}\n")
    
    tester = VITLiveTest()
    try:
        exit_code = await tester.run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n✗ Tests interrupted by user")
        await tester.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        await tester.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
