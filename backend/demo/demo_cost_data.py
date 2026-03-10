import random
from datetime import datetime, timedelta

def generate_demo_costs(days: int = 30):
    """Generates `days` worth of realistic demo cloud billing data."""
    services = [
        {"provider": "AWS", "service": "EC2"},
        {"provider": "AWS", "service": "S3"},
        {"provider": "AWS", "service": "RDS"},
        {"provider": "AWS", "service": "Lambda"},
        {"provider": "Azure", "service": "VM"},
        {"provider": "GCP", "service": "Compute Engine"},
    ]
    
    data = []
    end_date = datetime.utcnow()
    
    for i in range(days):
        current_date = end_date - timedelta(days=days - 1 - i)
        date_str = current_date.strftime("%Y-%m-%d")
        
        for s in services:
            # Generate realistic random costs between $5 and $200
            # Adding some noise based on the service to make it look a bit more realistic
            base_cost = random.uniform(20.0, 150.0)
            cost = round(base_cost + random.uniform(-10.0, 50.0), 2)
            
            # Clamp to range [5, 200] just in case
            cost = max(5.0, min(200.0, cost))
            
            data.append({
                "date": date_str,
                "provider": s["provider"],
                "service": s["service"],
                "cost": cost
            })
            
    return data
