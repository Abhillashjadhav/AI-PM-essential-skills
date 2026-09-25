"""Rules revision 6: categories from frozen revision 5's misses on the first
fresh set. Paraphrased examples, not copies of set prompts."""

import time
import unittest

from helpers import ROOT  # noqa: F401
from model_router.classifier import RULES_VERSION, ClassifierInput, classify
from model_router.contracts import Role
from model_router.policy import required_role

CASES = {
    Role.HIGHEST: [
        # personal data leaving the system
        "script to export every customer's email and phone number to a sheet for our sales intern",
        # a choice question that mentions a table or a checklist in passing
        "per-customer database or a customer_id column on every table? we're 3 people, maybe 40 clients",
        "signup page: long single form or a 4-step checklist wizard? cant decide",
        # a consequential choice with a count in it
        "the bank says i owe ₹9,200 in late fees. pay it or dispute it? i think they didnt count my june payment",
        # small edits to a credibility document
        "reword my second resume bullet so it shows impact: 'helped with onboarding revamp'",
        "summarise my resume into a 2-line pitch for cold emails to hiring managers",
        # vague directive on consequential work
        "do the needful on the prod deploy, it's urgent",
        # behaviour on a risk-named element is still risky
        "the pay button submits twice sometimes, customers get charged double",
    ],
    Role.MIDDLE: [
        # a tech name as the medium
        "firebase js: get the 10 newest posts ordered by createdAt",
        "postgres query to find duplicate emails in the invites table",
        "supabase edge function not firing on insert into orders_archive, logs are empty",
        # presentation-only work on risk-named elements
        "the 'Billing' tab in my settings page overlaps the header on mobile, tailwind",
        "sign-in button text is not centered on safari, css flex",
        # code that mentions LinkedIn is not LinkedIn writing
        "my extension can't find the easy apply button on linkedin job pages anymore, need a sturdier selector",
        # a word that only sounds risky, and an explicit scope statement
        "my secret santa draw sometimes pairs someone with themselves, fix?\n```py\nrandom.shuffle(names)\n```",
        "using sha1 of the url as a cache key, not for security, just dedup. collisions a concern?",
        "pandas: match my card statement csv against my budget sheet and flag mismatched amounts, read-only",
        # a parenthetical "vs" describes the problem
        "pip install fails with a resolver conflict (numpy 2 vs an old scipy). safe fix?",
    ],
    Role.LOWEST: [
        # extraction verbs and targets
        "pull the order id, amount and delivery date from this email:\n\nOrder #A-771 total ₹1,249 arriving Tue 14 Oct",
        "list just the table names from this:\nCREATE TABLE users (id int);\nCREATE TABLE orders (id int);",
        "copy my email and phone from the resume text below, nothing else\n\nAsha Rao · asha@example.com · +91 90000 00000",
        "just links: official docs for postgres row level security and next.js middleware",
        "4 quiet cafes in indiranagar with good wifi, just names",
        # constraints are not requests to change
        "from my cv below list the job titles only, dont change or improve anything\n\nPM, Kestrel Payments\nAPM, Orbit",
        "swap 'users' for 'members' everywhere in this paragraph: Users can invite users to a workspace.",
        "fix only the typos: 'the standup is movd to 11, pls confrim'",
        # arithmetic over pasted statements
        "total how much i spent from these\n\nRs 120 debited via UPI to CHAI POINT\nRs 640 debited via UPI to BIGBASKET",
        # a design document as material, a to-do list with a coding item in it
        "summarise this prd into 4 bullets for my own notes: [pasted prd for the referral feature]",
        "turn this brain dump into a checklist for tomorrow: dentist 10am, fix the flaky test in my bot, buy milk",
        # scheduling with a recruiter is logistics
        "reply to the recruiter: thursday 11am works for the screening call, please send the meet link",
    ],
}


class Revision6(unittest.TestCase):
    def test_version_is_at_least_revision_6(self):
        self.assertGreaterEqual(int(RULES_VERSION.rsplit(".", 1)[1]), 6)

    def test_categories_route_to_the_policy_role(self):
        for expected, prompts in CASES.items():
            for text in prompts:
                with self.subTest(text=text[:60]):
                    assessment = classify(ClassifierInput(text=text))
                    self.assertEqual(required_role(assessment).role, expected, assessment.reason_codes)

    def test_persuasive_recruiter_message_stays_highest(self):
        text = "reply to the recruiter: thank them and say why i'm excited about the role, 3pm works for the call"
        self.assertEqual(required_role(classify(ClassifierInput(text=text))).role, Role.HIGHEST)

    def test_new_patterns_stay_linear(self):
        for text in ("pull " * 20000, "get a from " * 8000, "swap a for " * 8000, "(a vs b) " * 8000, "dont change " * 8000,
                     "reply to the recruiter: " + "3pm works " * 6000, "x: " * 30000):
            started = time.monotonic()
            classify(ClassifierInput(text=text))
            self.assertLess(time.monotonic() - started, 1.0, repr(text[:12]))


if __name__ == "__main__":
    unittest.main()
