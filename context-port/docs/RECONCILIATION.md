# Independent reconciliation

Phase 7 compares a source ContextPack with a reconstruction plan without trusting the planner's dispositions or success flags.

The reviewer independently verifies plan integrity, source identity, inventory, exact titles, roles, content blocks, and ordinals. It reports omissions, extras, duplicates, content differences, ordering differences, and integrity failures. `status: clean` requires zero differences.

Destination observation is not available before an approved adapter exists. Phase 7 therefore proves source-versus-plan agreement only; later phases extend the same independent model to observed destination state.
