import json
import uuid
import httpx
import asyncio
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# CONFIGURATION - Update these with your actual values
API_TOKEN = "tok_047a6dbfdbb7f0086083e46ed01d8ea708bad64ae19f104967528536ef8b46b8"  
BASE_URL = "https://datapacks.shop/api.php"
TEST_PHONE = "0538636317"  

class DataPacksAPITester:
    def __init__(self, token: str, base_url: str):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        self.test_results: List[Tuple[str, str, any]] = []
    
    def print_separator(self, title: str = ""):
        print("\n" + "=" * 70)
        if title:
            print(f"{title}")
            print("=" * 70)
    
    def log_test(self, endpoint: str, status: any, response_data: any = None):
        """Log test result"""
        self.test_results.append((endpoint, status, response_data))
        status_symbol = "✅" if str(status).startswith("2") else "❌"
        print(f"{status_symbol} Status: {status}")
        if response_data:
            try:
                if isinstance(response_data, str):
                    print(f"Response: {response_data[:500]}")
                else:
                    print(f"Response: {json.dumps(response_data, indent=2)[:500]}")
            except:
                print(f"Response: {response_data}")
    
    async def test_get_bundles(self, network: Optional[str] = None):
        """Test getting available bundles"""
        endpoint = "?action=bundles"
        if network:
            endpoint += f"&network={network}"
            title = f"1. Testing GET /api.php?action=bundles&network={network}"
        else:
            title = "1. Testing GET /api.php?action=bundles"
        
        self.print_separator(title)
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    timeout=30.0
                )
                try:
                    data = response.json()
                except:
                    data = response.text
                self.log_test(f"GET {endpoint}", response.status_code, data)
                return data
            except Exception as e:
                print(f"❌ Error: {e}")
                self.log_test(f"GET {endpoint}", "ERROR", str(e))
                return None
    
    async def test_get_balance(self):
        """Test getting wallet balance"""
        self.print_separator("2. Testing GET /api.php?action=balance")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}?action=balance",
                    headers=self.headers,
                    timeout=30.0
                )
                data = response.json() if response.status_code == 200 else response.text
                self.log_test("GET ?action=balance", response.status_code, data)
                return data
            except Exception as e:
                print(f"❌ Error: {e}")
                self.log_test("GET ?action=balance", "ERROR", str(e))
                return None
    
    async def test_single_order(self, network: str, capacity: float, 
                                recipient: str, client_ref: str, 
                                dry_run: bool = True):
        """Test creating a single order"""
        title = f"3. Testing POST /api.php?action=order ({'DRY RUN' if dry_run else 'LIVE'})"
        self.print_separator(title)
        
        # Generate unique idempotency key
        idempotency_key = str(uuid.uuid4())
        
        payload = {
            "network": network,
            "capacity": capacity,
            "recipient": recipient,
            "client_ref": client_ref
        }
        
        headers = self.headers.copy()
        headers["Idempotency-Key"] = idempotency_key
        
        print(f"📝 Request Body: {json.dumps(payload, indent=2)}")
        print(f"🔑 Idempotency-Key: {idempotency_key}")
        
        if dry_run:
            print("⚠️  DRY RUN MODE - Skipping actual API call")
            print("   Remove dry_run=True to execute real order")
            self.log_test("POST ?action=order", "SKIPPED", payload)
            return None
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}?action=order",
                    json=payload,
                    headers=headers,
                    timeout=60.0
                )
                data = response.json() if response.status_code == 200 else response.text
                self.log_test("POST ?action=order", response.status_code, data)
                return data
            except Exception as e:
                print(f"❌ Error: {e}")
                self.log_test("POST ?action=order", "ERROR", str(e))
                return None
    
    async def test_bulk_order(self, orders: List[Dict], dry_run: bool = True):
        """Test creating bulk orders"""
        title = f"4. Testing POST /api.php?action=bulk_order ({'DRY RUN' if dry_run else 'LIVE'})"
        self.print_separator(title)
        
        payload = {"orders": orders}
        
        print(f"📝 Request Body: {json.dumps(payload, indent=2)}")
        
        if dry_run:
            print("⚠️  DRY RUN MODE - Skipping actual API call")
            print("   Remove dry_run=True to execute real bulk order")
            self.log_test("POST ?action=bulk_order", "SKIPPED", payload)
            return None
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}?action=bulk_order",
                    json=payload,
                    headers=self.headers,
                    timeout=60.0
                )
                data = response.json() if response.status_code == 200 else response.text
                self.log_test("POST ?action=bulk_order", response.status_code, data)
                return data
            except Exception as e:
                print(f"❌ Error: {e}")
                self.log_test("POST ?action=bulk_order", "ERROR", str(e))
                return None
    
    async def test_get_status(self, ref: str):
        """Test checking order status"""
        self.print_separator(f"5. Testing GET /api.php?action=status&ref={ref}")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}?action=status&ref={ref}",
                    headers=self.headers,
                    timeout=30.0
                )
                data = response.json() if response.status_code == 200 else response.text
                self.log_test(f"GET ?action=status&ref={ref}", response.status_code, data)
                return data
            except Exception as e:
                print(f"❌ Error: {e}")
                self.log_test(f"GET ?action=status&ref={ref}", "ERROR", str(e))
                return None
    
    async def test_invalid_token(self):
        """Test with invalid token to verify authentication"""
        self.print_separator("6. Testing Authentication - Invalid Token")
        invalid_headers = {
            "Authorization": "Bearer INVALID_TOKEN_12345",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}?action=bundles",
                    headers=invalid_headers,
                    timeout=30.0
                )
                data = response.json() if response.status_code != 200 else response.text
                self.log_test("GET ?action=bundles (invalid token)", response.status_code, data)
            except Exception as e:
                print(f"❌ Error: {e}")
                self.log_test("GET ?action=bundles (invalid token)", "ERROR", str(e))
    
    async def test_invalid_phone_format(self):
        """Test with invalid phone number format"""
        self.print_separator("7. Testing Validation - Invalid Phone Format")
        
        payload = {
            "network": "MTN",
            "capacity": 1,
            "recipient": "+233538636317",
            "client_ref": f"TEST-INVALID-{datetime.now().timestamp()}"
        }
        
        print(f"📝 Request Body: {json.dumps(payload, indent=2)}")
        print("⚠️  Expected to fail - testing validation")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}?action=order",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )
                data = response.json() if response.status_code != 200 else response.text
                self.log_test("POST ?action=order (invalid phone)", response.status_code, data)
            except Exception as e:
                print(f"❌ Error: {e}")
                self.log_test("POST ?action=order (invalid phone)", "ERROR", str(e))
    
    async def test_duplicate_idempotency(self, network: str = "MTN", 
                                        capacity: float = 1, 
                                        recipient: str = "0548541380"):
        """Test idempotency by sending same request twice"""
        self.print_separator("8. Testing Idempotency - Duplicate Key")
        
        # Use same idempotency key for both requests
        idempotency_key = str(uuid.uuid4())
        client_ref = f"TEST-IDEM-{datetime.now().timestamp()}"
        
        payload = {
            "network": network,
            "capacity": capacity,
            "recipient": recipient,
            "client_ref": client_ref
        }
        
        headers = self.headers.copy()
        headers["Idempotency-Key"] = idempotency_key
        
        print(f"📝 Request Body: {json.dumps(payload, indent=2)}")
        print(f"🔑 Idempotency-Key: {idempotency_key}")
        print("\n⚠️  This test is SKIPPED by default to avoid actual charges")
        print("   Set execute_idempotency_test=True in run_all_tests() to run")
        
        self.log_test("POST ?action=order (idempotency test)", "SKIPPED", payload)
    
    def print_summary(self):
        """Print test summary"""
        self.print_separator("TEST SUMMARY")
        
        success_count = sum(1 for _, status, _ in self.test_results 
                          if str(status).startswith("2"))
        skipped_count = sum(1 for _, status, _ in self.test_results 
                           if status == "SKIPPED")
        error_count = sum(1 for _, status, _ in self.test_results 
                         if status == "ERROR")
        client_error_count = sum(1 for _, status, _ in self.test_results 
                                if str(status).startswith("4"))
        server_error_count = sum(1 for _, status, _ in self.test_results 
                                if str(status).startswith("5"))
        
        print(f"\nTotal Tests: {len(self.test_results)}")
        print(f"✅ Successful (2xx): {success_count}")
        print(f"⏭️  Skipped (dry run): {skipped_count}")
        print(f"❌ Client Errors (4xx): {client_error_count}")
        print(f"❌ Server Errors (5xx): {server_error_count}")
        print(f"❌ Connection Errors: {error_count}")
        
        print("\n" + "-" * 70)
        print("DETAILED RESULTS:")
        print("-" * 70)
        
        for endpoint, status, _ in self.test_results:
            if status == "SKIPPED":
                status_symbol = "⏭️"
            elif str(status).startswith("2"):
                status_symbol = "✅"
            else:
                status_symbol = "❌"
            print(f"{status_symbol} {endpoint}: {status}")
        
        print("=" * 70)

async def run_all_tests(execute_live_orders: bool = False, 
                       execute_idempotency_test: bool = False,
                       test_order_ref: Optional[str] = None):
    """
    Run all API tests
    
    Args:
        execute_live_orders: Set to True to make actual order API calls (will charge your account)
        execute_idempotency_test: Set to True to test idempotency (will make actual orders)
        test_order_ref: Existing order reference to test status endpoint (e.g., "API-1000452")
    """
    print("\n" + "🚀" * 35)
    print("DataPacks.shop API Testing Suite")
    print("🚀" * 35)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    if not execute_live_orders:
        print("\n⚠️  SAFE MODE: Order tests will run in DRY RUN mode")
        print("   Set execute_live_orders=True to make real API calls")
    else:
        print("\n🔴 LIVE MODE: Orders will be executed and charged!")
        await asyncio.sleep(3)  # Give time to cancel
    
    tester = DataPacksAPITester(API_TOKEN, BASE_URL)
    
    # Test 1: Get all bundles
    bundles_data = await tester.test_get_bundles()
    
    # Test 2: Get bundles filtered by network
    if bundles_data and isinstance(bundles_data, dict) and bundles_data.get("success"):
        networks = list(set([b["network_key"] for b in bundles_data.get("bundles", [])]))
        if networks:
            await tester.test_get_bundles(network=networks[0])
    
    # Test 3: Get balance
    await tester.test_get_balance()
    
    # Test 4: Single order (dry run by default)
    await tester.test_single_order(
        network="MTN",
        capacity=1,
        recipient=TEST_PHONE,
        client_ref=f"TEST-{datetime.now().timestamp()}",
        dry_run=not execute_live_orders
    )
    
    # Test 5: Bulk order (dry run by default)
    bulk_orders = [
        {
            "network": "MTN",
            "capacity": 1,
            "recipient": "0548541380",
            "client_ref": f"BULK-1-{datetime.now().timestamp()}"
        },
        {
            "network": "MTN",
            "capacity": 2,
            "recipient": "0556186221",
            "client_ref": f"BULK-2-{datetime.now().timestamp()}"
        }
    ]
    await tester.test_bulk_order(bulk_orders, dry_run=not execute_live_orders)
    
    # Test 6: Check order status (if reference provided)
    if test_order_ref:
        await tester.test_get_status(test_order_ref)
    else:
        print("\n" + "=" * 70)
        print("5. SKIPPED: GET /api.php?action=status")
        print("=" * 70)
        print("⏭️  No order reference provided")
        print("   Set test_order_ref='API-XXXXXXX' to test status endpoint")
        tester.test_results.append(("GET ?action=status", "SKIPPED", None))
    
    # Test 7: Invalid authentication
    await tester.test_invalid_token()
    
    # Test 8: Invalid phone format
    await tester.test_invalid_phone_format()
    
    # Test 9: Idempotency test
    if execute_idempotency_test:
        await tester.test_duplicate_idempotency()
    else:
        await tester.test_duplicate_idempotency()  # Will show as skipped
    
    # Print summary
    tester.print_summary()
    
    print("\n" + "💡" * 35)
    print("NEXT STEPS:")
    print("=" * 70)
    print("1. Review the test results above")
    print("2. If all auth tests pass, you can test live orders:")
    print("   - Set execute_live_orders=True")
    print("3. Test status endpoint with a real order reference:")
    print("   - Set test_order_ref='API-1000XXX'")
    print("4. Check your webhook configuration if using webhooks")
    print("=" * 70)

if __name__ == "__main__":
    print("\n⚠️  CONFIGURATION CHECKLIST:")
    print("=" * 70)
    print(f"✓ API_TOKEN: {'SET' if API_TOKEN != 'YOUR_API_TOKEN_HERE' else '❌ NOT SET'}")
    print(f"✓ BASE_URL: {BASE_URL}")
    print(f"✓ TEST_PHONE: {TEST_PHONE}")
    print("=" * 70)
    
    if API_TOKEN == "YOUR_API_TOKEN_HERE":
        print("\n❌ ERROR: Please set your API_TOKEN before running!")
        print("   Get your token from: https://datapacks.shop/user/api_tokens.php")
        exit(1)
    
    print("\n")
    
    # Run tests in safe mode (dry run) by default
    asyncio.run(run_all_tests(
        execute_live_orders=True,  # Set to True to make real orders
        execute_idempotency_test=True,  # Set to True to test idempotency
        test_order_ref=None  # Set to "API-1000XXX" to test status endpoint
    ))