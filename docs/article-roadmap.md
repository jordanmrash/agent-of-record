# Article Roadmap: 20 Next Topics

These subjects extend the published arc from tax-software implementation into a practical operating model for AI in public accounting.

1. **Public Accounting Does Not Have a Prompting Problem; It Has a Control-System Problem** — Explain why repeatable professional use depends on evidence, deterministic boundaries, approval, memory, testing, and change management rather than increasingly elaborate prompts.
2. **Human in the Loop Is Not a Control Unless the Human Sees the Action** — Distinguish general responsibility statements from approval at the exact point where an agent can send, change, delete, or execute.
3. **The Audit Trail Starts Before the AI Produces an Answer** — Show how inputs, provenance, tool calls, rule versions, approvals, and failure records matter as much as the final output.
4. **Production Should Be a Flag, Not a Guess from the System Name** — Use the Power Automate bridge design to explain why environment classification must be explicit data rather than a naming convention.
5. **The Control That Could Not See the Agent** — Describe how file linters appeared to enforce rules but remained blind to direct session behavior, and why honest controls declare their blind spots.
6. **Why AI Tests Need a Negative Control** — Explain how three successful runs prove little unless a comparable agent without the intervention fails.
7. **Logging an AI Failure Is Not the Same as Fixing It** — Distinguish incident capture, reusable lessons, standing rules, deterministic checks, and verified behavioral change.
8. **Your AI Memory Can Learn the Wrong Lesson** — Explore coincidence, stale facts, contradictory memories, review cadence, supersession, and why persistence does not imply truth.
9. **Delivered, Promoted, Enforced: Three Words AI Governance Should Not Confuse** — Define the difference between placing a rule in a skill, loading it every session, and mechanically preventing the behavior.
10. **When an Instruction Should Become Code** — Provide a decision framework for moving recurring invariants out of model prose and into validators, linters, schemas, and refusal gates.
11. **The Self-Improving Agent That Rejected Its Own Improvement** — Tell the story of an apparently useful rule that was measured inert because the tool schema already made the mistake impossible.
12. **Stateless Infrastructure Is a Governance Feature, Not Just a Reliability Feature** — Connect independent requests, bounded state, restartability, and observable failure to safer professional automation.
13. **How to Give a Cloud Agent Local Reach Without Giving It a Shell** — Explain the restricted filesystem and filename-only batch-execution pattern, including its residual risks.
14. **Why My Command Bridge Accepts a Filename and Nothing Else** — Walk through how reducing the interface makes an approval meaningful and removes whole classes of hidden execution parameters.
15. **One Sign-In, Three APIs: What Power Automate Taught Me About Enterprise Agent Design** — Use the Dataverse, Flow, and PowerApps split to show why enterprise capabilities rarely fit behind one neat endpoint.
16. **A Public Repository Can Leak a Client Without Containing a Credential** — Explain disclosure through filenames, prose, history, examples, and menus, and why clean-room publication is broader than secret scanning.
17. **Build the Foundation Before the Accounting Skills** — Make the case for common memory, evidence, execution, testing, and governance before proliferating disconnected tax and accounting automations.
18. **A Common Contract for Every Accounting Agent Skill** — Propose the required inputs, evidence, deterministic calculations, hard stops, review points, audit record, tests, owner, and release status.
19. **Where Determinism Ends and Professional Judgment Begins** — Show how accounting workflows should divide arithmetic and reconciliation into code while reserving ambiguity and accountable conclusions for professionals.
20. **From a Correct Workpaper to a Governed Agent** — Trace the path from an answer key through decomposition, validation, failure protocols, behavioral tests, release, ownership, and maintenance.

## Suggested publishing sequence

Publish in four five-article series:

1. **The operating model:** topics 1, 2, 3, 17, 18.
2. **Controls that can fail:** topics 4, 5, 6, 9, 10.
3. **Learning systems:** topics 7, 8, 11, 12, 16.
4. **Applied architecture:** topics 13, 14, 15, 19, 20.
