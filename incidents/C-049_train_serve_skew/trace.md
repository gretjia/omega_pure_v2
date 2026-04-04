## 背景

Phase 11c (commit 89b4ebf, 2026-04-01 08:48) replaced the Softmax cross-entropy loss with Pointwise Huber Loss (delta=50 BP). This was a paradigm shift: the model now outputs **absolute BP** values instead of normalized logits. The training pipeline (`compute_spear_loss`) was updated, but the inference and backtest pipelines were not touched.

## 执行序列

1. **08:48 — Phase 11c feature commit (89b4ebf)**
   - `train.py`: `compute_spear_loss` rewritten — Softmax removed, Huber loss added
   - Model output semantics changed: logits → absolute BP
   - `backtest_5a.py` and `phase7_inference.py` NOT updated

2. **Post-training — backtest run on checkpoint**
   - `backtest_5a.py` line 161 still contained:
     ```python
     pred_bp = prediction.squeeze().cpu() * TARGET_STD + TARGET_MEAN
     ```
   - `TARGET_STD = 216.24`, `TARGET_MEAN = -5.08`
   - Model outputting ~20 BP (absolute) → multiplied by 216.24 → **4319 BP predictions**

3. **Symptom observed**: backtest engine produced nonsensical returns, portfolio positions wildly inflated

4. **10:49 — Fix commit (d744c4d)**
   - `backtest_5a.py`: `prediction.squeeze().cpu() * TARGET_STD + TARGET_MEAN` → `prediction.view(-1).cpu()`
   - `gcp/train.py`: `preds.std().item() * TARGET_STD` → `preds.std().item()`
   - Also fixed `.squeeze()` → `.view(-1)` (C-008 squeeze collapse prevention)
   - Applied to 4 files: `train.py`, `gcp/train.py`, `backtest_5a.py`, `gcp/backtest_5a.py`

5. **11:09 — C-049 lesson documented (203f0a4)**

## 环境

- **Code**: local repo + gcp/ mirror (6+ files with TARGET_STD references)
- **Docker**: `phase11-v3` image built from 89b4ebf (pre-fix code)
- **Data**: Vertex AI training job already running with old Docker image
- **Constants**: `TARGET_STD = 216.24` (historical standard deviation from Phase 2 train split), `TARGET_MEAN = -5.08`
