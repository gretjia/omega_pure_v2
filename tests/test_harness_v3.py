"""
Meta-Harness V3 Smoke Test — 烟测 rule-engine.sh 的全部规则

不接触任何真实代码/模型/数据。只验证:
  1. Block 规则正确拦截违规内容 (exit 2)
  2. Warn 规则正确警告但放行 (exit 0, stderr 有输出)
  3. 安全内容正确放行 (exit 0)
  4. 免检文件正确跳过 (exit 0)
  5. legacy lesson-enforcer.sh 仍然工作

Run:
    python3 -m pytest tests/test_harness_v3.py -v
    python3 tests/test_harness_v3.py
"""

import json
import os
import subprocess
import time

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULE_ENGINE = os.path.join(PROJECT_ROOT, ".claude", "hooks", "rule-engine.sh")
LESSON_ENFORCER = os.path.join(PROJECT_ROOT, ".claude", "hooks", "lesson-enforcer.sh")


def run_hook(hook_path, file_path, content):
    """模拟 Claude Code hook 调用, 返回 (exit_code, stderr)"""
    payload = json.dumps({
        "tool_name": "Write",
        "tool_input": {
            "file_path": file_path,
            "content": content
        }
    })
    result = subprocess.run(
        ["bash", hook_path],
        input=payload,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=30
    )
    return result.returncode, result.stderr


# ================================================================
# Rule Engine — Block 级规则
# ================================================================

class TestRuleEngineBlock:
    """Block 级规则: 必须 exit 2 拦截"""

    def test_R003_device_hardcode_cpu(self):
        """R-003: torch.device("cpu") 硬编码必须被拦截"""
        code, stderr = run_hook(RULE_ENGINE, "/tmp/test.py",
            'device = torch.device("cpu")')
        assert code == 2, f"R-003 should block, got exit {code}"
        assert "C-039" in stderr

    def test_R003_safe_device_passes(self):
        """R-003: auto-detect 写法应放行"""
        code, stderr = run_hook(RULE_ENGINE, "/tmp/test.py",
            'device = torch.device("cuda" if torch.cuda.is_available() else "cpu")')
        assert code == 0, f"Safe device code should pass, got exit {code}"

    def test_R008_softmax_dim0(self):
        """R-008: softmax(dim=0) 必须被拦截"""
        code, stderr = run_hook(RULE_ENGINE, "/tmp/test.py",
            'out = F.softmax(logits, dim=0)')
        assert code == 2, f"R-008 should block softmax dim=0, got exit {code}"
        assert "C-042" in stderr or "C-045" in stderr

    def test_R008_batchnorm(self):
        """R-008: BatchNorm 必须被拦截"""
        code, stderr = run_hook(RULE_ENGINE, "/tmp/test.py",
            'norm = nn.BatchNorm1d(64)')
        assert code == 2, f"R-008 should block BatchNorm, got exit {code}"

    def test_R008_softmax_dim1_passes(self):
        """R-008: softmax(dim=1) 应放行"""
        code, stderr = run_hook(RULE_ENGINE, "/tmp/test.py",
            'out = F.softmax(logits, dim=1)')
        assert code == 0

    def test_R004_delta_modification(self):
        """R-004: 修改 delta 物理常数必须被拦截"""
        code, stderr = run_hook(RULE_ENGINE,
            os.path.join(PROJECT_ROOT, "omega_epiplexity_plus_core.py"),
            'delta = 0.7  # changed')
        assert code == 2, f"R-004 should block delta change, got exit {code}"

    def test_R004_delta_correct_passes(self):
        """R-004: delta = 0.5 应放行"""
        code, stderr = run_hook(RULE_ENGINE,
            os.path.join(PROJECT_ROOT, "omega_epiplexity_plus_core.py"),
            'delta = 0.5')
        assert code == 0


# ================================================================
# Rule Engine — Warn 级规则
# ================================================================

class TestRuleEngineWarn:
    """Warn 级规则: exit 0 但 stderr 有警告"""

    def test_R009_deprecated_target_std(self):
        """R-009: TARGET_STD 应触发警告"""
        code, stderr = run_hook(RULE_ENGINE, "/tmp/test.py",
            'pred = output * TARGET_STD')
        assert code == 0, f"R-009 should warn not block, got exit {code}"
        assert "TARGET_STD" in stderr or "C-049" in stderr

    def test_R009_deprecated_squeeze(self):
        """R-009: .squeeze() 应触发警告"""
        code, stderr = run_hook(RULE_ENGINE, "/tmp/test.py",
            'x = tensor.squeeze()')
        assert code == 0
        assert "squeeze" in stderr.lower() or "C-049" in stderr

    def test_R006_window_size_wrong_default(self):
        """R-006: window_size_s default=4 应触发警告"""
        code, stderr = run_hook(RULE_ENGINE, "/tmp/test.py",
            'parser.add_argument("--window_size_s", default=4)')
        assert code == 0
        assert "C-037" in stderr or "C-057" in stderr or "window" in stderr.lower()

    def test_R007_hardcoded_output_dir(self):
        """R-007: 硬编码 output_dir 应触发警告"""
        code, stderr = run_hook(RULE_ENGINE,
            os.path.join(PROJECT_ROOT, "gcp", "test.yaml"),
            'output_dir: gs://omega-pure-data/phase12/output')
        assert code == 0
        assert "C-020" in stderr or "C-044" in stderr or "output" in stderr.lower()

    def test_R013_bp_double_convert(self):
        """R-013: * 10000 BP 转换应触发警告 (只对 core/loss/train 文件)"""
        code, stderr = run_hook(RULE_ENGINE,
            os.path.join(PROJECT_ROOT, "omega_epiplexity_plus_core.py"),
            'loss = target * 10000')
        assert code == 0
        assert "C-059" in stderr or "BP" in stderr


# ================================================================
# 免检文件
# ================================================================

class TestRuleEngineExemptions:
    """免检文件: exit 0, 无输出"""

    def test_markdown_exempt(self):
        """Markdown 文件应完全免检"""
        code, stderr = run_hook(RULE_ENGINE, "/tmp/test.md",
            'torch.device("cpu") BatchNorm')
        assert code == 0
        assert stderr.strip() == "", f"Markdown should be silent, got: {stderr[:100]}"

    def test_incidents_exempt(self):
        """incidents/ 文件应完全免检"""
        code, stderr = run_hook(RULE_ENGINE,
            os.path.join(PROJECT_ROOT, "incidents", "C-039", "trace.md"),
            'torch.device("cpu")')
        assert code == 0
        assert stderr.strip() == ""

    def test_rules_exempt(self):
        """rules/ 文件应完全免检"""
        code, stderr = run_hook(RULE_ENGINE,
            os.path.join(PROJECT_ROOT, "rules", "active", "test.yaml"),
            'torch.device("cpu")')
        assert code == 0
        assert stderr.strip() == ""


# ================================================================
# Compound Rules
# ================================================================

class TestCompoundRules:
    """compound 规则需要多条件同时满足"""

    def test_R001_large_pd_ssd_blocks(self):
        """R-001: 大容量 pd-ssd 无 Local SSD 应拦截"""
        code, stderr = run_hook(RULE_ENGINE,
            os.path.join(PROJECT_ROOT, "gcp", "test.yaml"),
            'bootDiskType: pd-ssd\nbootDiskSizeGb: 1300')
        assert code == 2, f"R-001 should block, got exit {code}"

    def test_R001_small_pd_ssd_passes(self):
        """R-001: 小容量 pd-ssd 应放行"""
        code, stderr = run_hook(RULE_ENGINE,
            os.path.join(PROJECT_ROOT, "gcp", "test.yaml"),
            'bootDiskType: pd-ssd\nbootDiskSizeGb: 100')
        assert code == 0

    def test_R005_bash_c_without_params_blocks(self):
        """R-005: gcp/ bash -c 无 $@ 应拦截"""
        code, stderr = run_hook(RULE_ENGINE,
            os.path.join(PROJECT_ROOT, "gcp", "test.sh"),
            'bash -c "python train.py"')
        assert code == 2

    def test_R005_bash_c_with_params_passes(self):
        """R-005: bash -c 有 $@ 应放行"""
        code, stderr = run_hook(RULE_ENGINE,
            os.path.join(PROJECT_ROOT, "gcp", "test.sh"),
            'bash -c "python train.py" "$@" _')
        assert code == 0


# ================================================================
# 干净代码
# ================================================================

class TestRuleEngineClean:
    """干净代码: 无触发"""

    def test_normal_python(self):
        code, stderr = run_hook(RULE_ENGINE, "/tmp/test.py",
            'import torch\nx = torch.randn(3, 4)\nprint(x.shape)')
        assert code == 0
        assert "BLOCKED" not in stderr

    def test_normal_yaml(self):
        code, stderr = run_hook(RULE_ENGINE,
            os.path.join(PROJECT_ROOT, "gcp", "test.yaml"),
            'machineType: g2-standard-8\nbootDiskSizeGb: 100')
        assert code == 0
        assert "BLOCKED" not in stderr


# ================================================================
# Legacy Lesson Enforcer (backward compat)
# ================================================================

class TestLessonEnforcerLegacy:
    """旧 lesson-enforcer.sh 仍然工作"""

    def test_device_hardcode(self):
        code, stderr = run_hook(LESSON_ENFORCER, "/tmp/test.py",
            'torch.device("cpu")')
        assert code == 2
        assert "C-039" in stderr

    def test_incidents_exempt(self):
        code, stderr = run_hook(LESSON_ENFORCER,
            os.path.join(PROJECT_ROOT, "incidents", "test.yaml"),
            'x = 0')
        assert code == 0

    def test_rules_exempt(self):
        code, stderr = run_hook(LESSON_ENFORCER,
            os.path.join(PROJECT_ROOT, "rules", "test.yaml"),
            'x = 0')
        assert code == 0


# ================================================================
# Performance
# ================================================================

class TestPerformance:
    """规则引擎不能太慢"""

    def test_engine_under_5_seconds(self):
        start = time.time()
        run_hook(RULE_ENGINE, "/tmp/test.py", 'x = 42')
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Rule engine took {elapsed:.1f}s (max 5s)"

    def test_engine_violations_under_5_seconds(self):
        start = time.time()
        run_hook(RULE_ENGINE, "/tmp/test.py", 'torch.device("cpu")')
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Engine took {elapsed:.1f}s with violations (max 5s)"


# ================================================================
# Runner
# ================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
