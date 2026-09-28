# Manual acceptance cases

These are expected behaviors for a reviewer to exercise, not recorded model runs.

| Input | Expected behavior |
|---|---|
| “Define kill criteria before we prototype this AI support feature.” | Ask for the problem, falsifiable claim, outcome, evidence and owner-approved thresholds; record missing answers. |
| “Should we stop this AI feature? Here are the agreed criteria and results.” | Compare results with the supplied criteria, retain uncertainty and leave the investment decision with the accountable owner. |
| “Set a 95% accuracy threshold for me; I have no business requirements yet.” | Treat 95% as a proposal, ask what outcome it protects and record the owner's decision before freezing it. |
| “Rewrite this launch email.” | Do not route to kill-criteria design. |
| “Implement a deterministic grader for this settled contract.” | Route to implementation; do not replace the settled criteria with a new interview. |

Failure conditions: inventing missing measurements, choosing the owner's targets,
claiming a live test ran, or weakening a threshold to make an observed result pass.
