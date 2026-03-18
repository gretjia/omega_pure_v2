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
# 这些是物理常数，不随架构版本变化。AI 不可修改。
# ============================================================

DELTA = 0.5          # 平方根法则指数 (I ∝ Q^δ)
C_TSE = 0.842        # TSE 实证常数 (无量纲冲击系数)
POWER_INVERSE = 2.0  # δ 的逆运算 (1/0.5 = 2.0)


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
            "feature_axis": 7,
        },
        "physics": {
            "delta": 0.5,
            "c_tse": 0.842,
        },
        "etl": {
            "vol_threshold": 50000,
            "window_size": 160,
            "stride": 20,
            "adv_fraction": 0.02,
        },
    }


def _parse_simple_yaml(path: str) -> dict:
    """Minimal YAML parser for our flat spec format (no external deps)"""
    result = {}
    current_section = None

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            # Count indentation
            indent = len(line) - len(line.lstrip())

            # Remove inline comments
            if " #" in stripped:
                stripped = stripped[:stripped.index(" #")].strip()

            if ":" not in stripped:
                continue

            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if indent == 0 and not value:
                # Top-level section
                current_section = key
                result[current_section] = {}
            elif indent == 0 and value:
                # Top-level scalar
                result[key] = _cast_value(value)
            elif current_section is not None and value:
                result[current_section][key] = _cast_value(value)

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
    """验证 Layer 1 永恒物理公理"""
    errors = []

    # 1. δ = 0.5 (平方根法则)
    if DELTA != 0.5:
        errors.append(f"FATAL: δ = {DELTA}, expected 0.5")
    elif verbose:
        print("  [OK] δ = 0.5 (Square Root Law exponent)")

    # 2. c = 0.842 (TSE constant)
    if abs(C_TSE - 0.842) > 1e-6:
        errors.append(f"FATAL: c_TSE = {C_TSE}, expected 0.842")
    elif verbose:
        print("  [OK] c = 0.842 (TSE empirical constant)")

    # 3. Inverse power = 2.0
    expected_inverse = 1.0 / DELTA
    if abs(POWER_INVERSE - expected_inverse) > 1e-6:
        errors.append(f"FATAL: POWER_INVERSE = {POWER_INVERSE}, expected {expected_inverse}")
    elif verbose:
        print("  [OK] POWER_INVERSE = 2.0 (1/δ)")

    return errors


def assert_layer2_architecture(spec: dict, verbose: bool = False) -> list:
    """验证 Layer 2 架构公理（从 spec 动态读取）"""
    errors = []
    tensor = spec.get("tensor", {})
    physics = spec.get("physics", {})
    etl = spec.get("etl", {})

    # 4. Spec 中的物理常数必须与 Layer 1 一致
    spec_delta = physics.get("delta")
    if spec_delta is not None and abs(float(spec_delta) - DELTA) > 1e-6:
        errors.append(f"CONFLICT: spec.physics.delta={spec_delta} != Layer1 DELTA={DELTA}")
    elif verbose:
        print("  [OK] spec.physics.delta consistent with Layer 1")

    spec_c = physics.get("c_tse")
    if spec_c is not None and abs(float(spec_c) - C_TSE) > 1e-6:
        errors.append(f"CONFLICT: spec.physics.c_tse={spec_c} != Layer1 C_TSE={C_TSE}")
    elif verbose:
        print("  [OK] spec.physics.c_tse consistent with Layer 1")

    # 5. 张量维度合法性
    time_axis = tensor.get("time_axis")
    spatial_axis = tensor.get("spatial_axis")
    feature_axis = tensor.get("feature_axis")

    if time_axis is not None and int(time_axis) <= 0:
        errors.append(f"INVALID: tensor.time_axis={time_axis}, must be > 0")
    elif verbose:
        print(f"  [OK] tensor.time_axis = {time_axis}")

    if spatial_axis is not None and int(spatial_axis) <= 0:
        errors.append(f"INVALID: tensor.spatial_axis={spatial_axis}, must be > 0")
    elif verbose:
        print(f"  [OK] tensor.spatial_axis = {spatial_axis}")

    # 6. 空间轴不可被拍扁（核心拓扑不变量）
    if spatial_axis is not None and int(spatial_axis) < 2:
        errors.append(f"TOPOLOGY VIOLATION: spatial_axis={spatial_axis} < 2 — spatial axis cannot be collapsed!")
    elif verbose:
        print(f"  [OK] spatial_axis = {spatial_axis} (topology preserved)")

    if feature_axis is not None and int(feature_axis) <= 0:
        errors.append(f"INVALID: tensor.feature_axis={feature_axis}, must be > 0")
    elif verbose:
        print(f"  [OK] tensor.feature_axis = {feature_axis}")

    # 7. ETL 参数合法性
    vol_threshold = etl.get("vol_threshold")
    if vol_threshold is not None and int(vol_threshold) < 1000:
        errors.append(f"SUSPECT: etl.vol_threshold={vol_threshold} < 1000 (micro-bars risk)")
    elif verbose:
        print(f"  [OK] etl.vol_threshold = {vol_threshold}")

    window_size = etl.get("window_size")
    if window_size is not None and int(window_size) < 10:
        errors.append(f"SUSPECT: etl.window_size={window_size} < 10 (too short)")
    elif verbose:
        print(f"  [OK] etl.window_size = {window_size}")

    stride = etl.get("stride")
    if stride is not None and window_size is not None:
        if int(stride) >= int(window_size):
            errors.append(f"INVALID: stride={stride} >= window_size={window_size} (no overlap)")
        elif verbose:
            print(f"  [OK] etl.stride = {stride} (< window_size, overlap guaranteed)")

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
        int(tensor_spec.get("feature_axis", 7)),
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

    # Check c_constant default
    if "c_constant: float = 0.842" not in content:
        errors.append("CODE TAMPERING: c_constant default in AxiomaticSRLInverter is not 0.842")
    elif verbose:
        print("  [OK] AxiomaticSRLInverter.c_constant = 0.842")

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
