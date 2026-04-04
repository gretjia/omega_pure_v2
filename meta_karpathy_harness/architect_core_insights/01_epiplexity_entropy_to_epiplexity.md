# From Entropy to Epiplexity: Rethinking Information for Computationally Bounded Intelligence

> **原文**: https://arxiv.org/html/2601.03220v2
> **arXiv ID**: 2601.03220v2 | **Date**: January 6, 2026 (v1); March 16, 2026 (v2)
> **GitHub**: https://github.com/shikaiqiu/epiplexity
> **归档目的**: OMEGA "压缩即智能" 哲学的学术基石。Epiplexity 理论证明了在有限算力下计算可以"创造"新知识。
> **OMEGA 映射**: WHY 核心哲学 "压缩即智能: MDL = H_T + λ_s × S_T" 的理论来源
> **归档说明**: 以下为架构师完整转写的论文正文+附录，原文保留。

---

**Marc Finzi$^{*1}$, Shikai Qiu$^{*2}$, Yiding Jiang$^{*1}$, Pavel Izmailov$^2$, J. Zico Kolter$^1$, Andrew Gordon Wilson$^2$**
$^1$Carnegie Mellon University, $^2$New York University

## Abstract
Can we learn more from data than existed in the generating process itself? Can new and useful information be constructed from merely applying deterministic transformations to existing data? Can the learnable content in data be evaluated without considering a downstream task? On these questions, Shannon information and Kolmogorov complexity come up nearly empty-handed, in part because they assume observers with unlimited computational capacity and fail to target the useful information content.

In this work, we identify and exemplify three seeming paradoxes in information theory: (1) information cannot be increased by deterministic transformations; (2) information is independent of the order of data; (3) likelihood modeling is merely distribution matching. To shed light on the tension between these results and modern practice, and to quantify the value of data, we introduce epiplexity, a formalization of information capturing what computationally bounded observers can learn from data. Epiplexity captures the structural content in data while excluding time-bounded entropy, the random unpredictable content exemplified by pseudorandom number generators and chaotic dynamical systems. With these concepts, we demonstrate how information can be created with computation, how it depends on the ordering of the data, and how likelihood modeling can produce more complex programs than present in the data generating process itself. We also present practical procedures to estimate epiplexity which we show capture differences across data sources, track with downstream performance, and highlight dataset interventions that improve out-of-distribution generalization. In contrast to principles of model selection, epiplexity provides a theoretical foundation for data selection, guiding how to select, generate, or transform data for learning systems.

---

## 1 Introduction
As AI research progresses towards more general-purpose intelligent systems, cracks are beginning to show in mechanisms for grounding mathematical intuitions. Much of learning theory is built around controlling generalization error with respect to a given distribution, treating the training distribution as fixed and focusing optimization effort on the choice of model. Yet modern systems are expected to transfer across tasks, domains, and objectives that were not specified at training time, often after large-scale pretraining on diverse and heterogeneous data. In this regime, success or failure frequently hinges less on architectural choices than on what data the model was exposed to in the first place.

Pursuing broad generalization to out-of-distribution tasks forces a shift in perspective: instead of treating data as given and optimizing for in-distribution performance, we need to choose and curate data to facilitate generalization to unseen tasks. This shift makes the value of data itself a central question—how much usable, transferable information can a model acquire from training? In other words, instead of model selection, how do we perform data selection? On this question, existing theory offers little guidance and often naively contradicts empirical observations.

Consider synthetic data, crucial for further developing model capabilities when existing natural data are exhausted. Existing concepts in information theory like the data processing inequality appear to suggest that synthetic data adds no additional value. Questions about what information is transferred to a given model seem naturally within the purview of information theory, yet, quantifying this information with existing tools proves to be elusive. Even basic questions, such as the source of the information in the weights of an AlphaZero game-playing model, are surprisingly tricky to answer. AlphaZero takes in zero human data, learning merely from the deterministic rules of the game and the AlphaZero RL algorithm, both of which are simple to describe. Yet the resulting models achieve superhuman performance and are large in size. To assert that AlphaZero has learned little to no information in this process is clearly missing the mark, and yet both Shannon and algorithmic information theory appear to say so.

In this paper, we argue that the amount of structural information a computationally bounded observer can extract from a dataset is a fundamental concept that underlies many observed empirical phenomena. As we will show, existing notions from Shannon and algorithmic information theory are inadequate when forced to quantify this type of information. These frameworks often lend intuitive or mathematical support to beliefs that, in fact, obscure important aspects of empirical phenomena. To highlight the limitations of classical frameworks and motivate the role of computational constraints in quantifying information, we identify and demonstrate three apparent paradoxes: statements which can be justified mathematically by Shannon and algorithmic information theory, and yet are in tension with intuitions and empirical phenomena.

* **Paradox 1: Information cannot be increased by deterministic processes.** For both Shannon entropy and Kolmogorov complexity, deterministic transformations cannot meaningfully increase the information content of an object. And yet, we use pseudorandom number generators to produce randomness, synthetic data improves model capabilities, mathematicians can derive new knowledge by reasoning from axioms without external information, dynamical systems produce emergent phenomena, and self-play loops like AlphaZero learn sophisticated strategies from games.
* **Paradox 2: Information is independent of factorization order.** A property of both Shannon entropy and Kolmogorov complexity is that total information content is invariant to factorization: the information from observing first $X$ and then $Y$ is the same as observing $Y$ followed by $X$. On the other hand, LLMs learn better on English text ordered left-to-right than reverse ordered text, picking out an "arrow of time", and we have cryptography built on the existence of functions that are computationally hard to predict in one direction and easy in another.
* **Paradox 3: Likelihood modeling is merely distribution matching.** Maximizing the likelihood is often equated with matching the training data generating process: the true data-generating process is a perfect model of itself, and no model can achieve a higher expected likelihood. As a consequence, it is often assumed that a model trained on a dataset cannot extract more structure or learn useful features that were not used in generating the data. However, we show that a computationally-limited observer can in fact uncover much more structure than is in the data generating process.

The tension between these theoretical statements and empirical phenomena can be resolved by imposing computational constraints on the observer and separating the random content from the structural content. Drawing on ideas from cryptography, algorithmic information theory, and these unexplained empirical phenomena, we define a new information measure, **epiplexity** (epistemic complexity), which formally defines the amount of structural information that a computationally-bounded observer can extract from the data (Section 3, Definition 8). Briefly, epiplexity is the information in the model that minimizes the description length of data under computational constraints. A simple heuristic measurement is the area under the loss curve above the final loss, while a more rigorous approach uses the cumulative KL divergence between a teacher and student model (Section 4, Figure 2).

Our definitions capture the intuition that an object contains both random, inherently unpredictable information (entropy), and predictable structured information that enables observers to generalize by identifying patterns (epiplexity).

An essential property of our formulation is that information is observer dependent: the same object may appear random or structured depending on the computational resources of the observer.

Together, our results provide clarity on the motivating questions: the information content of data can be compared independently of a specific task, new information can be created by computation, and models can learn more information than their generating processes contain.

---

## 2 Background

### 2.1 What Does it Mean for An Object to Be Random?

**Definition 1** *(Prefix Kolmogorov complexity)* Fix a universal prefix-free Turing machine $\mathcal{U}$. The (prefix) Kolmogorov complexity of a finite binary string $x$ is $K(x) = \min\{|p| : \mathcal{U}(p) = x\}$.

**Definition 2** *(Martin-Löf random sequence)* An infinite sequence $x_{1:\infty} \in \{0, 1\}^{\mathbb{N}}$ is Martin-Löf random iff there exists a constant $c$ such that for all $n$, $K(x_{1:n}) \geq n - c$.

**Definition 3** *(Non-uniform CSPRNG)* A function $G$ stretching $k$ input bits into $n$ output bits is a CSPRNG iff for every non-uniform probabilistic polynomial time algorithm $D_{k}$:

$$\epsilon(k) = |\text{Pr}_{s \sim U_{k}}[D_{n}(G(s)) = 1] - \text{Pr}_{u \sim U_{n}}[D_{n}(u) = 1]| < \text{negl}(k).$$

**Definition 4** *(Non-uniform one-way function, OWF)* Let $f: \{0, 1\}^{n} \to \{0, 1\}^{m}$ be computable in time $\text{poly}(n)$. We say $f$ is one-way against non-uniform adversaries if for every non-uniform PPT algorithm $A_{n}$,

$$\text{Pr}_{x \sim U_{n}}[A_{n}(f(x)) \in f^{-1}(f(x))] < \text{negl}(n)$$

### 2.2 Random vs Structural Information

**Definition 5** *(Naive Sophistication)* Sophistication is defined as the smallest Kolmogorov complexity of a set $S$ such that $x$ is a random element from that set:

$$\text{nsoph}_{c}(x) = \min_{S} \{ K(S) : K(x|S) > \log|S| - c \}$$

### 2.3 The Minimum Description Length Principle

**Definition 6** *(Two-part MDL)* Let $x \in \{0, 1\}^{n \times d}$ be the data and $\mathcal{H}$ be a set of candidate models:

$$L(x) = \min_{H \in \mathcal{H}} L(H) - \log P(x|H)$$

---

## 3 Epiplexity: Structural Information Extractable by a Computationally Bounded Observer

**Definition 7** *(Time-bounded probabilistic model)* Let $T : \mathbb{N} \to \mathbb{N}$ be non-decreasing time-constructible function and let $\mathcal{U}$ be a fixed prefix-free universal Turing machine. A program $P$ is a $T$-time probabilistic model over $\{0, 1\}^{n}$ if it supports both sampling and probability evaluation in time $T(n)$.

**Definition 8** *(Epiplexity and Time-Bounded Entropy)* Consider a random variable $X$ on $\{0, 1\}^{n}$. Let

$$P^{*} = \arg\min_{P \in \mathcal{P}_{T}} \{ |P| + \mathbb{E}[\log(1/P(X))] \}$$

be the program that minimizes the time bounded MDL. We define the $T$-bounded epiplexity $S_{T}$ and entropy $H_{T}$ of the random variable $X$ as

$$S_{T}(X) := |P^{*}|, \quad \text{and} \quad H_{T}(X) := \mathbb{E}[\log(1/P^{*}(X))].$$

**Theorem 9** *For any $T \in \text{Poly}(n)$ and $G$ CSPRNG that stretches the input to $n = \text{poly}(k)$ bits:*

$$n - 2 - n\epsilon(k) < H_{T}(G(U_{k})) \leq n + c$$

*and the epiplexity is nearly constant:*

$$S_{T}(G(U_{k})) < c + n\epsilon(k).$$

**Theorem 10** *Assuming the existence of one-way functions, there exists a sequence of random variables $\{X_{n}\}$ such that $S_{\text{Poly}}(X_{n}) = \Omega(\log n)$.*

**Definition 11** *(Conditional epiplexity and time-bounded entropy)* For a pair of random variables $X$ and $Y$:

$$S_{T}(Y|X) := |P_{Y|X}^{*}|, \quad H_{T}(Y|X) := \mathbb{E}_{(X,Y)}[-\log P_{Y|X}^{*}(Y|X)].$$

---

## 4 Measuring Epiplexity and Time-Bounded Entropy

### 4.1 Approximating Model Description Length with Prequential Coding

$$|P_{\text{preq}}| \approx \sum_{i=0}^{M-1} (\log(1/P_{i}(Z_{i})) - \log(1/P_{M}(Z_{i}))).$$

### 4.2 Explicitly Coding the Model with Requential Coding

$$|P_{\text{req}}| = \sum_{i=0}^{M-1} \text{KL}(P_{i}^{t} || P_{i}^{s}) + \log(1 + \text{KL}(P_{i}^{t} || P_{i}^{s})) + 4 + O(1) \approx \sum_{i=0}^{M-1} \text{KL}(P_{i}^{t} || P_{i}^{s})$$

### 4.3 Comparison Between the Two Approaches and Practical Recommendations

While requential coding is the more rigorous approach, it is typically 2x to 10x slower than prequential coding. We recommend using prequential coding for crudely estimating epiplexity and ranking datasets, and requential coding for obtaining the most accurate estimates.

### 4.4 How Epiplexity and Time-Bounded Entropy Scale with Compute and Data

Under natural assumptions, epiplexity $S_{T}(X)$ typically grows with $T$ while time-bounded entropy $H_{T}(X)$ decreases.

---

## 5 Three Apparent Paradoxes of Information

### 5.1 Paradox 1: Information Cannot be Created by Deterministic Transformations

**Theorem 12** *Let $G$ be a CSPRNG. $H_{\text{Poly}}(G(U_{k})) > H_{\text{Poly}}(U_{k}) + n - n\epsilon(k) - k - O(1)$.*

ECA Rule 54 experiments: complex dynamics produce both random and structural information, reflected in training loss curves.

### 5.2 Paradox 2: Information Content is Independent of Factorization

**Theorem 13** *Let $f$ be a one-way permutation and let $X=U_{n}$, $Y=f(X)$. $H_{\text{Poly}}(X|Y) + H_{\text{Poly}}(Y) > H_{\text{Poly}}(Y|X) + H_{\text{Poly}}(X) + \omega(\log n)$.*

Chess experiments: reverse order (board-then-moves) yields higher epiplexity and better downstream performance.

### 5.3 Paradox 3: Likelihood Modeling is Merely Distribution Matching

#### 5.3.1 Induction
Models must learn induction strategies not present in the data generating process. Epiplexity grows with the number of hidden bits.

#### 5.3.2 Emergent Phenomena

**Definition 14** *(Epiplexity Emergent)* $(\Phi, X)$ displays emergent phenomena if two observers see equivalent structural complexity in the one step map, but asymptotically more structural complexity in the multistep map for the observer with fewer computational resources.

---

## 6 Epiplexity, Pre-Training, and OOD Generalization

### 6.1 Epiplexity Correlates with OOD Generalization in Chess
Reverse ordering yields higher epiplexity and significantly higher accuracy on centipawn evaluation task.

### 6.2 Measuring Structural Information in Natural Data
Language data has the highest epiplexity, while image data has the least. Over 99% of CIFAR-5M information is random.

### 6.3 Estimating Epiplexity from Scaling Laws

Asymptotic epiplexity: $S_{\infty}(X) = \frac{\beta}{1-\beta} D_{0}^{\beta} \mathcal{D}^{1-\beta}$

### 6.4 Pre-Training Data Selection and Curriculum for Language Models
ADO achieves higher epiplexity and higher downstream performance than standard data sampling.

---

## 7 Additional Related Work
Epiplexity builds on sophistication, effective complexity, logical depth, algorithmic statistics, V-entropy, and computational pseudoentropy. Key distinction: epiplexity accounts for computational constraints and separates structural from random information.

---

## 8 Discussion
This work reframes information as a property of data relative to a computationally-bounded observer, demonstrating that information can be decomposed into time-bounded entropy and epiplexity. It resolves tensions between information theory and empirical ML, including the usefulness of synthetic data, the dependence of learning on factorization, and the emergence of structure beyond the data-generating process.

---

## Appendix A. Proofs

**Lemma 15** *(Maximum expected description length)* $S_{T}(X) + H_{T}(X) \leq n + c_{1}$ for $T(n) \geq c_{2}n + c_{3}$.

**Lemma 16** *(Time-bounded entropy of uniform distribution)* $n \leq H_{T}(X) \leq n + c_{1}$.

### A.1 CSPRNGs have (nearly) maximal time-bounded Entropy and low epiplexity

**Theorem 17** $H_{T}(G(U_{k})) \geq n - 2 - n\epsilon(k)$.

*Proof uses distinguisher construction at each precision level $t$, uniform threshold bound, CSPRNG transfer, and layercake representation.*

### A.2 Deterministic transformation can increase time bounded entropy

**Theorem 18** $H_{\text{Poly}}(G(U_{k})) > H_{\text{Poly}}(U_{k}) + n - n\epsilon(k) - k - O(1)$.

### A.3 CSPRNGs have low epiplexity

**Theorem 19** $S_{T}(Y) \leq c + n\epsilon(k)$.

### A.4 Existence of High Epiplexity random variables

**Theorem 24** Under PRF existence, $S_{\text{Poly}}(X_{n}) = \Omega(\log n)$.

*Proof uses heavy set construction, distinguisher from model Q, union bound over short models, and MDL lower bound.*

### A.5 Information Content is not Independent of Factorization

**Theorem 25** *(OWP induces entropy asymmetry)* For OWP $f$, $X=U_n$, $Y=f(X)$:
$H_{\text{poly}}(X|Y) + H_{\text{poly}}(Y) > H_{\text{poly}}(Y|X) + H_{\text{poly}}(X) + c \log n$.

**Corollary 26** No polynomial time probability model fitting a OWP's forward direction can satisfy Bayes theorem.

### A.6 Problems with time-bounded sophistication

**Lemma 29** Naive time-bounded sophistication is $O(1)$ for every string — the definition collapses.

---

## Appendix B. Measuring Epiplexity

### B.1 Further details on estimating epiplexity
Details on evaluating code lengths, time bounds, finding hyperparameters for compute-optimal two-part code, estimating Pareto frontier, and sources of errors.

### B.2 Prequential Coding Approximates Requential Coding with a Static Teacher

### B.3 A Solvable Model Using Scaling Laws

Scaling law: $\mathcal{L}(N,D) = E + (N/N_{0})^{-\alpha} + (D/D_{0})^{-\beta}$

Large-compute asymptotic epiplexity: $S_{\infty}(X) = \frac{\beta}{1-\beta} D_{0}^{\beta} \mathcal{D}^{1-\beta}$

Small-compute: $S_{T}(X) \propto T^{\frac{\alpha(1-\beta)}{\beta+1}}$

### B.4 How Epiplexity and Time-Bounded Entropy Scale with Compute and Dataset Size

**Theorem 30** *(Monotone growth of compute-optimal N and D)* Under complementarity, diminishing returns in model size and data, both $N^*(T)$ and $D^*(T)$ are strictly increasing in $T$.

$D^*(T) \to \mathcal{D}$ as $T \to \infty$ for prequential coding.

---

## Appendix C. Experiment Details

- **C.1 ECA**: State size 64, 48 evolution steps, width ∈ {16-512}, depth ∈ {1-9}
- **C.2 Easy induction**: Sequence length 512, 3 layers, width 128
- **C.3 Hard induction**: Rule 30 iterated 4 steps, state size 32
- **C.4 Chess**: 1M to 160M parameters, character-level tokenization, 5B tokens
- **C.5 OpenWebText**: Character-level tokenization, 96 common symbols
- **C.6 CIFAR-5M**: Greyscale flattened to 1024 sequence, vocabulary {0,...,255}
- **C.8 ECA Emergence**: Rule 54, 64 evolution steps, looped vs non-looped models
- **C.9 Scaling Laws**: Chinchilla for language, Henighan et al. for images/video

---

## Appendix D. RASP-L for Elementary Cellular Automata
RASP-L code demonstrating ECA evolution rule implementation within autoregressive transformer model.

## Appendix E. Cellular Automata and Game of Life
Definitions of ECA (256 rules, Rule 54 Turing-complete) and Conway's Game of Life.

## Appendix F. Emergence
Lorenz system chaotic dynamics, chess strategy (AlphaZero vs minimax).

## Appendix G. Induction is not specific to autoregressive models
Key requirement is MLE, not autoregressive factorization. VAEs explicitly perform induction.

## Appendix H. MDL Review
Two-part code, one-part code, and regret as generalization of epiplexity.

---

*(References omitted per transcription norms — full bibliography of 80+ entries available in original paper)*
