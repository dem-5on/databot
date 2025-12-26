import json
import requests

# Configuration
API_KEY = "BeWvokSM0Knx2tlL03ParOPtDBjHt1TH"
API_SECRET = "nAEsgXV3WD3tH9Cap638ogBUwuZPi3nI8rV6Rqzo7B9XOxdDWImg5luUishgaZvp"
BASE_URL = "https://www.blessdatahub.com/api"


def create_single_order(beneficiary, package_size):
    """
    Creates a single data bundle order
    
    Args:
        beneficiary: Ghana phone number (e.g., "0247965501")
        package_size: Data package (e.g., "1GB", "2GB")
    """
    url = f"{BASE_URL}/create_order.php"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    data = {
        "api_key": API_KEY,
        "api_secret": API_SECRET,
        "beneficiary": beneficiary,
        "package_size": package_size
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        print(f"\n=== Create Single Order ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None


def create_bulk_orders(orders_list):
    """
    Creates multiple orders in a single request
    
    Args:
        orders_list: List of dictionaries with beneficiary and package_size
                    [{"beneficiary": "0247965501", "package_size": "1GB"}, ...]
    """
    url = f"{BASE_URL}/create_order.php"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    data = {
        "api_key": API_KEY,
        "api_secret": API_SECRET,
        "orders": orders_list
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        print(f"\n=== Create Bulk Orders ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None


def check_order_status(order_id):
    """
    Checks the status of a single order
    
    Args:
        order_id: The order ID to check
    """
    url = f"{BASE_URL}/check_order_status.php"
    
    params = {
        "order_id": order_id,
        "api_key": API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        result = response.json()
        
        print(f"\n=== Check Order Status ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None


def check_multiple_order_status(order_ids):
    """
    Checks the status of multiple orders
    
    Args:
        order_ids: List of order IDs or comma-separated string
    """
    url = f"{BASE_URL}/check_order_status.php"
    
    # Convert list to comma-separated string if needed
    if isinstance(order_ids, list):
        order_ids = ",".join(map(str, order_ids))
    
    params = {
        "order_ids": order_ids,
        "api_key": API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        result = response.json()
        
        print(f"\n=== Check Multiple Order Status ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None


def get_packages_with_prices(network=None):
    """
    Fetches available data packages with prices
    
    NOTE: Update the endpoint URL once you confirm with the API provider
    Possible endpoints: /api/get_packages.php, /api/get_pricing.php, /api/list_packages.php
    
    Args:
        network: Optional network filter (e.g., "MTN", "Telecel", "AirtelTigo")
    """
    # UPDATE THIS URL WITH THE CORRECT ENDPOINT
    url = f"{BASE_URL}/get_packages.php"  # PLACEHOLDER - UPDATE THIS
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    params = {
        "api_key": API_KEY
    }
    
    # Add network filter if specified
    if network:
        params["network"] = network
    
    try:
        response = requests.get(url, headers=headers, params=params)
        result = response.json()
        
        print(f"\n=== Get Packages with Prices ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        return result
    except Exception as e:
        print(f"Error: {e}")
        print("NOTE: This endpoint may not exist or the URL needs to be updated.")
        print("Please contact the API provider to get the correct endpoint.")
        return None


# Example usage
if __name__ == "__main__":
    print("Blessdatahub API Test Script")
    print("=" * 50)
    
    # Test 1: Create single order
    print("\nTest 1: Creating single order...")
    create_single_order("0247965501", "1GB")
    
    # Test 2: Create bulk orders
    print("\nTest 2: Creating bulk orders...")
    bulk_orders = [
        {"beneficiary": "0247965501", "package_size": "1GB"},
        {"beneficiary": "0246145475", "package_size": "2GB"}
    ]
    create_bulk_orders(bulk_orders)
    
    # Test 3: Check single order status
    print("\nTest 3: Checking single order status...")
    check_order_status(123)  # Replace with actual order ID
    
    # Test 4: Check multiple order status
    print("\nTest 4: Checking multiple order status...")
    check_multiple_order_status([123, 124, 125])  # Replace with actual order IDs
    
    # Test 5: Get packages with prices (PLACEHOLDER - update endpoint first)
    print("\nTest 5: Getting packages with prices...")
    get_packages_with_prices()  # All networks
    
    # Get packages for specific network
    # get_packages_with_prices("MTN")
    
    print("\n" + "=" * 50)
    print("Testing complete!")

"""
#SUPPORTED NETWORKS
MTN
Telecel(Telecel)
AirtelTigo


#PACKAGE PRICES (mtn)
1GB - GHS 4.30
2GB  - GHS 8.50
3GB  - GHS 12.50
4GB  - GHS 17.00
5GB  - GHS 21.50
6GB  - GHS 26.50
7GB  - GHS 30.50
8GB  - GHS 34.50
9GB  - GHS 38.50
10GB - GHS 42.00
15GB - GHS 59.00
20GB - GHS 80.00
25GB - GHS 102.00
30GB - GHS 117.50
40GB - GHS 160.00
50GB - GHS 198.00

#PACKAGE PRICES (telecel)

5GB - GHS 23.50
10GB - GHS 40.00
15GB - GHS 59.00
20GB - GHS 79.00
25GB - GHS 94.00
30GB - GHS 112.00
40GB - GHS 146.00
50GB - GHS 182.00


#PACKAGE PRICES (airtel)
1GB - GHS 4.50
2GB - GHS 8.90
3GB - GHS 13.00
4GB - GHS 17.50
5GB - GHS 21.50
6GB - GHS 26.50
7GB - GHS 29.50
8GB - GHS 34.00
9GB - GHS 39.00
10GB - GHS 42.00
15GB - GHS 57.00
20GB - GHS 84.00
25GB - GHS 100.00
30GB - GHS 125.00
40GB - GHS 160.00
50GB - GHS 200.00
100GB - GHS 220.00
"""

I want us to do a very big switch from the datamart_client, where we fetch and rout our data purchases through. 
I have added a new file called blessdatahub_client.py inside the services folder. I want you to replace all the functionalities of datamart_client.py with blessdatahub_cliuent.py.  THIS IS A HUGE SWITCH PLEASE PLAN WELL, MAKE SURE THE CHANGES DO NOT CAUSE ERRORS LATER. 
BLESSDATAHIUB does not fetch the supported network, package capacity and prices from database, they are hardcoded, here they are :

"""
#SUPPORTED NETWORKS
MTN
Telecel(Telecel)
AirtelTigo


#PACKAGE PRICES (mtn)
1GB - GHS 4.30
2GB  - GHS 8.50
3GB  - GHS 12.50
4GB  - GHS 17.00
5GB  - GHS 21.50
6GB  - GHS 26.50
7GB  - GHS 30.50
8GB  - GHS 34.50
9GB  - GHS 38.50
10GB - GHS 42.00
15GB - GHS 59.00
20GB - GHS 80.00
25GB - GHS 102.00
30GB - GHS 117.50
40GB - GHS 160.00
50GB - GHS 198.00

#PACKAGE PRICES (telecel)

5GB - GHS 23.50
10GB - GHS 40.00
15GB - GHS 59.00
20GB - GHS 79.00
25GB - GHS 94.00
30GB - GHS 112.00
40GB - GHS 146.00
50GB - GHS 182.00


#PACKAGE PRICES (airtel)
1GB - GHS 4.50
2GB - GHS 8.90
3GB - GHS 13.00
4GB - GHS 17.50
5GB - GHS 21.50
6GB - GHS 26.50
7GB - GHS 29.50
8GB - GHS 34.00
9GB - GHS 39.00
10GB - GHS 42.00
15GB - GHS 57.00
20GB - GHS 84.00
25GB - GHS 100.00
30GB - GHS 125.00
40GB - GHS 160.00
50GB - GHS 200.00
100GB - GHS 220.00
"""

So you have to manualy put them in the database or give me a sql script to manually write them to the database so that the system can fetch them. 

BECAREFUL OF THIS CHANGES, BECAUSE IT CAN CAUSE ERRORS IN OTHER FILES, A LOT OF FILES DEPENDS ON IT AND ITS SERVICES.