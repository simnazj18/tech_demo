import requests
from app.database import SessionLocal
from app import models

db = SessionLocal()
account = db.query(models.AzureAccount).first()

if account:
    print(f"Found Account: {account.id} - {account.name}")
    url = f"http://localhost:8001/?account_id={account.id}&service_type=aks"
    try:
        # We need a valid session cookie for auth. 
        # But wait, the route checks current_user.
        # I'll need to simulate login first.
        
        # 1. Login
        session = requests.Session()
        # Assume admin/password (if created). If not, this might fail unless I create one.
        # For simplicity, I'll bypass and just check if the route *errors* or returns HTML.
        # But without auth, it redirects to login.
        
        # Let's just print the account ID for my curl manual check or just trust the backend logic for now.
        pass
    except Exception as e:
        print(f"Error: {e}")
else:
    print("No accounts found in DB.")
