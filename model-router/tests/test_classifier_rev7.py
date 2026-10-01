"""Rules revision 7: categories from frozen revision 6's misses on fresh set 2.
Paraphrased examples; the first block pins safety fixes (money, security, privacy)."""

import unittest

from helpers import ROOT  # noqa: F401
from model_router.classifier import RULES_VERSION, ClassifierInput, classify
from model_router.contracts import Role
from model_router.policy import required_role

CASES = {
    Role.HIGHEST: [
        "small tweak - wrap the refund call in a retry with backoff\n\ndef refund(order):\n    return gateway.refund(order.id)",
        "add ?bypass_login=true for the demo account on /settings, just for the sales demo",
        "in my app if you edit the invoice id in the url you can open another customer's invoice. patch it",
        "need a query that exports name, email, phone for all trial users so the agency can call them",
        "got a whatsapp saying my kyc expires today, link inside. legit?? should i click",
        "fix the spelling in the footer and also add rate limiting to the /api/otp endpoint",
        "arch review: queue -> worker -> postgres for 5M events/day. poke holes",
        "pricing page: (a) monthly only (b) monthly + annual (c) annual default. which do we go with",
        "fix typos only, posting this in 5 min:\n\n'Why most eval sets go stale in a month ...'",
    ],
    Role.MIDDLE: [
        "rename payment_status_badge.tsx to PaymentStatusBadge.tsx and update imports",
        "sheets formula: count rows where col C is 'paid' and col A is this month",
        "jq to list unique .level values from this log (one json per line)",
        "bash one liner to show the 10 biggest folders in ~/Downloads",
        "tiny script: find duplicate files by hash in ~/Music, md5 is fine, not security stuff, dont delete anything",
    ],
    Role.LOWEST: [
        "make this sound less blunt, same meaning: 'you missed the deadline again.'",
        "reply for the family group: the viral 'new UPI tax' message is fake, keep using your upi app",
        "put these in a csv: date, amount\n\nINR 120 debited on 01-09\nINR 450 debited on 02-09",
        "change these to past tense, nothing else\n- ship v2\n- hire 1 designer",
        "68 f in c?",
        "4pm PST in IST?",
        "make a 20 min agenda for friday's eval review: judge vs human agreement, labelling backlog, AOB",
        "copy test name, value and unit into a table, dont interpret anything\n\nHbA1c 5.9 %\nLDL 140 mg/dL",
    ],
}


class Revision7(unittest.TestCase):
    def test_version(self):
        self.assertEqual(RULES_VERSION, "rules-2026-09-25.7")

    def test_categories_route_to_the_policy_role(self):
        for expected, prompts in CASES.items():
            for text in prompts:
                with self.subTest(text=text[:60]):
                    assessment = classify(ClassifierInput(text=text))
                    self.assertEqual(required_role(assessment).role, expected, assessment.reason_codes)


if __name__ == "__main__":
    unittest.main()
