---
name: axiom-audit
description: 运行omega_axioms.py公理断言，检查物理常数、张量形状、数值稳定性
user_invocable: true
---

# Axiom Audit

运行 OMEGA 公理断言模块，验证物理常数和架构规范的完整性。

## 步骤

1. **运行公理自检**:
   ```bash
   cd /home/zephryj/projects/omega_pure_v2 && python omega_axioms.py --verbose
   ```

2. **检查 architect/current_spec.yaml 存在性和格式**:
   - 文件是否存在
   - YAML 格式是否正确（能被 omega_axioms.py 解析）
   - 必要字段是否齐全（tensor, physics, etl）

3. **检查代码中的物理常数**:
   - `omega_epiplexity_plus_core.py` 中 `c_constant = 0.842`
   - `omega_epiplexity_plus_core.py` 中 `power_constant = 2.0`
   - SRL inverter 在 `torch.no_grad()` 下运行

4. **交叉验证 spec 与代码**:
   - spec 中的 physics.delta 与 Layer 1 硬编码一致
   - spec 中的 physics.c_tse 与 Layer 1 硬编码一致
   - 空间轴维度 >= 2（拓扑不可拍扁）

5. **报告结果**:

## 输出格式

```
==================================================
 OMEGA AXIOM AUDIT
==================================================

[Layer 1] Eternal Physics Axioms:
  [OK] δ = 0.5 (Square Root Law exponent)
  [OK] c = 0.842 (TSE empirical constant)
  [OK] POWER_INVERSE = 2.0 (1/δ)

[Layer 2] Architecture Axioms (from spec):
  [OK] spec.physics.delta consistent with Layer 1
  [OK] spec.physics.c_tse consistent with Layer 1
  [OK] tensor.time_axis = 160
  [OK] tensor.spatial_axis = 10 (topology preserved)
  [OK] tensor.feature_axis = 7
  [OK] etl.vol_threshold = 50000
  [OK] etl.window_size = 160
  [OK] etl.stride = 20 (< window_size, overlap guaranteed)

[Code] Physical Constants in Source:
  [OK] AxiomaticSRLInverter.c_constant = 0.842
  [OK] AxiomaticSRLInverter.power_constant = 2.0
  [OK] SRL inverter runs under torch.no_grad()

==================================================
 AUDIT PASSED — All axioms verified
==================================================
```

## 失败处理

- 如果任何检查失败，显示具体违规内容
- **Layer 1 违规是 FATAL** — 意味着物理常数被篡改，必须立即停止并通知用户
- **Layer 2 违规可能是配置更新** — 检查是否有待执行的架构师指令
