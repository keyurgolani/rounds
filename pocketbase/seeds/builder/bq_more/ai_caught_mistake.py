"""BQ: Caught an AI mistake before it shipped — verification rigor."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Caught an AI Mistake Before It Shipped",
    "Tell me about a time you caught an AI mistake before it shipped to production. How did you find it?",
    situation=(
        "I was building a permissions check for a new admin endpoint on our internal tools "
        "platform. The endpoint let users with role 'workspace_admin' invite other users. I had "
        "Claude scaffold the permissions middleware: it generated a check that compared the caller's "
        "role against an allow-list and rejected with 403 if the role wasn't in the list. The code "
        "looked clean, it passed the unit tests it had written for itself, and three reviewers "
        "approved the PR. It would have shipped in the next deploy window — about 90 minutes away."
    ),
    task=(
        "I was the author and owner of the PR. My specific job was to make sure the permissions "
        "check was correct before it merged. 'Reviewers approved it' is necessary but not "
        "sufficient — a permissions bug here would let any authenticated user invite themselves "
        "to workspaces they shouldn't have access to, including potentially our largest customer's."
    ),
    action=(
        "Right before merging I did one last targeted check on my own. I wrote a tiny adversarial "
        "test list — five cases I expected the system to handle correctly: "
        "(1) workspace_admin invites someone, allowed; "
        "(2) regular member tries to invite, rejected; "
        "(3) anonymous user with no auth header, rejected; "
        "(4) user with a SPOOFED 'workspace_admin' role from a different workspace, rejected; "
        "(5) user with no role field at all in the JWT, rejected. "
        "I ran cases 1-3 manually using curl against the staging endpoint — all behaved correctly. "
        "Case 4 caught the bug. Claude had written the check as `if role in ALLOWED_ROLES`, "
        "which checked whether the caller's role string was in the allow-list — but didn't check "
        "whether the caller's workspace_id matched the workspace being modified. A user who was a "
        "workspace_admin in workspace A could call the endpoint with a workspace_id of B and the "
        "check would pass. The unit tests Claude generated had only tested case 1 and case 2, both "
        "with the same workspace_id, so the bug never surfaced. "
        "Once I saw it, the fix was a single additional clause: the caller's role string had to be "
        "in the allow-list AND the caller's workspace_id had to equal the target workspace_id. I "
        "added three new test cases for case 4 — same role, different workspace; same role, same "
        "workspace; missing workspace_id entirely — and re-ran. I pushed the fix and flagged the "
        "original gap in the PR thread so the three reviewers understood why I'd held the merge. "
        "I also wrote a quick post-mortem on what process gap had let this slip past review: the "
        "AI had written tests that proved the happy path but not the *cross-tenant* path, and "
        "reviewers had trusted the green tests. We added a checklist item to our permissions-change "
        "review template: 'cross-tenant case enumerated and tested.' Two weeks later, that "
        "checklist caught a similar bug in a different PR. "
        "What I want to highlight: the catch wasn't a coding skill, it was a *threat modeling* "
        "skill. The question I asked myself wasn't 'is this code correct?' (it parsed fine, it "
        "passed tests) but 'what's the failure that lets someone access data they shouldn't?' "
        "That's the question AI is bad at asking on its own."
    ),
    result=(
        "Bug caught about 80 minutes before the deploy window. Zero customer impact. Three "
        "additional test cases checked into the suite. New review-checklist item adopted "
        "team-wide that caught a similar issue two weeks later in a different PR. "
        "What I'd defend in an interview: this is the failure mode I'm most paranoid about with "
        "AI code — plausible, well-tested, locally-correct, and globally wrong. The AI is good at "
        "passing the tests it imagines; it's not good at imagining the tests that *would have "
        "broken*. The discipline that prevented this from shipping was building a personal "
        "adversarial test list before merging anything security-sensitive, regardless of who wrote "
        "it. I do this for my own code too, but for AI-generated code it's load-bearing. I learned "
        "to treat 'all tests pass' as a much weaker signal when the tests are AI-written, and to "
        "specifically enumerate cross-cutting concerns (tenancy, auth, rate limits, idempotency) "
        "as their own checklist."
    ),
    key_strengths=[
        "Verification rigor",
        "Threat modeling",
        "Skepticism of AI-written tests",
        "Process improvement from incident",
        "Ownership of the merge gate",
    ],
    framework_tips=[
        "Show the SPECIFIC adversarial case that caught the bug — vague 'I reviewed it carefully' doesn't land",
        "Name what the AI got right vs wrong: it wrote correct *code* for a wrong *spec*",
        "Distinguish 'AI wrote bad code' from 'AI wrote code that passes tests but misses a category of bugs'",
        "Connect the catch to a repeatable process change — Meta values systemic fixes, not heroics",
        "Frame the discipline as 'adversarial test list', not 'general carefulness'",
    ],
    tips=[
        "Pick a story where the AI was *plausibly* right — that's the dangerous failure mode Meta is testing for",
        "Have the specific test case ready: what input revealed the bug?",
        "Show that you didn't just catch THIS bug, you built a process change to catch the class",
        "Mention reviewing AI-generated tests with extra skepticism — they prove the path the AI imagined, not the path you care about",
        "Be ready for 'what would have changed if you hadn't caught it?' — quantify the customer impact",
    ],
    common_pitfalls=[
        "Picking a syntactic bug AI made — too easy, doesn't show judgment",
        "Sounding lucky rather than disciplined — 'I happened to notice' is weaker than 'I always do an adversarial test pass'",
        "Skipping the process change — a one-off catch is less valuable than a repeatable mechanism",
        "Blaming the AI — the failure mode is the AI being plausibly wrong; YOUR job was to catch it",
        "Not naming a specific cross-cutting concern (tenancy, auth, idempotency) the bug touched",
    ],
    follow_up_questions=[
        "How do you decide which AI-generated code needs an adversarial test pass and which doesn't?",
        "What did you change about your code-review practice after this?",
        "Have you missed an AI bug that did ship? How did you find out?",
        "How do you train your team to do this kind of review?",
        "What's your test-list for permissions checks specifically?",
    ],
    what_look_for=[
        "Specific, named adversarial test case that revealed the bug",
        "Distinguishing 'syntactically wrong' from 'plausibly wrong' AI failures",
        "Systematic process change, not just an individual catch",
        "Ownership of the merge gate, regardless of who wrote the code",
        "Calibrated skepticism of AI-written tests",
    ],
    tags=[
        "verification",
        "ai-judgment",
        "threat-modeling",
        "safe-and-responsible-ai",
        "code-review",
    ],
    categories=["AI Collaboration", "Ownership & Accountability"],
)
