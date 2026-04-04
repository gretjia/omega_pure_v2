## WHY Chain

1. Phase 11c was a paradigm shift commit (89b4ebf) — loss function changed, output semantics changed
2. Docker image `phase11-v3` was built immediately from this commit
3. The Train-Serve Skew bug (C-049) was only discovered AFTER the image was built and training started
4. Code fix d744c4d was committed to git 2 hours later
5. "Git fix" did not propagate to the already-running Docker container
6. Dashboard metrics (computed by in-Docker code) showed `pred_std * 216.24` — 216x hallucination
7. The hallucinated dashboard masked the model's brain death for 15 epochs (~7h)

**Root**: Docker build happened at the wrong point in the commit timeline. The mental model was "commit feature → build Docker → submit job" but should be "commit feature → validate all paths → fix bugs → THEN build Docker → submit job."

## 为什么现有教训没拦住

C-049 was discovered and fixed during the same session (2h gap), but the Docker image was already deployed. The C-049 fix addressed the code but not the deployment. There was no protocol requiring Docker rebuild after any post-deploy code fix. The assumption was: "we fixed the code, the next run will be fine" — ignoring that the CURRENT run was still using the broken image.

The `safe_build_and_canary.sh` script enforces build quality but has no mechanism to detect that git HEAD has diverged from the last-built Docker image. It builds whatever is in the working directory at build time.

## 模式泛化

**Docker-Code Timeline Misalignment**: In containerized ML training, there are two independent timelines:
1. Git timeline (code evolves via commits)
2. Docker timeline (image is a frozen snapshot at build time)

When a bug is discovered and fixed in git AFTER Docker build, the fix does NOT exist in the running container. This is especially dangerous when:
- The bug affects monitoring/dashboard code (not just model weights)
- Dashboard values appear plausible (216x inflation looks like "high variance" not "hallucination")
- Long training jobs prevent quick iteration

**Rule**: After ANY code fix that touches files inside the Docker image, the image MUST be rebuilt and the job restarted. "Fixed in git" != "fixed in Docker."
