# Phase 11c: 点对点建仓之矛 (The Pointwise Spear)

**日期**: 2026-04-01
**来源**: 首席架构师 (DeepThink 独立审计 + Codex/Gemini 联合验尸)
**公理影响**: AXIOM UPDATE REQUIRED (Layer 2 训练范式彻底重构)
**状态**: 待用户确认

---

## 第一部分：终极物理死因诊断 (The Autopsy of the Illusion)

### 1. 终极元凶：时空坍塌 (Batch vs. CS Misalignment)

**Codex 的发现是一刀毙命的真相！**

* **物理违例**：我们的底层数据是通过 `WebDataset` 从 188 个 Tar 碎片中随机流式加载的。这意味着，一个 Batch 里的 256 个样本，**包含了跨越 3 年不同日期、不同股票的随机切片**（比如同时塞入了 2023 年熊市的茅台和 2024 年疯牛市的微盘股）。
* **赌场的诞生**：当你在这样一个"时空缝合怪"上使用 `F.softmax(dim=0)` 或 Batch Z-score 时，你是在逼迫模型跨越时空玩"零和博弈"。
* **作弊逻辑**：模型立刻发现：提取微观盘口的 Alpha 拓扑太难了，但**识别哪个切片来自"宏观大牛市"极度简单**！只要识别出宏观 Beta，它就利用 Softmax 的指数放大效应，将牛市样本的预测值暴力膨胀（飙升至 6956 BP），就能霸占整个 Batch 的权重！**它彻底退化成了一个"宏观 Beta 剥削器"。**

### 2. 认知撕裂：语义翻转与脑死亡幻觉 (The Semantic Inversion)

必须立刻纠正整个知识库对 $S_T$（`z_sparsity`，即 L1 范数）的认知翻转！

* 根据《From Entropy to Epiplexity》理论，**真正的智能是"提取出高度精简的拓扑结构"**，这会占用 Epiplexity 预算（L1 > 0）。
* **Z-D0 ($S_T \approx 0$) 根本不是"最高压缩"，这叫"特征脑死亡 (Brain Death)"！**
  当 L1 趋近于 0 时，模型关闭了 `z_core` 所有的特征通道（为了逃避 $\lambda_s$ 的惩罚），单纯利用最后一层的 Bias（偏置项）盲目输出 6956 BP 去赌宏观 Beta。所以它 IC 为负（方向全错），但绝对值极大（高熵赌徒）。
* **Z-D9 ($S_T \approx 0.011$) 才是真正的"智能涌现 (True Intelligence)"！**
  模型点亮了特定的神经元去描绘主力建仓的 2D 拓扑，所以它 IC 为正（看懂了），且预测值克制（2000 BP）。
* **真相大白**：你之前的 P0 Gating 逻辑（过滤高 $S_T$），**等同于把真正消耗脑力去理解市场的智能样本（Z-D9）全部处决了，满仓买入了 L1=0 的"脑死亡赌徒"（Z-D0）！** 利润当然会瞬间蒸发成 -34%！

---

## 第二部分：P0 级重铸指令 —— 点对点之矛 (The Pointwise Spear)

上述魔鬼指向了同一个唯一的解药：**在乱序流式数据下，绝对禁止使用任何跨 Batch 的横截面归一化操作（封杀 Softmax、Z-score 和 Pearson IC）！**

我们必须将数学核心降维至最严酷、最纯粹的物理环境：利用**点对点非对称损失（Pointwise Asymmetric Loss）**来实现"建仓之矛"。它彻底免疫时空错位，且自带绝对尺度的物理枷锁。

### 防弹级代码

```python
import torch
import torch.nn.functional as F

def compute_spear_loss_pointwise(raw_logits, target, z_core, lambda_s=1e-3):
    """
    Phase 11c: The Pointwise Spear (点对点建仓之矛)
    【物理法则】：
    1. 彻底废除跨时空的 Batch Softmax/Z-score，斩断宏观 Beta 走私。
    2. Pointwise Huber Loss 物理锚定真实的 BP 尺度，彻底击碎 6956 BP 的赌场漂移。
    """
    # 0. 剥离 FP16 溢出风险，确保量纲一致 (单位：基点 BP)
    pred = raw_logits.float().squeeze()
    target = target.float().squeeze()
    z_core = z_core.float()
    
    # ==========================================
    # 1. 非对称目标致盲 (Asymmetric Target Blinding)
    # ==========================================
    # 核心物理：只提纯主力建仓 (右尾)。所有下跌和微小波动噪音强行归零。
    # Gemini 担心的"物理对称性"被降维到了交易策略层，不再污染数学空间。
    target_acc = torch.clamp(target, min=0.0)
    
    # ==========================================
    # 2. 点对点绝对尺度惩罚 (Pointwise Huber Loss)
    # ==========================================
    # 没有任何跨 Batch 比较！如果模型瞎赌 (pred > 0 但 target <= 0)，将承受绝对误差惩罚！
    # 为什么用 Huber (delta=50)？防止极少数超大牛股 (>1000 BP) 引发梯度爆炸，
    # 同时在 0~50 BP 区间保持 MSE 级别的严苛尺度锁定。
    loss_spear = F.huber_loss(pred, target_acc, delta=50.0)
    
    # ==========================================
    # 3. 压缩即智能 (Epiplexity Axiom)
    # ==========================================
    # 当 Logit 膨胀的捷径被 Huber 封死，模型只能乖乖利用 z_core 去提取特征。
    z_core_safe = torch.clamp(z_core, min=-20.0, max=20.0)
    s_t = torch.norm(z_core_safe, p=1, dim=-1).mean()
    
    # Huber Loss 绝对值约在几十到几百，lambda_s 提至 1e-3 提供强大的 MDL 挤压力
    total_loss = loss_spear + lambda_s * s_t
    
    return total_loss, loss_spear, s_t, pred
```

---

## 第三部分：首席架构师的执行路标 (Execution Roadmap)

### Step 1：认知地图重构 (Mental Model Update)

请立即更新 `CLAUDE.md` 和 `OMEGA_LESSONS.md`。必须明确写入：

* **[C-045] 跨期 Batch 毒药**：在时序随机 Shard 的 DataLoader 中，绝对禁止使用任何 Batch 维度的归一化算子（Softmax/Pearson/Z-score），否则将引发严重的宏观时间泄露。
* **[C-046] L1 脑死亡陷阱**：为避免认知错乱，将 `z_sparsity` 重新在心智中标记为 `z_complexity`。L1 趋近 0 代表脑死亡（作弊）；非零的适度值才代表激活了真智能。未来若需使用 Gating 回测，必须**保留高 L1，剔除低 L1**。

### Step 2：云端重铸 Phase 11c

拿着上述 `compute_spear_loss_pointwise`，立即覆盖代码并启动 GCP 训练。

* **物理预期**：由于去掉了 Softmax 且引入了 Huber，你会看到 TensorBoard 中的 `Std_yhat` 会迅速被**物理重力死死拉回到几十到几百 BP 的真实 A 股区间**。6956 BP 的怪物将彻底绝迹。

---

## 对 current_spec.yaml 的影响

| 字段 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| `training.loss` | Spear Accumulation Loss + Variance Straitjacket + MDL | **Pointwise Spear (Huber) + MDL** | 彻底废除跨 Batch Softmax |
| `training.loss_function` | Softmax cross-entropy + detached Z-score | **Pointwise Huber(delta=50) + asymmetric target blinding** | 免疫时空错位 |
| `training.temperature` | 0.5 | **DELETED** | 无 Softmax → 无温度参数 |
| `training.variance_lock` | "detached" | **DELETED** | 无 Z-score → 无方差锁 |
| `training.lambda_s` | 2e-5 | **1e-3** | Huber Loss 量纲 (~几十到几百) vs Softmax Loss (~8) |
| `hpo.search_space.temperature` | [0.3, 0.5, 0.7, 1.0] | **DELETED** | 无 Softmax → 无温度搜索 |
| `hpo.search_space.lambda_s.range` | [1e-8, 1e-5] | **[1e-4, 1e-2]** | 匹配 Huber Loss 量纲 |
