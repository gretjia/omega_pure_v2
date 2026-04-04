# Strict Universality of the Square-Root Law in Price Impact — 完整归档

> **原文**: https://arxiv.org/html/2411.13965v3
> **arXiv ID**: 2411.13965v3 | **Date**: December 15, 2025
> **归档目的**: OMEGA 物理公理 δ=0.5 的实证基石。本文以东京证券交易所全量数据证明 SRL 的严格普适性。
> **OMEGA 映射**: 物理公理 #7 (δ=0.5 严禁修改) 的终极文献支撑

---

## Authors

Yuki Sato, Kiyoshi Kanazawa
Department of Physics, Graduate School of Science, Kyoto University, Kyoto 606-8502, Japan

---

## Abstract

The paper examines universal power laws in econophysics, specifically investigating whether the nonlinear price impact follows the square-root law (SRL) with exponent δ ≈ 1/2 universally across all stocks. The authors resolve a long-standing debate by conducting a comprehensive survey of all trading accounts for all liquid stocks on the Tokyo Stock Exchange (TSE) over eight years. Their dataset enables tracking trading behavior of individual accounts with unprecedented precision.

Key findings:
- Exponent δ equals 1/2 within statistical errors at both individual stock and trader levels
- Rejection of two prominent nonuniversality-supporting models: GGPS and FGLW
- Exceptionally high-precision evidence supporting universality in social science
- Practical implications for evaluating price impact of large institutional investors

---

## 1. Introduction

### Core Concept: The Square-Root Law

Average price impact I(Q) follows power-law scaling:

$$I(Q) \propto Q^{\delta}, \quad \delta \approx 1/2$$

**Definition of Price Impact**: For a trader buying or selling Q units via market orders, price impact I(Q) represents the average mid-price change Δp between metaorder beginning and end.

### Central Debate

- **Universality hypothesis**: δ = 1/2 exactly for all stocks worldwide
- **Nonuniversality hypothesis**: δ depends on microscopic details, varies by system

### Challenge

Previous resolution required high-precision measurements (error ~0.1) across hundreds of stocks, impossible without large microscopic datasets tracking all individual trading accounts. Most previous datasets were proprietary, provided by hedge funds — neither comprehensive nor randomly sampled, introducing sampling bias.

---

## 2. Data Description

**Dataset Source**: Japan Exchange (JPX) Group, Inc., platform manager of TSE

**Coverage**: Complete order lifecycle records for **all TSE stocks** over nearly **eight years** (January 4, 2012 - November 2, 2019)

**Unique Feature**: Includes virtual server IDs, enabling tracking of individual trading accounts

**Data Division**:
- Dataset 1: January 4, 2012 - September 18, 2015
- Dataset 2: September 24, 2015 - November 2, 2019

**Liquid Stock Definition**: Total metaorders exceeding 10^5

**Resulting Data Points**:
- Dataset 1: 942 liquid stocks
- Dataset 2: 1,357 liquid stocks
- **Total: 2,299 datapoints**

---

## 3. Stock-Level Analysis Results

### Measurement Process

1. Extract metaorders (assumed when successive orders have identical sign)
2. Define dimensionless volume: Q̃ = Q/V_D
3. Define dimensionless impact: Ĩ = I/σ_D (where V_D = daily transaction volume, σ_D = daily volatility)
4. Fit power law: Ĩ(Q̃) = c·Q̃^δ

### Primary Result

$$\langle \delta \rangle = 0.489 \pm 0.0015$$
$$\sigma_{\delta} = 0.071$$

**Key Observation**: Histogram exhibits **sharp peak around 1/2** across 2,000+ data points

### Aggregate Scaling

After nondimensionalization and rescaling by prefactor c, **all stocks collapse onto single master curve** consistent with square-root law.

**Prefactor Statistics**: ⟨c⟩ = 0.842

### Robustness Check

Using ordinary least squares directly on raw datapoints yields ⟨δ_OLS⟩ = 0.474 ± 0.0012, nearly identical.

**Additional Finding**: Consistent observation of crossover from linear to square-root scaling.

---

## 4. Errorbar Estimation Methodology

### Challenge
Dataset exhibits time-series structure with serial correlation, violating independence assumption.

### Solution: Monte Carlo Simulation
1. Randomly shuffle metaorder signs while preserving submission timestamps from real TSE data
2. Assume price impacts exactly follow SRL with δ = 1/2, adding random contributions
3. Generate 100 Monte Carlo iterations
4. Measure δ for all stocks in each iteration
5. Calculate mean and standard deviation

### Result

$$\langle\langle \bar{\delta} \rangle\rangle = 0.489 \pm 0.0013$$
$$\langle\langle \sigma_{\bar{\delta}} \rangle\rangle = 0.063$$

**Validation**: Cross-sectional average from TSE data equals Monte Carlo average within errorbar; cross-sectional dispersion matches — confirming finite sample size accounts for observed variation, **supporting universality hypothesis**.

---

## 5. Trader-Level Analysis

**Active Traders**: 1,293 (415 from Dataset 1, 878 from Dataset 2)

### Secondary Result

$$\langle \delta^{(i)} \rangle = 0.493 \pm 0.0050$$
$$\sigma_{\delta^{(i)}} = 0.177$$

**Key Finding**: Sharp peak around 1/2 persists despite diversity in individual trading strategies.

**Prefactor Statistics**: ⟨c^(i)⟩ = 1.501

---

## 6. Rejection of Nonuniversality Models

### GGPS Model (Gabaix et al.)
Prediction: δ = β - 1 (where β characterizes power-law exponent of metaorder volume distribution)

### FGLW Model (Farmer et al.)
Prediction: δ = α - 1 (where α characterizes power-law exponent of child-order count distribution)

### Empirical Test
Scatterplots between β and δ, and between α and δ.

### Result
**"No correlation was found and, thus, both models were rejected"**

Single-market survey suffices to falsify universal validity of prominent nonuniversal models.

---

## Key Equations

### Power-Law Scaling (nondimensionalized)

$$\tilde{\mathcal{I}}(\tilde{\mathcal{Q}}) \approx c_0 \tilde{\mathcal{Q}}^{\delta}$$

where:
- $\tilde{\mathcal{Q}} := Q/V_D$ (dimensionless volume)
- $\tilde{\mathcal{I}} := I/\sigma_D$ (dimensionless impact)

### Linear Response Regime

$$I(Q) := \langle \epsilon \Delta p | Q \rangle \approx \lambda Q$$

where ε = +1 (buy), -1 (sell)

---

## Figures Summary

| Figure | Content |
|--------|---------|
| Fig. 1 | Schematic: practitioners splitting metaorder Q into child orders |
| Fig. 2 | (a) Impact profiles for Toyota/NTT/SoftBank/Takeda (b) Aggregate scaling (c) δ histogram peak at 0.5 (d) c histogram |
| Fig. 3 | Errorbar estimation via Monte Carlo |
| Fig. 4 | (a) Trader-level aggregate scaling (b) δ^(i) histogram (c) c^(i) histogram |
| Fig. 5 | (a) β vs δ scatter — no correlation (b) α vs δ scatter — no correlation |

---

## OMEGA 项目核心映射

| 论文发现 | OMEGA 公理/实现 | 位置 |
|---------|----------------|------|
| **δ = 0.489 ± 0.0015** ≈ 0.5 | 物理公理 #7: δ=0.5 严禁修改 | `CLAUDE.md` Rule 7 |
| **⟨c⟩ = 0.842** | c_default=0.842 作为回退值 | `CLAUDE.md` Rule 10 |
| SRL 对所有股票普适 | 单一 δ 值适用全 A 股 | `omega_epiplexity_plus_core.py` |
| 需要 per-stock 标定 c | Layer 2 per-stock 动态标定 | `architect/current_spec.yaml` |
| Metaorder 提取方法 | SRL 反演提取元订单流 | Core pipeline |
| 线性→平方根交叉 | vol_threshold 冷启动检测 | ETL pipeline |

---

## Data & Code

- **Data**: TSE dataset provided by JPX Group under NDA
- **Code**: https://gitlab.com/Yuki-Sato_JPN/CodeDisclosure-2024-SRL
- **Funding**: JSPS KAKENHI Grants (multiple)

---

## Key References

- [3] Bouchaud et al., *Trades, quotes and prices* (Cambridge, 2018)
- [24] Gabaix et al., Nature 423, 267 (2003) — GGPS model
- [26] Farmer et al., Quant. Finance 13, 1743 (2013) — FGLW model
- [34] Hamilton, *Time Series Analysis* (Princeton, 1994)
