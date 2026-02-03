import requests

BASE_URL = "http://localhost:8001"
SESSION = requests.Session()

def run():
    # 1. Register
    print("1. Registering...")
    r = SESSION.post(f"{BASE_URL}/register", data={"username": "verify_user", "password": "password"})
    print(f"   Status: {r.status_code}") # Should be 200 (login page) or 303

    # 2. Login
    print("2. Logging in...")
    r = SESSION.post(f"{BASE_URL}/token", data={"username": "verify_user", "password": "password"})
    if r.status_code != 200:
        print(f"   Login Failed: {r.text}")
        return
    token = r.json()["access_token"]
    SESSION.cookies.set("access_token", token)
    print("   Login Success.")

    # 3. Add Account
    print("3. Adding Account...")
    r = SESSION.post(f"{BASE_URL}/accounts/add", data={
        "name": "TestEnv",
        "client_id": "ae56138f-d36a-443b-b2f8-1bc3d8b68c59",
        "client_secret": "0Er8Q~E5SCdNeLXS7ziEeW6~ohC2a5kBmDK1Vb7f",
        "tenant_id": "1dcc587a-e945-4997-ba86-712dcdfabb36",
        "kv_url": "https://kv-techdemo-1769683213.vault.azure.net/"
    })
    print(f"   Status: {r.status_code}")

    # 4. Get Account ID
    # We need to parse the dashboard to find the ID, or just guess '1' if it's new DB
    # Let's try ID 1
    ACC_ID = 1

    # 5. Access Dashboard (AKS)
    print(f"4. Accessing Dashboard (Account {ACC_ID}, Type: aks)...")
    r = SESSION.get(f"{BASE_URL}/?account_id={ACC_ID}&service_type=aks")
    
    if r.status_code == 200:
        if "Detected Secrets Usage" in r.text or "Vault Inventory" in r.text:
            print("   SUCCESS! Dashboard content found.")
        else:
            print("   WARNING: Page loaded but content missing.")
            print(r.text[:500])
    else:
        print(f"   FAILED: {r.status_code} - {r.text[:200]}")

if __name__ == "__main__":
    run()
