"""
v2 world: more products across categories. Each CATEGORY has its own
return-policy document, with a different window AND a different return method.
The method is what makes a 'wrong document' mistake visible later: the agent
can get allow/deny right by luck while recommending the wrong method.
"""

# Each category's return-policy "document"
RETURN_POLICIES = {
    "decor":       {"window_days": 30, "method": "mail-back", "final_sale": False},
    "lighting":    {"window_days": 30, "method": "mail-back", "final_sale": False},
    "kitchenware": {"window_days": 0,  "method": "none",      "final_sale": True},   # final sale
    "electronics": {"window_days": 15, "method": "in-store",  "final_sale": False},  # shorter window, different method
    "bedding":     {"window_days": 60, "method": "mail-back", "final_sale": False},  # longer window
}

ITEMS = {
    "rug-01":   {"name": "Wool Area Rug", "category": "decor"},
    "lamp-02":  {"name": "Table Lamp",    "category": "lighting"},
    "knife-03": {"name": "Chef's Knife",  "category": "kitchenware"},
    "tv-04":    {"name": "Smart TV",      "category": "electronics"},
    "quilt-05": {"name": "Cotton Quilt",  "category": "bedding"},
}

ORDERS = {
    "A100": {"item_id": "rug-01",   "delivered_days_ago": 5},
    "A200": {"item_id": "lamp-02",  "delivered_days_ago": 40},
    "A300": {"item_id": "knife-03", "delivered_days_ago": 3},
    "A400": {"item_id": "tv-04",    "delivered_days_ago": 10},
    "A500": {"item_id": "quilt-05", "delivered_days_ago": 20},
}
