# Autoresearch Phase 11d Plan & Specification

## 1. The Core Problem: Variance Collapse (INS-054)
In Phase 11c/11d, our model learned a pathological shortcut. To minimize the $L_1$ sparsity penalty (`lambda_s * s_t`) and survive the harsh gradient clipping of the Huber loss (`delta`), it found the mathematically safest route:
**Turn off all features (`z_core` -> 0) and output a near-constant prediction.**

**Symptoms:**
- The standard deviation of predictions (`Std_yhat`) collapsed to **13-23 Basis Points (BP)**.
- We physically require a natural dispersion of **> 30 BP** to differentiate strong directional signals from market noise.
- The model is essentially "brain dead," outputting the mean of the training set rather than learning microstructural dynamics.

## 2. The Autoresearch Objective
We will unleash an AI agent on the `linux1-lx` node (now wielding **108GB of VRAM**) to autonomously rewrite the mathematical topology of the loss function. 

**The Goal:** Evolve a new loss function inside `train.py` that maximizes the following Composite North Star Metric (Reward):
```python
Reward = Val_PfRet - 2.0 * max(0.0, 30.0 - Val_Std_yhat)
```
*Translation: "Maximize Portfolio Return, but if your prediction variance drops below 30 BP, you will be severely punished."*

## 3. The Sandbox Environment (5-Minute Feedback Loop)
To enable rapid evolution, we have constructed `tools/autoresearch_sandbox.py`.
- **Speed:** It runs a micro-epoch (30 train batches, 20 val batches) in under 5 minutes.
- **Hardware:** It uses the `linux1-lx` APU (`HSA_OVERRIDE_GFX_VERSION=11.0.0`).
- **Data:** It loads real shards from `/omega_pool` if available, or synthetic data if not, ensuring the mathematical graph is fully differentiable.
- **Output:** It prints a single `FINAL_REWARD` scalar. The agent uses this scalar to decide whether to keep or discard its code changes.

## 4. The Agent's Constraints
The AI agent operates under strict rules defined in `autoresearch_program.md`:
1. **Surgical Precision:** It is ONLY allowed to modify the `compute_spear_loss` function inside `train.py`.
2. **Interface Contract:** It MUST NOT change the function signature (`pred, target, z_core, lambda_s, epoch...`).
3. **Output Contract:** It MUST return `(total_loss, pf_ret, s_t)`, where `total_loss` is a differentiable scalar.

## 5. Evolutionary Search Space (Hypotheses to Explore)
The agent will be prompted to explore the following mathematical spaces:

1. **Leaky Target Blinding:** Currently, negative targets are clamped to exactly zero. The agent might change this to a Leaky ReLU equivalent for the target, allowing a small gradient on negative returns to prevent the network from dying in a flat region.
2. **Log-Cosh Loss:** The Huber loss has a sharp transition at `delta`. Log-Cosh is perfectly smooth everywhere, potentially offering a better optimization landscape for the optimizer.
3. **Dynamic / Variance-Aware Feature Tax:** Instead of a static `lambda_s * s_t`, the agent could implement a tax that vanishes if the prediction variance is too low: `lambda_eff = lambda_s * max(0, pred.std() - 30)`.
4. **Direct Variance Bonus:** The agent could add a term that directly rewards dispersion: `total_loss = loss_spear + lambda_s * s_t - alpha * pred.std()`.
5. **Asymmetric Pearson:** Bringing back a bounded version of Pearson correlation that focuses only on the right tail (positive returns).

## 6. Execution Flow
1. **Init:** The agent reads `autoresearch_program.md`.
2. **Mutate:** The agent edits `compute_spear_loss` in `train.py`.
3. **Evaluate:** The agent runs `HSA_OVERRIDE_GFX_VERSION=11.0.0 python3 tools/autoresearch_sandbox.py`.
4. **Select:** If `FINAL_REWARD` improves, the agent runs `git commit` to save the mutation. If it decreases, the agent runs `git restore train.py` and tries a new mutation.
5. **Loop:** Repeat steps 2-4 indefinitely (or for a set number of iterations) until convergence.