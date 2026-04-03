"""
OMEGA PURE 公理断言模块 (Axiom Assertion Module)
================================================
双层设计：
  Layer 1: 永恒物理公理（硬编码，不随版本变化，AI 不可修改）
  Layer 2: 架构公理（从 architect/current_spec.yaml 动态加载，随版本演进）

用法：
  python omega_axioms.py              # 独立自检
  python omega_axioms.py --verbose    # 详细输出
"""

import sys
import os
import math
from pathlib import Path

# ============================================================
# Layer 1: 永恒物理公理 (Eternal Physics Axioms)
# 只有 δ 和 POWER_INVERSE 是永恒不变的。AI 不可修改。
# ============================================================

DELTA = 0.5          # 平方根法则指数 (I ∝ Q^δ) — 宇宙拓扑常数
POWER_INVERSE = 2.0  # δ 的逆运算 (1/0.5 = 2.0)

# ============================================================
# Layer 2 回退值 (不是 Layer 1！per-stock c_i 标定取代)
# 仅用于 fallback / 向后兼容。见 architect/gdocs/id4
# ============================================================

C_DEFAULT = 0.842    # TSE 全局中位数 — Layer 2 回退值
C_TSE = C_DEFAULT    # 向后兼容别名


def load_spec(spec_path: str = None) -> dict:
    """从 architect/current_spec.yaml 加载 Layer 2 架构公理"""
    if spec_path is None:
        spec_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "architect", "current_spec.yaml"
        )

    if not os.path.exists(spec_path):
        print(f"[WARN] Spec file not found: {spec_path}")
        print("[WARN] Using hardcoded defaults for Layer 2 axioms")
        return _default_spec()

    # Pure-Python YAML parser (no PyYAML dependency required)
    return _parse_simple_yaml(spec_path)


def _default_spec() -> dict:
    """Layer 2 默认值（仅在 spec 文件缺失时使用）"""
    return {
        "version": "v3",
        "tensor": {
            "time_axis": 160,
            "spatial_axis": 10,
            "feature_axis": 10,
        },
        "physics": {
            "delta": 0.5,
            "c_default": C_DEFAULT,
        },
        "etl": {
            "vol_threshold": 50000,
            "window_size": 160,
            "stride": 20,
            "adv_fraction": 0.02,
            "feature_dim": 10,
        },
        "training": {
            "target_model": "Omega-TIB",
            "lambda_s": 0.001,
        },
    }


def _parse_simple_yaml(path: str) -> dict:
    """YAML parser supporting arbitrary nesting depth (no external deps).

    Uses indentation to track hierarchy. Each indent level (2 spaces)
    creates a deeper dict. Handles the full current_spec.yaml including
    hpo.search_space.macro_window.range etc.
    """
    result = {}
    # Stack of (indent_level, dict_ref) pairs
    stack = [(-1, result)]

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            # Count indentation (spaces)
            indent = len(line) - len(line.lstrip())

            # Remove inline comments
            if " #" in stripped:
                stripped = stripped[:stripped.index(" #")].strip()

            if ":" not in stripped:
                continue

            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            # Pop stack until we find a parent with smaller indent
            while len(stack) > 1 and stack[-1][0] >= indent:
                stack.pop()

            parent = stack[-1][1]

            if not value:
                # Section header — create nested dict
                new_dict = {}
                parent[key] = new_dict
                stack.append((indent, new_dict))
            else:
                # Key-value pair
                parent[key] = _cast_value(value)

    return result


def _cast_value(v: str):
    """Cast string value to appropriate Python type"""
    if v.startswith("[") and v.endswith("]"):
        # List like [B, 160, 10, 7]
        items = [x.strip() for x in v[1:-1].split(",")]
        return [_cast_scalar(x) for x in items]
    return _cast_scalar(v)


def _cast_scalar(v: str):
    """Cast scalar string to int, float, or str"""
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


# ============================================================
# 断言函数 (Assertion Functions)
# ============================================================

class AxiomViolation(Exception):
    """公理违反异常"""
    pass


def assert_layer1_physics(verbose: bool = False) -> list:
    """验证 Layer 1 永恒物理公理 (只有 δ 和 POWER_INVERSE 是永恒的)"""
    errors = []

    # 1. δ = 0.5 (平方根法则 — 宇宙拓扑常数)
    if DELTA != 0.5:
        errors.append(f"FATAL: δ = {DELTA}, expected 0.5")
    elif verbose:
        print("  [OK] δ = 0.5 (Square Root Law exponent — eternal)")

    # 2. Inverse power = 2.0 (1/δ)
    expected_inverse = 1.0 / DELTA
    if abs(POWER_INVERSE - expected_inverse) > 1e-6:
        errors.append(f"FATAL: POWER_INVERSE = {POWER_INVERSE}, expected {expected_inverse}")
    elif verbose:
        print("  [OK] POWER_INVERSE = 2.0 (1/δ — eternal)")

    # Note: c (TSE 0.842) is NO LONGER Layer 1. It was demoted to Layer 2
    # per architect directive (per-stock c_i calibration, 2026-03-18).
    # See architect/gdocs/id4_srl_friction_calibration.md
    if verbose:
        print(f"  [INFO] c_default = {C_TSE} (Layer 2 fallback, per-stock c_i takes precedence)")

    return errors


def _get_nested(d: dict, dotpath: str, default=None):
    """Safely get a nested value by dot-separated path, e.g. 'hpo.search_space.macro_window'"""
    keys = dotpath.split(".")
    current = d
    for k in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(k, default)
        if current is default:
            return default
    return current


def assert_layer2_architecture(spec: dict, verbose: bool = False) -> list:
    """验证 Layer 2 架构公理（从 spec 动态读取，支持全嵌套结构）"""
    errors = []
    tensor = spec.get("tensor", {})
    physics = spec.get("physics", {})
    etl = spec.get("etl", {})
    training = spec.get("training", {})
    target = spec.get("target", {})
    hpo = spec.get("hpo", {})
    backtest = spec.get("backtest", {})

    # --- Physics ---
    spec_delta = physics.get("delta")
    if spec_delta is not None and abs(float(spec_delta) - DELTA) > 1e-6:
        errors.append(f"CONFLICT: spec.physics.delta={spec_delta} != Layer1 DELTA={DELTA}")
    elif verbose:
        print("  [OK] spec.physics.delta consistent with Layer 1")

    # c is now Layer 2 (c_default), just verify it exists as fallback
    spec_c = physics.get("c_default")
    if spec_c is not None:
        if verbose:
            print(f"  [OK] spec.physics.c_default = {spec_c} (Layer 2 fallback)")
    else:
        # Backward compat: check old c_tse field
        spec_c = physics.get("c_tse")
        if spec_c is not None and verbose:
            print(f"  [WARN] spec uses old field 'c_tse', should be 'c_default'")

    # --- Tensor ---
    time_axis = tensor.get("time_axis")
    spatial_axis = tensor.get("spatial_axis")
    feature_axis = tensor.get("feature_axis")

    if time_axis is not None and int(time_axis) <= 0:
        errors.append(f"INVALID: tensor.time_axis={time_axis}, must be > 0")
    elif verbose:
        print(f"  [OK] tensor.time_axis = {time_axis}")

    if spatial_axis is not None and int(spatial_axis) < 2:
        errors.append(f"TOPOLOGY VIOLATION: spatial_axis={spatial_axis} < 2 — cannot collapse!")
    elif verbose:
        print(f"  [OK] tensor.spatial_axis = {spatial_axis} (topology preserved)")

    if feature_axis is not None:
        fa = int(feature_axis)
        if fa < 7:
            errors.append(f"INVALID: tensor.feature_axis={fa}, minimum 7 (original channels)")
        elif fa != 10:
            errors.append(f"SUSPECT: tensor.feature_axis={fa}, expected 10 (7 original + ΔP + V_D + σ_D)")
        elif verbose:
            print(f"  [OK] tensor.feature_axis = {fa} (10 channels: 7 base + ΔP + V_D + σ_D)")

    # --- ETL ---
    vol_threshold = etl.get("vol_threshold")
    if vol_threshold is not None and int(vol_threshold) < 1000:
        errors.append(f"SUSPECT: etl.vol_threshold={vol_threshold} < 1000")
    elif verbose:
        print(f"  [OK] etl.vol_threshold = {vol_threshold}")

    window_size = etl.get("window_size")
    if window_size is not None and int(window_size) < 10:
        errors.append(f"SUSPECT: etl.window_size={window_size} < 10")
    elif verbose:
        print(f"  [OK] etl.window_size = {window_size}")

    stride = etl.get("stride")
    if stride is not None and window_size is not None:
        if int(stride) >= int(window_size):
            errors.append(f"INVALID: stride={stride} >= window_size={window_size} (no overlap)")
        elif verbose:
            print(f"  [OK] etl.stride = {stride} (< window_size, overlap guaranteed)")

    etl_feat = etl.get("feature_dim")
    if etl_feat is not None and feature_axis is not None:
        if int(etl_feat) != int(feature_axis):
            errors.append(f"CONFLICT: etl.feature_dim={etl_feat} != tensor.feature_axis={feature_axis}")
        elif verbose:
            print(f"  [OK] etl.feature_dim = {etl_feat} (matches tensor.feature_axis)")

    # --- Training (Omega-TIB) ---
    model_name = training.get("target_model")
    if model_name is not None:
        if "MAE" in str(model_name):
            errors.append(f"STALE: training.target_model='{model_name}' still uses MAE naming (should be Omega-TIB)")
        elif verbose:
            print(f"  [OK] training.target_model = {model_name}")

    lambda_s = training.get("lambda_s")
    if lambda_s is not None:
        ls = float(lambda_s)
        if ls <= 0 or ls >= 1:
            errors.append(f"SUSPECT: training.lambda_s={ls}, expected 0 < λ_s < 1")
        elif verbose:
            print(f"  [OK] training.lambda_s = {ls}")

    masking = training.get("masking", {})
    if isinstance(masking, dict):
        mask_min = masking.get("min_bars")
        mask_max = masking.get("max_bars")
        if mask_min is not None and mask_max is not None:
            if int(mask_min) >= int(mask_max):
                errors.append(f"INVALID: masking.min_bars={mask_min} >= max_bars={mask_max}")
            elif verbose:
                print(f"  [OK] masking.min_bars={mask_min}, max_bars={mask_max}")
        train_only = masking.get("train_only")
        if train_only is not None and str(train_only).lower() != "true":
            errors.append(f"DANGER: masking.train_only={train_only}, must be true (inference must see full data)")
        elif verbose and train_only is not None:
            print(f"  [OK] masking.train_only = {train_only}")

    # --- Target ---
    target_type = target.get("type")
    if target_type is not None:
        if verbose:
            print(f"  [OK] target.type = {target_type}")
    else:
        if verbose:
            print("  [WARN] target section missing from spec")

    payoff_h = target.get("payoff_horizon")
    if payoff_h is not None:
        if int(payoff_h) < 1:
            errors.append(f"INVALID: target.payoff_horizon={payoff_h}, must be >= 1")
        elif verbose:
            print(f"  [OK] target.payoff_horizon = {payoff_h}")

    # --- HPO ---
    hpo_metric = hpo.get("metric")
    if hpo_metric is not None:
        metric_str = str(hpo_metric).lower()
        allowed_metrics = {"fvu", "portfolio_return", "d9_d0_spread", "d9-d0 spread", "rank_ic"}
        if any(m in metric_str for m in allowed_metrics):
            if verbose:
                print(f"  [OK] hpo.metric = {hpo_metric}")
        else:
            errors.append(f"SUSPECT: hpo.metric='{hpo_metric}', expected one of {allowed_metrics}")

    search_space = hpo.get("search_space", {})
    if isinstance(search_space, dict) and search_space:
        if verbose:
            print(f"  [OK] hpo.search_space has {len(search_space)} parameters")
    elif verbose:
        print("  [WARN] hpo.search_space is empty or missing")

    # --- Backtest (full coverage) ---
    bt_criterion = backtest.get("success_criterion")
    if bt_criterion is not None:
        if "3.0" not in str(bt_criterion):
            errors.append(f"SUSPECT: backtest.success_criterion='{bt_criterion}', expected payoff_ratio > 3.0")
        elif verbose:
            print(f"  [OK] backtest.success_criterion = {bt_criterion}")

    bt_delay = backtest.get("execution_delay")
    if bt_delay is not None:
        if "VWAP" not in str(bt_delay):
            errors.append(f"SUSPECT: backtest.execution_delay='{bt_delay}', expected VWAP-based")
        elif verbose:
            print(f"  [OK] backtest.execution_delay = {bt_delay}")

    bt_t1 = backtest.get("t_plus_1_exposure")
    if bt_t1 is not None:
        if str(bt_t1).lower() != "true":
            errors.append(f"DANGER: backtest.t_plus_1_exposure={bt_t1}, must be true (A-share T+1 rule)")
        elif verbose:
            print(f"  [OK] backtest.t_plus_1_exposure = {bt_t1}")

    bt_exit = backtest.get("exit_strategy")
    if bt_exit is not None:
        if "volume" not in str(bt_exit).lower() and "clocked" not in str(bt_exit).lower():
            errors.append(f"SUSPECT: backtest.exit_strategy='{bt_exit}', expected volume-clocked")
        elif verbose:
            print(f"  [OK] backtest.exit_strategy = {bt_exit}")

    # --- SRL Calibration ---
    srl_cal = spec.get("srl_calibration", {})
    if isinstance(srl_cal, dict) and srl_cal:
        cal_method = srl_cal.get("method")
        cal_output = srl_cal.get("output")
        cal_bounds = srl_cal.get("physical_bounds")
        if cal_method is not None and "OLS" not in str(cal_method):
            errors.append(f"SUSPECT: srl_calibration.method='{cal_method}', expected OLS-based")
        elif verbose and cal_method:
            print(f"  [OK] srl_calibration.method = {cal_method}")
        if cal_output is not None:
            if not str(cal_output).endswith(".json"):
                errors.append(f"SUSPECT: srl_calibration.output='{cal_output}', expected .json file")
            elif verbose:
                print(f"  [OK] srl_calibration.output = {cal_output}")
        if cal_bounds is not None:
            if isinstance(cal_bounds, list) and len(cal_bounds) == 2:
                lo, hi = float(cal_bounds[0]), float(cal_bounds[1])
                if lo >= hi or lo <= 0:
                    errors.append(f"INVALID: srl_calibration.physical_bounds={cal_bounds}, need 0 < lo < hi")
                elif verbose:
                    print(f"  [OK] srl_calibration.physical_bounds = [{lo}, {hi}]")
            elif verbose:
                print(f"  [WARN] srl_calibration.physical_bounds format unexpected: {cal_bounds}")
    elif verbose:
        print("  [WARN] srl_calibration section missing from spec")

    # --- Model Architecture ---
    model_arch = spec.get("model_architecture", {})
    if isinstance(model_arch, dict) and model_arch:
        arch_name = model_arch.get("name")
        if arch_name is not None:
            if "MAE" in str(arch_name):
                errors.append(f"STALE: model_architecture.name='{arch_name}' uses MAE naming")
            elif verbose:
                print(f"  [OK] model_architecture.name = {arch_name}")
        # Check 4-layer structure exists
        for layer_key in ["layer_1_physics", "layer_2_topology", "layer_3_compression", "layer_4_prediction"]:
            if model_arch.get(layer_key) is not None:
                if verbose:
                    print(f"  [OK] model_architecture.{layer_key} = {model_arch[layer_key]}")
            else:
                errors.append(f"MISSING: model_architecture.{layer_key}")
    elif verbose:
        print("  [WARN] model_architecture section missing from spec")

    # --- Additional Training fields ---
    masking_strategy = _get_nested(spec, "training.masking.strategy")
    if masking_strategy is not None:
        if "block" not in str(masking_strategy).lower():
            errors.append(f"SUSPECT: masking.strategy='{masking_strategy}', expected block-based")
        elif verbose:
            print(f"  [OK] masking.strategy = {masking_strategy}")

    masking_prob = _get_nested(spec, "training.masking.probability")
    if masking_prob is not None:
        mp = float(masking_prob)
        if mp <= 0 or mp > 1:
            errors.append(f"INVALID: masking.probability={mp}, expected 0 < p <= 1")
        elif verbose:
            print(f"  [OK] masking.probability = {mp}")

    masking_keep = _get_nested(spec, "training.masking.keep_last")
    if masking_keep is not None:
        if int(masking_keep) < 1:
            errors.append(f"INVALID: masking.keep_last={masking_keep}, must be >= 1")
        elif verbose:
            print(f"  [OK] masking.keep_last = {masking_keep}")

    # --- Additional ETL fields ---
    adv_frac = etl.get("adv_fraction")
    if adv_frac is not None:
        af = float(adv_frac)
        if af <= 0 or af >= 1:
            errors.append(f"INVALID: etl.adv_fraction={af}, expected 0 < x < 1")
        elif verbose:
            print(f"  [OK] etl.adv_fraction = {af}")

    spatial_depth = etl.get("spatial_depth")
    if spatial_depth is not None and spatial_axis is not None:
        if int(spatial_depth) != int(spatial_axis):
            errors.append(f"CONFLICT: etl.spatial_depth={spatial_depth} != tensor.spatial_axis={spatial_axis}")
        elif verbose:
            print(f"  [OK] etl.spatial_depth = {spatial_depth} (matches spatial_axis)")

    return errors


def assert_numerical_stability(tensor_data=None, verbose: bool = False) -> list:
    """检查数值稳定性（可选，传入实际张量数据）"""
    errors = []
    if tensor_data is None:
        if verbose:
            print("  [SKIP] No tensor data provided for numerical stability check")
        return errors

    try:
        import numpy as np
        arr = np.asarray(tensor_data)
        if np.any(np.isnan(arr)):
            errors.append(f"NaN DETECTED in tensor (shape={arr.shape})")
        elif verbose:
            print(f"  [OK] No NaN in tensor (shape={arr.shape})")

        if np.any(np.isinf(arr)):
            errors.append(f"Inf DETECTED in tensor (shape={arr.shape})")
        elif verbose:
            print(f"  [OK] No Inf in tensor (shape={arr.shape})")
    except ImportError:
        if verbose:
            print("  [SKIP] NumPy not available for numerical stability check")

    return errors


def assert_tensor_shape(tensor_data, spec: dict, verbose: bool = False) -> list:
    """验证实际张量形状是否匹配 spec"""
    errors = []
    tensor_spec = spec.get("tensor", {})
    expected = (
        int(tensor_spec.get("time_axis", 160)),
        int(tensor_spec.get("spatial_axis", 10)),
        int(tensor_spec.get("feature_axis", 10)),
    )

    try:
        import numpy as np
        arr = np.asarray(tensor_data)
    except ImportError:
        if verbose:
            print("  [SKIP] NumPy not available for shape check")
        return errors

    actual = arr.shape[-3:] if arr.ndim >= 3 else arr.shape
    if actual != expected:
        errors.append(f"Tensor shape mismatch: expected {expected}, got {actual}")
    elif verbose:
        print(f"  [OK] Tensor shape {actual} matches spec")

    return errors


def assert_code_constants(verbose: bool = False) -> list:
    """验证代码中的物理常数未被篡改"""
    errors = []
    core_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "omega_epiplexity_plus_core.py"
    )

    if not os.path.exists(core_path):
        if verbose:
            print(f"  [SKIP] Core file not found: {core_path}")
        return errors

    with open(core_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check c_constant — either hardcoded default 0.842 (legacy) or accepts c_friction in forward() (post Phase 0.6)
    has_c_hardcoded = "c_constant: float = 0.842" in content
    # Verify c_friction appears as a parameter in a forward() method signature, not just in comments
    import re as _re
    has_c_forward_param = bool(_re.search(r'def\s+forward\s*\([^)]*c_friction', content))
    if has_c_forward_param:
        if verbose:
            print("  [OK] AxiomaticSRLInverter.forward() accepts c_friction (per-stock, id4 contract)")
    elif has_c_hardcoded:
        if verbose:
            print("  [OK] AxiomaticSRLInverter.c_constant = 0.842 (legacy, Phase 0.6 pending)")
    else:
        errors.append("CODE TAMPERING: AxiomaticSRLInverter has neither c_constant=0.842 nor c_friction in forward()")

    # Check power_constant
    if "self.power_constant = 2.0" not in content:
        errors.append("CODE TAMPERING: power_constant in AxiomaticSRLInverter is not 2.0")
    elif verbose:
        print("  [OK] AxiomaticSRLInverter.power_constant = 2.0")

    # Check torch.no_grad() on SRL (physics layer must not be learnable)
    if "torch.no_grad()" not in content:
        errors.append("CODE TAMPERING: SRL inverter must run under torch.no_grad()")
    elif verbose:
        print("  [OK] SRL inverter runs under torch.no_grad()")

    return errors


# ============================================================
# 主入口 (Main Entry)
# ============================================================

def run_full_audit(verbose: bool = False, spec_path: str = None) -> bool:
    """运行完整公理审计，返回是否全部通过"""
    all_errors = []

    print("=" * 50)
    print(" OMEGA AXIOM AUDIT")
    print("=" * 50)

    print("\n[Layer 1] Eternal Physics Axioms:")
    errs = assert_layer1_physics(verbose)
    all_errors.extend(errs)

    print("\n[Layer 2] Architecture Axioms (from spec):")
    spec = load_spec(spec_path)
    errs = assert_layer2_architecture(spec, verbose)
    all_errors.extend(errs)

    print("\n[Code] Physical Constants in Source:")
    errs = assert_code_constants(verbose)
    all_errors.extend(errs)

    print("\n" + "=" * 50)
    if all_errors:
        print(f" AUDIT FAILED — {len(all_errors)} violation(s):")
        for e in all_errors:
            print(f"   !! {e}")
        print("=" * 50)
        return False
    else:
        print(" AUDIT PASSED — All axioms verified")
        print("=" * 50)
        return True


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    passed = run_full_audit(verbose=verbose)
    sys.exit(0 if passed else 1)
