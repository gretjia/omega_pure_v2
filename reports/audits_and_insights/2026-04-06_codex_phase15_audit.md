## Checkpoint 1: Plan Internal Logic Consistency
**Verdict**: FAIL
**Evidence**:
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:179-190` defines Step 1 success as `Rank IC > 0.029`, but the branch table only covers `>0.040`, `0.030~0.040`, `≈0.029`, and `<0.020`.
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:270-272` says Step 3 runs when `Step 1 IC > 0.025` and MLP is weaker, while `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:189` and `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:348-351` skip Step 3 for `IC ≈ 0.029`.
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:262-264` defines MLP branches for `<0.3x`, `0.5~0.8x`, and `<15% gap`, leaving `0.3~0.5x` and `0.8~0.85x` uncovered.
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:297` says "感受野 (Step 4) 是更重要的限制", but `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:358-360` says "无差异 → 容量够，跳 Step 4".
**Reasoning**: The thresholds do not partition the result space cleanly, and they produce contradictory downstream actions. A control-experiment plan needs one unambiguous next step for every reachable metric range. As written, several plausible outcomes are either undefined or routed inconsistently.

## Checkpoint 2: Spec Changes Aligned with Plan
**Verdict**: FAIL
**Evidence**:
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:404-419` proposes new CLI/spec surface for `grad_accum`, `swa_start_epoch`, `embargo_shards`, and `training.swa.tau: 0.999`.
- `architect/current_spec.yaml:90-134` contains no `training.gradient_accumulation`, no `training.swa`, and no `training.embargo_shards`.
- `architect/current_spec.yaml:163-189` still exposes `hidden_dim` as an HPO choice and fixes only `batch_size`, `epochs`, `steps_per_epoch`, `grad_clip`, `mask_prob`, and `lambda_s`; it does not encode the Phase 15 Step 1 control setup from `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:92-99` and `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:153-167`.
- `train.py:487-553` and `gcp/train.py:487-553` do not define `--grad_accum`, `--swa_start_epoch`, or `--embargo_shards`.
**Reasoning**: The Phase 15 configuration exists only in the draft directive. The live YAML and both executable training scripts still reflect the older Phase 13 surface, so the spec, plan, and code are not synchronized. That makes the planned experiment non-reproducible from the checked-in config.

## Checkpoint 3: Gradient Accumulation + OneCycleLR `total_steps`
**Verdict**: FAIL
**Evidence**:
- `train.py:351-380` and `gcp/train.py:351-380` zero gradients and call `optimizer.step()` plus `scheduler.step()` every batch.
- `train.py:651-655` and `gcp/train.py:651-655` set `total_steps = args.epochs * args.steps_per_epoch`.
- `train.py:487-553` and `gcp/train.py:487-553` contain no `--grad_accum` argument or remainder-handling policy.
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:94-98`, `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:123-135`, and `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:164` propose `grad_accum=16` and `OneCycleLR total_steps = 4,687`.
- PyTorch `OneCycleLR` docs state that the schedule changes after every batch/optimizer step and that `total_steps` is the total number of scheduler steps: `https://docs.pytorch.org/docs/stable/generated/torch.optim.lr_scheduler.OneCycleLR` lines 3188-3197, 3221-3233, 3302-3304.
**Reasoning**: The current code is mathematically correct only for accumulation factor `1`, because it performs `15 × 5000 = 75,000` optimizer/scheduler steps. Under the Phase 15 proposal, `scheduler.step()` must advance on optimizer updates after accumulation, not on raw microbatches. The plan's own `75000/16 = 4687` figure is underspecified because it is non-integer (`4687.5`); with the shown modulo-16 loop and no flush/carry rule, `5000` microbatches per epoch yield `312` optimizer steps per epoch and `4680` total.

## Checkpoint 4: SWA Compatibility with `torch.optim.swa_utils`
**Verdict**: FAIL
**Evidence**:
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:95` and `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:414-417` describe SWA with `tau=0.999`.
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:104-117` uses `AveragedModel(model)` with no `avg_fn` or `multi_avg_fn`.
- PyTorch SWA docs state that plain `AveragedModel(model)` performs equal-weight SWA by default, while EMA with decay requires a custom averaging function such as `get_ema_multi_avg_fn(decay)`: `https://docs.pytorch.org/docs/stable/optim.html` lines 3878-3895 and 3903-3904.
- `train.py:170-171` plus `omega_epiplexity_plus_core.py:164-176` show `LayerNorm` only; there is no `BatchNorm` in the audited model path.
- PyTorch `update_bn()` assumes a tensor batch or a tuple/list whose first element is the model input: `https://docs.pytorch.org/docs/stable/optim.html` lines 3925-3932 and 4006-4025. This repo's loader batches are dict-shaped at `train.py:347-349`, and the model forward requires `(x_2d, c_friction)` at `train.py:173-243`.
**Reasoning**: The proposed SWA snippet does not implement the advertised `tau=0.999`; it implements plain equal-weight SWA unless the averaging function is changed. The `update_bn()` call is unnecessary for the current LayerNorm-only model, and if BatchNorm were introduced later the existing dict batch format would not satisfy `update_bn()` without a custom adapter loop. As written, the Phase 15 SWA spec is semantically inconsistent with PyTorch's actual API.

## Checkpoint 5: Embargo Gap of 2 Shards
**Verdict**: WARNING
**Evidence**:
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:58-60` drops the last 2 train shards and first 2 val shards, and claims `~10,000 样本 × stride=20 = ~200 bars`.
- `architect/current_spec.yaml:60-65` sets `etl.window_size: 160`, `etl.stride: 20`, and `etl.shard_max_count: 5000`.
**Reasoning**: A one-window embargo only needs `160 / 20 = 8` skipped sample starts. If shards are even moderately populated and truly time-ordered, dropping 2 shards on each side is far more than enough to cover a 160-bar window. The plan's arithmetic is still wrong, though: `10,000 × 20 = 200,000` bars, not `200`, and the exact realized bar gap is INCONCLUSIVE without the actual per-shard sample counts.

## Checkpoint 6: MLP Baseline Fairness
**Verdict**: WARNING
**Evidence**:
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:216-240` builds the MLP input from the same audited channels (`0-4`, `7-9`) and the same `c_friction`-driven SRL computation used by Omega.
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:243-249` explicitly keeps SRL and FRT, removing only FWT topology, bottleneck compression, and attention pooling.
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:253-254` says Step 2 uses the same training config and split as Step 1, changing only the model class.
- `train.py:577-622` defines the shared temporal split and loaders, but `train.py:625-630` hardcodes `OmegaTIBWithMasking` and `train.py:487-553` exposes no model-selection flag. The same is true in `gcp/train.py:577-630`.
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:247` states the MLP is `~5M` parameters versus `24.6K` for Omega.
**Reasoning**: On paper, the baseline is fair on data source, feature transform, and train/val split, so there is no obvious leakage advantage in the proposed comparison. The practical implementation is still incomplete because the current code cannot instantiate the MLP path, and the planned baseline is intentionally much larger, so the experiment isolates architectural topology more cleanly than it isolates capacity-matched modeling power.

## Checkpoint 7: Overlapping Windows via `unfold` and RPB Compatibility
**Verdict**: WARNING
**Evidence**:
- `omega_epiplexity_plus_core.py:65-79` defines relative-position bias purely from local `window_t` and `window_s` coordinates.
- `omega_epiplexity_plus_core.py:91-117` extracts non-overlapping windows, applies attention within each window, then reconstructs with a non-overlap-specific `.view(... T_pad // self.window_t ...)`.
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:317-323` changes only the time-window extraction to `x_nd.unfold(1, self.window_t, stride_t)` while keeping the same window sizes, and `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:328` says the RPB parameter count stays unchanged.
**Reasoning**: Relative-position bias itself is local within each window, so overlapping extraction is compatible with the existing bias table and does not require reparameterizing RPB. The missing piece is output merging: once bars appear in multiple windows, the current reshape-back path no longer defines how overlapping window outputs are aggregated. The plan is therefore compatible in principle but incomplete in implementation terms.

## Checkpoint 8: Omissions, Risks, or Blind Spots Not Covered Above
**Verdict**: FAIL
**Evidence**:
- The plan references `gcp/phase15_step1_config.yaml` at `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:141-169`, but that file does not exist in the audited repository.
- `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:15-16` explicitly stays on `v3 shards`, while `architect/directives/2026-04-06_phase15_pipeline_stabilization.md:51` admits `meta.json` may have no `date` field and proposes a fallback using `symbol + sample_id`.
- `architect/current_spec.yaml:94-97` says the training IC is still a batch-level approximation because shard metadata lacks `date`, and `architect/current_spec.yaml:156-157` says the primary HPO metric is still a global approximation pending per-date grouping.
- `architect/current_spec.yaml:66` defines the shard contract as `manifold_2d.npy + target.npy + c_friction + meta.json`; it does not define a `sample_id` field for the Step 0 fallback.
**Reasoning**: The plan is missing at least one referenced execution artifact, and its Step 0 fallback is not grounded in the current shard contract. More importantly, Phase 15 still evaluates success on the same documented batch/global approximation rather than the intended per-date metric, so even a "stabilized" run may remain confounded by the unresolved `date`-field limitation. That is a material blind spot for both leakage diagnosis and threshold comparison.

## Summary
- Total: 0 PASS, 3 WARNING, 5 FAIL
- Critical blockers (if any): Spec and code do not implement the proposed Phase 15 controls; the planned accumulation/OneCycle math is wrong or underspecified; the SWA section conflates EMA (`tau=0.999`) with plain `AveragedModel`; and the phase still relies on the known batch/global metric approximation while the referenced `gcp/phase15_step1_config.yaml` is missing.
- Recommendations: Update `architect/current_spec.yaml`, `train.py`, and `gcp/train.py` together before execution; define exact accumulation semantics for remainder microbatches and derive `global_step`/`OneCycleLR.total_steps` from optimizer steps; choose either true SWA or true EMA explicitly and remove the unnecessary `update_bn()` path for the current LayerNorm-only model; and resolve the `date`/`sample_id` gap before using Phase 15 thresholds to diagnose leakage or pipeline ceilings.
