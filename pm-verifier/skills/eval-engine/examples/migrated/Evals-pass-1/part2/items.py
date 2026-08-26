"""
PUBLIC items only: question + two candidate answers. NO labels here.
This is the ONLY data the judge ever sees. The answer key lives in a separate
file (answer_key.py) that the judge never reads -- so blindness is structural.
"""

ITEMS = [
    {"id": "Q1",
     "question": "I bought a chef's knife 3 days ago. Can I return it?",
     "answer_A": "No. Kitchen knives are final sale, so they can't be returned.",
     "answer_B": ("Absolutely! Since it's only been 3 days you're comfortably inside our standard "
                  "30-day return window, so you can send it back for a full refund. Just repack it "
                  "safely and use any prepaid label.")},
    {"id": "Q2",
     "question": "Can I return the TV I received 10 days ago, and how?",
     "answer_A": ("Great news! You're well within the window. Just print a prepaid label, drop the "
                  "box with any carrier, and your mail-in refund will process in 5-7 days."),
     "answer_B": "Yes, you're within the 15-day window. TVs must be returned in-store, not by mail."},
    {"id": "Q3",
     "question": "My cotton quilt arrived 20 days ago. Can I still return it?",
     "answer_A": ("Yes. Bedding has a generous 60-day return window and you're only on day 20, so "
                  "you're well within it -- just mail it back for a refund."),
     "answer_B": "No, the 30-day return window has already passed."},
    {"id": "Q4",
     "question": "Can I return a table lamp that was delivered 40 days ago?",
     "answer_A": "No, it's past the 30-day return window.",
     "answer_B": ("You should be fine to return it! Lighting is a popular category and we're usually "
                  "flexible, so go ahead and mail it back and we'll take care of the refund.")},
    {"id": "Q5",
     "question": "I got a wool area rug 5 days ago. Can I return it?",
     "answer_A": ("Yes, you're well within the 30-day window for decor items, so you can mail it back "
                  "for a full refund -- just keep the original packaging if you can."),
     "answer_B": "No, rugs are final sale."},
    {"id": "Q6",
     "question": "Can I return the quilt I bought 70 days ago?",
     "answer_A": "Yes, just mail it back.",
     "answer_B": ("Unfortunately not. Bedding has a 60-day return window and your order is at day 70, "
                  "which is past the cutoff, so it's no longer eligible for return.")},
]


def swapped(item):
    return {"id": item["id"], "question": item["question"],
            "answer_A": item["answer_B"], "answer_B": item["answer_A"]}


SWAPPED = [swapped(i) for i in ITEMS]
