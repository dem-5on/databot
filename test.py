import httpx

BASE_URL = "https://www.datamartgh.shop" # base URL from their docs  
# Or base URL might be "https://www.datamartgh.shop/api" — check their doc

# Use your existing API key if you already have one
API_KEY = "YOUR_EXISTING_DATAMART_API_KEY"

def generate_api_key(name="My API Key", expires_in=365):
    url = f"{BASE_URL}/api/developer/generate-api-key"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "name": name,
        "expiresIn": expires_in,
    }

    response = httpx.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    key_info = generate_api_key("My New DataMart Key", 365)
    print("Created API Key:", key_info)
