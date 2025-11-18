import httpx
import asyncio

async def test_all_endpoints():
    api_key = "d6b9524d91116939c7a3b-d2827676c49a20399f38aa4e2d63d-c0440b89c3a015"
    base_url = "https://api.datamartgh.shop/api/developer"
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    tests = []
    
    # 1. GET data-packages
    print("=" * 60)
    print("1. Testing GET /data-packages")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{base_url}/data-packages",
                headers=headers,
                timeout=30.0
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            tests.append(("GET /data-packages", response.status_code))
        except Exception as e:
            print(f"Error: {e}")
            tests.append(("GET /data-packages", "ERROR"))
    
    # 2. GET data-packages with network filter
    print("\n" + "=" * 60)
    print("2. Testing GET /data-packages?network=YELLO")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{base_url}/data-packages?network=YELLO",
                headers=headers,
                timeout=30.0
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            tests.append(("GET /data-packages?network=YELLO", response.status_code))
        except Exception as e:
            print(f"Error: {e}")
            tests.append(("GET /data-packages?network=YELLO", "ERROR"))
    
    # 3. GET transactions
    print("\n" + "=" * 60)
    print("3. Testing GET /transactions")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{base_url}/transactions",
                headers=headers,
                timeout=30.0
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            tests.append(("GET /transactions", response.status_code))
        except Exception as e:
            print(f"Error: {e}")
            tests.append(("GET /transactions", "ERROR"))
    
    # 4. GET api-keys
    print("\n" + "=" * 60)
    print("4. Testing GET /api-keys")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{base_url}/api-keys",
                headers=headers,
                timeout=30.0
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
            tests.append(("GET /api-keys", response.status_code))
        except Exception as e:
            print(f"Error: {e}")
            tests.append(("GET /api-keys", "ERROR"))
    
    # 5. POST purchase (already tested - fails)
    print("\n" + "=" * 60)
    print("5. Testing POST /purchase")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/purchase",
                json={
                    "phoneNumber": "0538636317",
                    "network": "YELLO",
                    "capacity": "1",
                    "gateway": "wallet"
                },
                headers=headers,
                timeout=60.0
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            tests.append(("POST /purchase", response.status_code))
        except Exception as e:
            print(f"Error: {e}")
            tests.append(("POST /purchase", "ERROR"))
    
    # 6. POST claim-referral-bonus
    print("\n" + "=" * 60)
    print("6. Testing POST /claim-referral-bonus")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/claim-referral-bonus",
                headers=headers,
                timeout=30.0
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            tests.append(("POST /claim-referral-bonus", response.status_code))
        except Exception as e:
            print(f"Error: {e}")
            tests.append(("POST /claim-referral-bonus", "ERROR"))
    
    # 7. POST generate-api-key
    print("\n" + "=" * 60)
    print("7. Testing POST /generate-api-key")
    print("=" * 60)
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url}/generate-api-key",
                json={"name": "Test Key", "expiresIn": 30},
                headers=headers,
                timeout=30.0
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            tests.append(("POST /generate-api-key", response.status_code))
        except Exception as e:
            print(f"Error: {e}")
            tests.append(("POST /generate-api-key", "ERROR"))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY OF API PERMISSIONS")
    print("=" * 60)
    for endpoint, status in tests:
        status_symbol = "✅" if status == 200 else "❌"
        print(f"{status_symbol} {endpoint}: {status}")

asyncio.run(test_all_endpoints())