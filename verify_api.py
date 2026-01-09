
import asyncio
import httpx

async def check_api():
    base_url = "http://localhost:8020/api/v1"
    async with httpx.AsyncClient() as client:
        # Login
        auth_data = {
            "username": "admin@backcast.org",
            "password": "adminadmin"
        }
        print(f"Logging in to {base_url}/auth/login...")
        login_resp = await client.post(f"{base_url}/auth/login", data=auth_data)
        
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.status_code} {login_resp.text}")
            return
            
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get Projects
        print("Fetching projects...")
        proj_resp = await client.get(f"{base_url}/projects", headers=headers)
        
        print(f"Status: {proj_resp.status_code}")
        print("Response Structure:")
        try:
            data = proj_resp.json()
            if isinstance(data, list):
                print("Type: List (Old Format)")
                print(f"Count: {len(data)}")
            elif isinstance(data, dict):
                print("Type: Dict (New Format)")
                print(f"Keys: {data.keys()}")
                if "items" in data:
                    print(f"Items Type: {type(data['items'])}")
                    print(f"Items Count: {len(data['items'])}")
            else:
                print(f"Type: {type(data)}")
                print(data)
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            print(proj_resp.text)

if __name__ == "__main__":
    asyncio.run(check_api())
