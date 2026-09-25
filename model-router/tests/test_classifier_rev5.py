"""Rules revision 5: general failure categories found by analysing every miss on
the examined prompt sets. Examples are paraphrases, not copies of set prompts,
so these tests pin the category, not a memorised sentence."""

import time
import unittest

from helpers import ROOT  # noqa: F401
from model_router.classifier import RULES_VERSION, ClassifierInput, classify
from model_router.contracts import Role
from model_router.policy import required_role

CASES = {
    Role.HIGHEST: [
        # risk words behind a hyphen
        "add auto-refunds to the checkout flow when an order is cancelled",
        # sessions, tokens and account access
        "users keep getting logged out after five minutes in my app, fix it",
        "the jwt refresh fails silently in my middleware",
        "script to add my ci user to sudoers so deploys can restart nginx",
        # incidents
        "got a suspicious login alert from my bank app, what now",
        "my instagram got hacked and the email was changed, help",
        # design and modelling questions
        "how should we model refunds and partial payments in the db?",
        # casually phrased consequential assessments
        "safe to upgrade postgres on my live app tonight?",
        # destructive work on real data
        "delete all inactive users from the database",
        "clean up old files in my firebase bucket, it's full",
        # small edits to a credibility document
        "fix typos in my cover letter",
        "just tidy the formatting of my linkedin post",
        # a judgement question about a consequential reply
        "got a legal notice from my landlord's lawyer, what should i reply?",
    ],
    Role.MIDDLE: [
        # the medium names the task as code
        "sql: top 5 customers by revenue last quarter",
        "scrape the table on this page with python + bs4",
        # debugging symptoms and UI state
        "when i click submit nothing happens",
        "TypeError: Cannot read properties of undefined (reading 'map') in renderList(items)",
        "add a loading state to the dashboard table",
        # turning something into software
        "turn this notebook into a small cli tool",
        # scope statements exclude a concern
        "architecture for the notes api is agreed (single-user, local only, no auth). build the POST endpoint with tests",
        # pasted input data for new code, and comments in code being changed
        "write a regex that extracts the amounts from these lines:\n\nrefund 200 to user 7\npayment 300 failed",
        "add docstrings to this, nothing else:\n\n# TODO: never log the password here\ndef add(a, b):\n    return a + b",
    ],
    Role.LOWEST: [
        # arithmetic and format conversion
        "what's 18% of 2,400, just the math",
        "convert 3,500 EUR to INR at 90.1",
        "csv to json pls:\n\nname,age\nasha,31",
        # material named in the instruction, pasted after a blank line
        "how many bullets are under each job in my resume? just count\n\nAcme\n- ran payments migration\n- led checkout",
        "summarize my notes from the call:\n\n- someone ran DROP TABLE on staging once\n- restore drill went fine",
        # message logistics, not a judgement call
        "reply to rohan that friday works, should i cc priya?",
        # summaries of sensitive-sounding material stay summaries
        "summarize this article about the okta breach in 3 bullets",
        # low-stakes personal writing and planning
        "write a haiku about the monsoon",
        "plan a 3 day trip to goa on a budget",
        "sew buttons back on my shirt, list the steps",
    ],
}


class Revision5(unittest.TestCase):
    def test_version_is_at_least_revision_5(self):
        self.assertGreaterEqual(int(RULES_VERSION.rsplit(".", 1)[1]), 5)

    def test_categories_route_to_the_policy_role(self):
        for expected, prompts in CASES.items():
            for text in prompts:
                with self.subTest(text=text[:60]):
                    assessment = classify(ClassifierInput(text=text))
                    self.assertEqual(required_role(assessment).role, expected, assessment.reason_codes)

    def test_no_auth_scope_statement_does_not_hide_other_risk(self):
        text = "build the checkout endpoint (no auth for now) that charges the card"
        self.assertEqual(required_role(classify(ClassifierInput(text=text))).role, Role.HIGHEST)

    def test_new_patterns_stay_linear(self):
        for text in ("a." * 30000, "1," * 30000, "a.a(" * 15000, '"' * 60000, "'x' " * 20000, "clean up the " * 5000):
            started = time.monotonic()
            classify(ClassifierInput(text=text))
            self.assertLess(time.monotonic() - started, 1.0, repr(text[:10]))


if __name__ == "__main__":
    unittest.main()
