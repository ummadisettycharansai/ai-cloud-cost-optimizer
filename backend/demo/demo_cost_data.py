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
    
    # Generate 30 days of data
    for i in range(days):
        current_date = end_date - timedelta(days=days - 1 - i)
        date_str = current_date.strftime("%Y-%m-%d")
        
        for s in services:
            # Generate realistic random costs between $10 and $200
            cost = round(random.uniform(10.0, 200.0), 2)
            
            data.append({
                "date": date_str,
                "provider": s["provider"],
                "service": s["service"],
                "cost": cost
            })
            
    return data
