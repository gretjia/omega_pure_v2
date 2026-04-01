# Phase 11b: 重铸的建仓之矛 (The Reforged Spear)

**日期**: 2026-04-01
**来源**: 首席架构师 (对话直传)
**公理影响**: AXIOM UPDATE REQUIRED (Layer 2 — temperature, lambda_s, Z-score 机制)
**关系**: 修复 Phase 11a NaN 崩溃 (S_T 指数爆炸)

---

## 死因诊断: Z-Score 的"勾股漂移 (Pythagorean Drift)"

Phase 11a 在 Epoch 5 Step 1500 脑死亡 (S_T: 4.3 → 203K → Inf → NaN)。

### 物理机制

1. **仿射黑洞 (Scale-Invariant Null-Space)**:
   Z-score `locked = (raw - mean) / std` 是绝对尺度不变的。
   根据欧拉齐次函数定理，尺度不变函数的梯度与输入向量绝对正交。
   → Softmax 梯度在 raw_logits 的尺度方向上永远为 0。

2. **勾股漂移**:
   梯度与权重正交 → W_new² = W_old² + Gradient² → 权重 L2 范数单调膨胀。
   Adam 优化器驱动下不可逆。

3. **温度催化 (T=0.1)**:
   梯度放大 10x → 漂移速度放大 100x → 多层乘法共振。

4. **量纲错配**:
   λ_s=1e-7 是 IC Loss (≈0.05) 时代的重力。
   Softmax Loss (≈10.0) 放大 200x → 惩罚占比 0.14% → 形同虚设。

### Codex 独立验证
- 根因确认: "mostly a scale-runaway problem, not an L1 problem"
- 梯度公式: ∂L/∂r ≈ (1/Tσ)(I - 11ᵀ/B - zzᵀ/(B-1))(p-q)
- λ_s 数值平衡需 ~7e-5, 梯度平衡需更大

---

## 修复方案: Detached Straitjacket + 动态引力

### 架构师对 Codex 建议的裁决
- ❌ Rank 1 (z_core LayerNorm): 驳回 — 会摧毁 L1 稀疏本质
- ❌ Rank 3 (clamp z_core): 驳回 — 暴力工程补丁，产生死区
- ✅ Rank 2 (T=0.5): 采纳
- ✅ Extra (FP32): 采纳
- 🌟 首席架构师方案: Detached Straitjacket

### 最终代码蓝图

```python
def compute_spear_loss(raw_logits, target, z_core, temperature=0.5, lambda_s=2e-5):
    # 0. FP32 Safe Room
    raw_logits = raw_logits.float()
    target = target.float()
    z_core = z_core.float()
    eps = 1e-8

    # 1. 目标遮罩
    target_acc = torch.clamp(target, min=0.0)
    target_sum = target_acc.sum()

    # 2. Detached Straitjacket
    logit_mean = raw_logits.mean(dim=0, keepdim=True)
    logit_std = raw_logits.std(dim=0, keepdim=True)
    # clamp(min=1.0): 防止 std→0 时 1/0 爆炸
    # .detach(): 斩断勾股漂移！梯度不再尺度不变，产生向内压缩引力
    safe_std = torch.clamp(logit_std, min=1.0).detach()
    locked_logits = (raw_logits - logit_mean) / safe_std

    # 3. Spear Loss
    if target_sum <= eps:
        loss_spear = torch.tensor(0.0, device=raw_logits.device, requires_grad=True)
    else:
        target_prob = target_acc / target_sum
        # log_softmax 替代 log(softmax+eps) — 数值稳定性
        log_pred_prob = F.log_softmax(locked_logits / temperature, dim=0)
        loss_spear = -torch.sum(target_prob * log_pred_prob)

    # 4. MDL with safety clamp
    z_core_safe = torch.clamp(z_core, min=-20.0, max=20.0)
    s_t = torch.norm(z_core_safe, p=1, dim=-1).mean()

    # lambda_s=2e-5: 匹配 Softmax Loss (~8.0) vs IC Loss (~0.05) 的 160x 量纲提升
    total_loss = loss_spear + lambda_s * s_t
    return total_loss.to(raw_logits.dtype), loss_spear.to(raw_logits.dtype), s_t, locked_logits
```

### 关键参数变更
| 参数 | Phase 11a | Phase 11b | 理由 |
|------|----------|----------|------|
| temperature | 0.1 | **0.5** | 梯度放大从 10x 降到 2x |
| lambda_s | 1e-7 | **2e-5** | 匹配 Softmax/IC 160x 量纲差 |
| Z-score std | 全梯度 | **detach + clamp(min=1.0)** | 斩断勾股漂移 |
| 精度 | AMP fp16 | **FP32 safe room** | 防 e^11 溢出 |
| log 计算 | log(softmax+eps) | **F.log_softmax** | 数值稳定 |
| z_core | 无约束 | **clamp [-20,20]** | 紧急防爆墙 |
| warmup | 保留 | **架构师未提及 → 保留** | |

### 返回签名变更
(total, pf_ret, s_t) → (total, loss_spear, s_t, locked_logits)
需要更新所有调用方。

---

## 执行指令
1. 立即覆盖 compute_spear_loss
2. 重启 GCP 训练 (Phase 11b)
3. 验收: S_T 稳定在几十到几百，不再飞向宇宙
