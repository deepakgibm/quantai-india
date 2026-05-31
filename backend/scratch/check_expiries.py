from datetime import datetime, timedelta

def get_upcoming_thursdays(count: int = 5):
    d = datetime.now()
    thursdays = []
    while d.weekday() != 3:
        d += timedelta(days=1)
    
    for _ in range(count):
        thursdays.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=7)
    return thursdays

def get_monthly_expiries(count: int = 3):
    d = datetime.now()
    expiries = []
    
    for _ in range(count):
        next_month = d.replace(day=28) + timedelta(days=4)
        last_day = next_month - timedelta(days=next_month.day)
        
        while last_day.weekday() != 3:
            last_day -= timedelta(days=1)
            
        if last_day < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            d = d.replace(day=28) + timedelta(days=4)
            continue
            
        expiries.append(last_day.strftime("%Y-%m-%d"))
        d = last_day + timedelta(days=7)
        
    return expiries

print("Current time:", datetime.now())
print("Upcoming Thursdays (weekly index expiries):", get_upcoming_thursdays())
print("Monthly expiries (stock expiries):", get_monthly_expiries())
