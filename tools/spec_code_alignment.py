#!/usr/bin/env python3
"""
spec_code_alignment.py — Meta-Harness V3 Spec-Code 对齐检查

检查 architect/current_spec.yaml 中的关键参数是否与代码默认值一致。
防止 C-057 类漂移: spec 写 window_size_s=10, 代码默认 4, 跑了 17 个 job 没人发现。

Usage:
    python3 tools/spec_code_alignment.py          # 检查所有参数
    python3 tools/spec_code_alignment.py --fix     # 检查并输出修复建议

Exit codes:
    0 = 全部对齐
    1 = 发现漂移
"""

import os
import re
import sys
import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_spec():
    """加载 current_spec.yaml"""
    spec_path = os.path.join(PROJECT_ROOT, "architect", "current_spec.yaml")
    with open(spec_path) as f:
        return yaml.safe_load(f)


def grep_default(files, param_name):
    """从代码文件中提取 argparse default 值"""
    results = {}
    for fpath in files:
        full_path = os.path.join(PROJECT_ROOT, fpath)
        if not os.path.exists(full_path):
            results[fpath] = "FILE_NOT_FOUND"
            continue
        with open(full_path) as f:
            content = f.read()
        # 匹配 argparse: --param_name ... default=VALUE
        pattern = rf'--{param_name}["\s,].*?default\s*=\s*([^\s,\)]+)'
        m = re.search(pattern, content)
        if m:
            results[fpath] = m.group(1).strip("'\"")
        else:
            # 尝试匹配直接赋值: PARAM_NAME = VALUE
            pattern2 = rf'{param_name}\s*=\s*([^\s,\)#]+)'
            m2 = re.search(pattern2, content, re.IGNORECASE)
            if m2:
                results[fpath] = m2.group(1).strip("'\"")
            else:
                results[fpath] = "NOT_FOUND"
    return results


def check_alignment():
    """检查 spec 与代码的参数对齐"""
    try:
        spec = load_spec()
    except Exception as e:
        print(f"ERROR: Cannot load spec: {e}")
        return 1

    # 定义检查项: (spec_path, code_files, param_name_in_code)
    checks = []

    # 从 spec 中提取 fixed_params
    hpo = spec.get("hpo", {})
    fixed = hpo.get("fixed_params", {})

    code_files = ["train.py", "gcp/train.py"]

    for param, spec_val in fixed.items():
        checks.append({
            "name": param,
            "spec_value": str(spec_val),
            "code_files": code_files,
        })

    # 额外检查: model 参数
    model = spec.get("model", {})
    for param in ["hidden_dim", "num_layers", "dropout"]:
        if param in model:
            checks.append({
                "name": param,
                "spec_value": str(model[param]),
                "code_files": code_files,
            })

    # 执行检查
    mismatches = []
    aligned = []
    not_found = []

    for check in checks:
        code_vals = grep_default(check["code_files"], check["name"])
        for fpath, code_val in code_vals.items():
            if code_val == "FILE_NOT_FOUND":
                not_found.append(f"  ? {check['name']}: {fpath} not found")
            elif code_val == "NOT_FOUND":
                not_found.append(f"  ? {check['name']}: not found in {fpath}")
            elif str(code_val) != str(check["spec_value"]):
                mismatches.append(
                    f"  ✗ {check['name']}: spec={check['spec_value']}, "
                    f"code={code_val} in {fpath}"
                )
            else:
                aligned.append(f"  ✓ {check['name']}: {check['spec_value']} in {fpath}")

    # 输出
    print("=== SPEC-CODE ALIGNMENT CHECK ===")
    print(f"Spec: architect/current_spec.yaml")
    print(f"Checked {len(checks)} parameters across {len(code_files)} files")
    print()

    if aligned:
        print("ALIGNED:")
        for a in aligned:
            print(a)
        print()

    if mismatches:
        print("MISMATCHES (C-057 class drift):")
        for m in mismatches:
            print(m)
        print()

    if not_found:
        print("NOT FOUND (may be set via config, not argparse):")
        for n in not_found:
            print(n)
        print()

    if mismatches:
        print(f"VERDICT: FAIL — {len(mismatches)} parameter(s) diverged from spec")
        return 1
    else:
        print(f"VERDICT: PASS — all found parameters match spec")
        return 0


if __name__ == "__main__":
    sys.exit(check_alignment())
