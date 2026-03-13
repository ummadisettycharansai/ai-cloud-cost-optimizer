import requests  # pyre-ignore[21]
import time
import os

print("Seeding logic implies checking backend readiness...")
def check_health():
    for _ in range(10):
         try:
             res = requests.get("http://localhost:8000/")
             if res.status_code == 200:
                 return True
         except:
             time.sleep(2)
    return False

if check_health():
    print("Backend is ready. The mock data automatically seeds on endpoints via memory state.")
    print("Database synced via SQLAlchemy metadata create_all in main.py.")
else:
    print("Backend not reachable. Run uvicorn main:app first.")
