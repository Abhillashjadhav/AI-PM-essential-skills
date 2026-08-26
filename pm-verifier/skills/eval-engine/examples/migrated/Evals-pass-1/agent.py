"""
v2 agent. Clean by default; can be told to pull the WRONG document.
Now records a full TRACE: every step, with the product, the date, and the
document it pulled -- so the eval can point at exactly where a run diverged.
"""

from store import ITEMS, ORDERS, RETURN_POLICIES

WRONG_DOC_CATEGORY = "decor"  # the doc the agent mistakenly grabs when faulty


def run_agent(order_id, wrong_doc=False):
    trace = []

    order = ORDERS[order_id]
    days = order["delivered_days_ago"]
    trace.append({"step": "get_order",
                  "detail": f"order {order_id} -> item {order['item_id']}, delivered {days} days ago"})

    item = ITEMS[order["item_id"]]
    true_category = item["category"]
    trace.append({"step": "get_item",
                  "detail": f"{order['item_id']} -> {item['name']}, category '{true_category}'"})

    doc_category = WRONG_DOC_CATEGORY if wrong_doc else true_category
    policy = RETURN_POLICIES[doc_category]
    trace.append({"step": "get_policy_doc",
                  "detail": f"pulled '{doc_category}' doc (window {policy['window_days']}d, "
                            f"method {policy['method']}, final_sale {policy['final_sale']})"})

    if policy["final_sale"]:
        decision, method = "DENY", "none"
    elif days <= policy["window_days"]:
        decision, method = "ALLOW", policy["method"]
    else:
        decision, method = "DENY", "none"
    trace.append({"step": "decide", "detail": f"{decision}, method={method}"})

    return {
        "answer": {"decision": decision, "method": method},
        "facts": {"product": item["name"], "category": true_category,
                  "days": days, "doc_category_pulled": doc_category},
        "trace": trace,
    }
