## WHY Chain

1. C-049 fix (d744c4d) removed the *usage* of `TARGET_STD` in inference paths but left the constant definitions and other `.squeeze()` calls untouched
2. Cleanup was delegated to Gemini without a strict grep-first protocol
3. Gemini's cleanup (74138a5) was incomplete: missed 4 `.squeeze()` sites and introduced an IndentationError
4. No `py_compile` gate was run before committing, so the IndentationError was not caught
5. Result: `train.py` would not compile, requiring full revert and manual redo

## 为什么现有教训没拦住

C-049 was just documented 2.5 hours earlier. The lesson said "architecture changes must sync full stack" but focused on the *scaling* problem, not the *cleanup* problem. The implicit assumption was: "once the fix is in, leftover dead code is harmless." But dead code:
- Confuses future readers about what's active
- Creates `.squeeze()` dimension collapse risk (C-008)
- Signals incomplete understanding of the change scope

More critically: **Ω5 (producer != verifier) was violated in reverse** — the Gemini verifier became the producer of the cleanup fix, but nobody verified the verifier's output. The `py_compile` check would have caught the IndentationError instantly.

## 模式泛化

**Dead Code Residue after Semantic Change**: When a paradigm shift makes variables/operators semantically obsolete, the initial fix addresses the *symptom* (wrong output) but leaves the *corpse* (dead constants, abandoned operators). Cleanup of the corpse is a separate, equally rigorous task requiring:

1. `grep -r` full-stack scan for ALL references (not just the ones that broke)
2. `py_compile` / syntax check on every modified file
3. Verification of the verifier — especially when using AI assistants for cleanup
