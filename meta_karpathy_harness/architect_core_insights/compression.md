***

# [cite_start]COMPRESSION IS ALL YOU NEED: MODELING MATHEMATICS [cite: 2]
[cite_start]**VITALY AKSENOV, EVE BODNIA, MICHAEL H. FREEDMAN, AND MICHAEL MULLIGAN** [cite: 3]

[cite_start]**ABSTRACT.** Human mathematics (HM), the mathematics humans discover and value, is a vanishingly small subset of formal mathematics (FM), the totality of all valid deductions. [cite: 4] [cite_start]We argue that HM is distinguished by its compressibility through hierarchically nested definitions, lemmas, and theorems. [cite: 5] We model this with monoids. [cite_start]A mathematical deduction is a string of primitive symbols; [cite: 6] [cite_start]a definition or theorem is a named substring or macro whose use compresses the string. [cite: 7] [cite_start]In the free abelian monoid $A_{n}$, a logarithmically sparse macro set achieves exponential expansion of expressivity. [cite: 8] [cite_start]In the free non-abelian monoid $F_{n}$, even a polynomially-dense macro set only yields linear expansion; superlinear expansion requires near-maximal density. [cite: 9] [cite_start]We test these models against MathLib, a large Lean 4 library of mathematics that we take as a proxy for HM. [cite: 10] [cite_start]Each element has a depth (layers of definitional nesting), a wrapped length (tokens in its definition), and an unwrapped length (primitive symbols after fully expanding all references). [cite: 11] [cite_start]We find unwrapped length grows exponentially with both depth and wrapped length; wrapped length is approximately constant across all depths. [cite: 12] [cite_start]These results are consistent with $A_{n}$ and inconsistent with $F_{n}$ supporting the thesis that HM occupies a polynomially-growing subset of the exponentially growing space FM. [cite: 13] [cite_start]We discuss how compression, measured on the MathLib dependency graph, and a PageRank-style analysis of that graph can quantify mathematical interest and help direct automated reasoning toward the compressible regions where human mathematics lives. [cite: 14]

## [cite_start]1. INTRODUCTION [cite: 15]

[cite_start]In this paper, we argue that math is soft and squishy-that this is its defining characteristic. [cite: 16] [cite_start]By "math" we do not mean the totality of all possible formal deductions, formal mathematics (FM), but rather human mathematics (HM), the type of arguments humans find and those we will appreciate when our AI agents find them for us. [cite: 17] [cite_start]By "soft and squishy," we mean compressible through the use of hierarchically nested concepts: definitions, lemmas, and theorems. [cite: 18] [cite_start]The finding that math is about compression is not new. [cite: 19] [cite_start]We were scooped 3,000 years ago by the invention of place notation. [cite: 20] Consider $\mathbb{N}$, the natural numbers, with generating set $\{1\}$. [cite_start]Place notation introduces additional symbols, or macros: "10" for ten ones, "100" for ten tens, and so on. [cite: 21] With logarithmically many macros, expressivity expands exponentially. [cite_start]This (exponential) expansion of expressivity is the flip side of notational compression. [cite: 32] [cite_start]Creating and exploiting definitions expands what we can reach by compressing expressions written in a primitive, definition-poor language. [cite: 33] (Our theorems below will be stated in terms of expansion; our informal discussions often use compression.) [cite_start][cite: 34]

[cite_start]However mathematics is formalized, we know from Gödel and other sources that there will be true statements without proofs (such as consistency of the system). [cite: 22] [cite_start]It is possible that extremely simple $\Pi_{1}^{0}$ statements of Peano arithmetic, such as the Goldbach conjecture (GC: "Every even number $>2$ is the sum of two primes"), could be both true and without any proof. [cite: 23] [cite_start]Since our discussion is anchored to the concept of proof, we would not count GC as part of HM or even FM if that is the case, despite the fact that it is of interest to humans. [cite: 24] [cite_start]A more subtle question: suppose GC has a proof but the shortest one is $10^{100}$ lines long is it part of HM? [cite: 25] [cite_start]Fortunately we do not have to adjudicate this; our results are not sharp enough to require us to identify an exact frontier to HM. [cite: 26] [cite_start]Moreover, HM might more precisely be considered a measure on FM that fades out rather than abruptly terminating at the edge of a subset; [cite: 27] [cite_start]see [BDF]. [cite: 28]

[cite_start]Formal mathematics can be viewed as a directed hypergraph (DH) emerging from axioms and syntactical rules [BDF]. [cite: 35] [cite_start]The DH records the full deduction space: every possible proof step, with each hyperedge specifying which premises are combined (Fig. 1, left). [cite: 36] [cite_start]A proof is a sub-hypergraph of the DH; flattened into a linear sequence, it becomes a string of primitive symbols. [cite: 37] [cite_start]We study finitely-generated monoids as models for such strings: word length measures size, and naming a substring for reuse-a macro-compresses it. [cite: 38] (Monoids with relations can simulate Turing machines [Pos47], so, despite its simplicity, this basic framework is computationally universal.) [cite_start]The simplest case is $A_{1}=\mathbb{N}$, the natural numbers. [cite: 39] 

[cite_start]To study compression more generally, we consider the free abelian monoid $A_{n}$ and the free (non-abelian) monoid $F_{n}$ (with $n$ denoting the number of generators). [cite: 40] [cite_start]In $A_{n}$, the generators commute, so only the multiplicities matter. [cite: 41] [cite_start]In $F_{n}$, the order of generators is important, and there are no relations; [cite: 42] [cite_start]since formal proofs are strings of symbols where order matters, $F_{n}$ might be presumed to model formal deduction. [cite: 43] [cite_start]We will argue, contrary this expectation, that the compression exhibited by human mathematics is characteristic of $A_{n}$, not $F_{n}$. [cite: 44] 

Our main theoretical results quantify the expansion that macros achieve in $A_{n}$ and $F_{n}$. [cite_start]In $A_{n}$ logarithmically many macros achieve exponential expansion (Theorem 1), and macros of polynomial density (growth exponent $1/k$) can yield infinite expansion every element expressible with bounded length-via Waring's theorem (Theorem 3). [cite: 45] [cite_start]In $F_{n}$ even polynomially growing macros (polynomial as a function of radius, i.e., polylogarithmic as a function of volume) yield only linear expansion (Theorem 4). [cite: 46] [cite_start]Superlinear expansion in $F_{n}$ requires an exponential number of macros (Theorem 5), in contrast with the logarithmically sparse macro set that suffices for exponential expansion in $A_{n}$. [cite: 47] This difference reflects underlying growth rates: balls grow polynomially in $A_{n}$ but exponentially in $F_{n}$. [cite_start]Our study of macro sets in $A_{n}$ extends straightforwardly to the much larger class of free nilpotent monoids; [cite: 48] [cite_start]they have nearly identical expansion properties to $A_{n}$ and can equally serve as models for HM according to the analysis presented here (see Sections 4.3 for details). [cite: 49] 

[cite_start]We test these facts against MathLib [Mat20], a large repository of mathematics written in Lean 4 [dMU21] that contains hundreds of thousands of definitions, lemmas, and theorems. [cite: 50] We use MathLib as a proxy for HM. [cite_start]MathLib can be viewed as a DAG extracted from the full deduction hypergraph (Fig. 1). [cite: 51] [cite_start]Each MathLib element is a named subgraph of this DAG, rooted at the element itself and extending down to primitives. [cite: 52] [cite_start]Flattening this subgraph by recursively expanding all references yields a string of primitives. [cite: 53] [cite_start]The wrapped length counts the tokens in an element's defining expression; the unwrapped length counts the primitives in the flattened string. [cite: 73] [cite_start]We find the longest element, when fully unwrapped, reaches approximately $10^{104}$ primitive terms-Googol, the number, not the company. [cite: 74] 

Our primary observations about MathLib are as follows. [cite_start]First, unwrapped length grows exponentially with depth (the longest path to primitives in the dependency graph). [cite: 75] Second, wrapped length is approximately constant across all depths. [cite_start]Third, unwrapped length grows exponentially with wrapped length. [cite: 76] [cite_start]The MathLib data is consistent with the $A_{n}$ logarithmic-density regime and inconsistent with the $F_{n}$ alternatives we study. [cite: 77, 78] 

[cite_start]Our central inference is that HM is a thin subset of polynomial growth within the exponentially growing space FM. [cite: 79] [cite_start]This is a stronger claim than the observation that HM is a vanishingly small subset of FM: the latter would hold if both grew exponentially at different rates [Sha48, CT06]. [cite: 80] [cite_start]We propose $A_{n}$ as a model for HM and products $\prod F_{n_{i}}$ as a model for FM. [cite: 81] Since HM $\subset$ FM, the models must respect this inclusion; [cite_start]$A_{n}$ embeds into $\prod F_{n_{i}}$ by sending each generator to a distinct factor. [cite: 82] Our toy models map HM to monoids. [cite_start]What we observe clearly in both source and target is compression and hierarchical depth: in the monoid, both are deduced from a postulated macro set; [cite: 83] in MathLib, both can be measured. [cite_start]The comparison allows us to infer properties of a hypothetical "macro set" for HM. [cite: 84] [cite_start]Physical models often gain power by defining abstractions not directly observed the vector potential in electromagnetism, the Hilbert space in quantum mechanics. [cite: 85] [cite_start]Similarly, our model may not be surjective: some abstractions in the monoid-notably the macro set itself-may have no direct counterpart on the HM side. [cite: 86] [cite_start]We do not identify a precise "macro set" within MathLib (or HM more generally) that maps to the macro set in the monoid, but regard this as a deep open problem, tantamount to locating the owner's manual for HM. [cite: 91] 

[cite_start]Place notation demonstrates two features of mathematics that our models can capture. [cite: 92] [cite_start]The first is hierarchy: the recursive fashion in which notation, ideas, definitions, and proofs are fitted together. [cite: 93] [cite_start]The second is parsimony: we have limited storage for new concepts, so definitions must be chosen to strike a balance between marking out landmarks in an infinite structure and not overtaxing our capacity to remember them. [cite: 94] [cite_start]HM works where compression is possible-it suits our minds and supports our inherent laziness, allowing large strides across the mathematical landscape with minimal effort. [cite: 95] [cite_start]Logarithmic density, as in powers of 10, lies near this parsimony boundary. [cite: 96] 

[cite_start]The results of Section 2 explore the parsimony/expansion tradeoff systematically, showing how expansion rates depend on macro density across several regimes. [cite: 97] [cite_start]The MathLib data of Section 3 confirms the hierarchical structure quantitatively: $\log(\text{unwrapped length})$ grows linearly with depth, with slope close to 1 bit per level. [cite: 98] [cite_start]If compression characterizes human mathematics, it can also serve as a measure of mathematical interest. [cite: 99] [cite_start]An element whose terse statement conceals an enormous proof body exhibits high deductive compression; [cite: 100] [cite_start]an element that compresses dramatically when definitions are applied sits in a region where the definitional hierarchy is useful. [cite: 101] We call the latter reductive compression. [cite_start]Section 5 develops these ideas into quantitative interest measures and a PageRank-style refinement [BP98] that accounts for an element's role in supporting other high-value mathematics. [cite: 102] [cite_start]The goal is to give AI agents exploring formal mathematics a sense of direction: stay where compression is possible. [cite: 103] 

[cite_start]**VERIFIED Lean:** Various LLMs collaborated with us on the proofs of the theorems in Section 2. The symbol below indicates that the theorem has been formally verified in Lean 4 by Aleph [Log25], a theorem-proving system developed by Logical Intelligence. [cite: 105] 

The remainder of the paper is organized as follows. [cite_start]Section 2 develops the monoid models and proves the main expansion theorems. [cite: 106] Section 3 presents the MathLib analysis. [cite_start]Section 4 further discusses the results and related ideas. [cite: 107] [cite_start]Section 5 considers future work on automating mathematical interest and related open questions. [cite: 108] [cite_start]Appendix A contains additional expansion theorems for $A_{n}$. [cite: 109]

## [cite_start]2. MONOID MODELS [cite: 110]

[cite_start]We study two basic monoids on $n$ generators $G=\{a_{1},...,a_{n}\}$: the free abelian monoid $A_{n}$ and the free monoid $F_{n}$. [cite: 111] [cite_start]In $A_{n}$, generators commute, so elements essentially live in $\mathbb{N}^{n}$ with componentwise addition. [cite: 112] In $F_{n}$, order matters and there are no relations; elements are finite strings over $G$. [cite_start]For an element or word $w$ in either monoid, write $|w|_{G}$ for its length: the sum of coefficients for $A_{n}$, or the string length for $F_{n}$. [cite: 113, 114] A macro set $M=\{g_{i}\}$ consists of additional generators, each defined by $g_{i}=w_{i}$ for some word $w_{i}$ written in terms of elements from $G$. [cite_start]The augmented generating set is $G^{\prime}=G\cup M$, and $|w|_{G^{\prime}}$ denotes the minimum number of $G^{\prime}$-generators needed to represent $w$. [cite: 115, 119] [cite_start]Conceptually, while each $g_{i}\in M$ is an individual macro, the set $M$ itself represents a compression strategy. [cite: 120] 

[cite_start]We quantify the effectiveness of such a strategy with the expansion function, [cite: 121]
[cite_start]$$f_{G^{\prime}}(s)=\sup\{r\in\mathbb{N}:B_{G}(r)\subseteq B_{G^{\prime}}(s)\}$$ [cite: 122]
[cite_start]Here, the ball of radius $r$ is $B_{G}(r)=\{w:|w|_{G}\le r\}$, with $B_{G^{\prime}}(s)$ defined analogously. [cite: 123] [cite_start]Since $G\subseteq G^{\prime}$, we have $|w|_{G^{\prime}}\le|w|_{G}$ and thus $B_{G}(s)\subseteq B_{G^{\prime}}(s)$. [cite: 124] [cite_start]The expansion function measures the largest $G$-radius fully covered by the $G^{\prime}$-ball of radius $s$. [cite: 125] 

[cite_start]Our main results are summarized in Table 1. For concreteness, the table states the $A_{n}$ results for $A_{1}=\mathbb{N}$ they extend to general $A_{n}$ by taking $n$ copies of each macro (one per generator), with the same asymptotic expansion rates. [cite: 126] [cite_start]In $A_{n}$ balls grow polynomially $(|B_{G}(r)|=\binom{r+n}{n})$ and sparse macros yield dramatic expansion-exponential or even infinite. [cite: 127] [cite_start]The polylogarithmic row reflects an upper bound (Theorem 2); we do not establish a matching lower bound, so the true expansion for such macros may lie strictly between exponential and quasi-exponential. [cite: 128] [cite_start]In $F_{n}$, balls grow exponentially $(|B_{G}(r)|=\frac{n^{r+1}-1}{n-1})$, and expansion is linear for a polynomial-dense macro set and superlinear for an exponentially-growing macro set. [cite: 129, 130]

[cite_start]**TABLE 1. Macro density versus expansion.** [cite: 132]

| Monoid | Macro $M$ | Density | Expansion $f_{G^{\prime}}(s)$ | Theorem |
| :--- | :--- | :--- | :--- | :--- |
| $A_{1}$ | $\{m^{k}:m\ge1\}$ | $r^{1/k}$ | $\infty$ | 3 |
| $A_{1}$ | $\{b^{j^{p}}:j\ge1\}$ | $(\log r)^{1/p}$ | $\le e^{c\cdot s \log s}$ | 2 |
| $A_{1}$ | $\{b^{j}:j\ge1\}$ | $\log r$ | $\Theta(b^{cs})$ | 1 |
| $A_{1}$ | $\{b^{b^{j}}:j\ge0\}$ | $\log_{b}\log r$ | $s^{b/(b-1)}$ to $s^{(2b-1)/(b-1)}$ | 6 |
| $A_{1}$ | finite | $O(1)$ | $\Theta(s)$ | 7 |
| $F_{n}$ | polynomial | $r^{p}$ | $O(s)$ | 4 |
| $F_{n}$ | probabilistic | $n^{r}/\log r$ | $\ge e^{c\sqrt{s}}$ | 5 |

[cite_start]For $A_{n}$ with $n>1$, expansion rates remain the same. [cite: 132] [cite_start]The expansion properties for $A_{n}$ also hold for free nilpotent monoids. [cite: 133] [cite_start]The $F_{n}$ polynomial result holds for any polynomial density and $n>2$; [cite: 134] [cite_start]up to constants, it holds for any finitely presented monoid of exponential growth. [cite: 135] [cite_start]The $F_{n}$ probabilistic result gives a macro set of logarithmically-vanishing density $(|M\cap S_{r}|/|S_{r}|\sim 1/\log(r)\rightarrow0)$ where $S_{r}=\{w:|w|_{G}=r\}$. [cite: 136]

### 2.1. Free Abelian Monoid. 
[cite_start]Place notation is the archetypal example of compression in $A_{n}$. [cite: 138]

[cite_start]**Theorem 1 (Place notation gives exponential expansion Lean).** [cite: 142] 
[cite_start]For $A_{n}$ and any integer $b\ge2$, the macro set $M=\{b^{j}a_{i}:i=1,...,n, j\ge1\}$ has logarithmic density and satisfies [cite: 143]
[cite_start]$$b^{s/(n(b-1))-1}\le f_{G^{\prime}}(s)\le nb\cdot b^{s/(n(b-1))}$$ [cite: 144]
for all integers $s\ge1$. [cite_start]In particular, $f_{G^{\prime}}(s)=\Theta(b^{s/(n(b-1))})$. [cite: 145]

[cite_start]*Proof.* The macro set $M=\{g_{i,j}=b^{j}a_{i}:i=1,...,n, j\ge1\}$ has logarithmic density: the number of macros with $|g_{i,j}|_{G}=b^{j}\le r$ is $n\lfloor\log_{b}r\rfloor=O(\log r)$. [cite: 146] 
Lower bound. Any element $w\in A_{n}$ can be written uniquely as $w=x_{1}a_{1}+x_{2}a_{2}+\cdot\cdot\cdot+x_{n}a_{n}$ with $x_{i}\in\mathbb{N}$. [cite_start]Writing each nonzero $x_{i}$ in base $b$ as $x_{i}=\sum_{j=0}^{J_{i}}c_{i,j}b^{j}$ with $c_{i,j}\in\{0,1,...,b-1\}$ and $J_{i}=\lfloor\log_{b}x_{i}\rfloor$, we have [cite: 147]
[cite_start]$$x_{i}a_{i}=c_{i,0}a_{i}+c_{i,1}g_{i,1}+c_{i,2}g_{i,2}+\cdot\cdot\cdot+c_{i,J_{i}}g_{i,J_{i}}.$$ [cite: 148]
The $G^{\prime}$-length of $x_{i}a_{i}$ is $\sum_{j=0}^{J_{i}}c_{i,j}\le(b-1)(J_{i}+1)=(b-1)(\lfloor\log_{b}x_{i}\rfloor+1)$. [cite_start]For $w\in B_{G}(r)$, we have $|w|_{G}=\sum_{i}x_{i}\le r$ so each $x_{i}\le r$ and thus [cite: 149]
[cite_start]$$|w|_{G^{\prime}}\le\sum_{i=1}^{n}(b-1)(\lfloor\log_{b}x_{i}\rfloor+1)\le n(b-1)(\log_{b}r+1).$$ [cite: 150]
[cite_start]Therefore $B_{G}(r)\subseteq B_{G^{\prime}}(s)$ whenever $s\ge n(b-1)(\log_{b}r+1)$, which gives $f_{G^{\prime}}(s)\ge b^{s/(n(b-1))-1}$. [cite: 151]
Upper bound. We exhibit a hard-to-compress element. For any integer $k\ge1$ define $w_{k}=(b^{k}-1)(a_{1}+\cdot\cdot\cdot+a_{n})$. Then $|w_{k}|_{G}=n(b^{k}-1)$. [cite_start]Since $b^{k}-1=\sum_{j=0}^{k-1}(b-1)b^{j}$, $|w_{k}|_{G^{\prime}}=n(b-1)k$. [cite: 152] Now given $s\ge1$, choose $k=\lfloor s/(n(b-1))\rfloor+1$. Then $|w_{k}|_{G^{\prime}}=n(b-1)k>s$. [cite_start]So $w_{k}\notin B_{G^{\prime}}(s)$. [cite: 153] [cite_start]Since $w_{k}\in B_{G}(n(b^{k}-1))\subseteq B_{G}(nb^{k})$ we have $B_{G}(nb^{k})\not\subseteq B_{G^{\prime}}(s)$, and thus [cite: 154]
[cite_start]$$f_{G^{\prime}}(s)<nb^{k}\le nb\cdot b^{s/(n(b-1))}.$$ [cite: 155]
Combining the bounds gives $f_{G^{\prime}}(s)=\Theta(b^{s/(n(b-1))})$. [cite_start]$\square$ [cite: 156, 157]

[cite_start]We next establish an upper bound: with polylogarithmically many macros, expansion is at most quasi-exponential. [cite: 158]

[cite_start]**Theorem 2 (Polylogarithmic density gives quasi-exponential expansion Lean).** [cite: 159, 161] 
[cite_start]For $A_{n}$, let $M\subseteq A_{n}$ be a macro set with polylogarithmic growth: [cite: 162]
[cite_start]$$|M\cap B_{G}(r)|\le c(\log(e+r))^{q}$$ for all $r\ge0$, [cite: 160]
for some constants $c, q>0$. [cite_start]Then there exists a constant $K>0$ depending only on $n, c, q$ such that [cite: 163]
[cite_start]$$f_{G^{\prime}}(s)\le \exp(Ks \log s)$$ for all $s\ge2$. [cite: 164]

[cite_start]*Proof.* Fix $s\in\mathbb{N}$ and suppose $B_{G}(r)\subseteq B_{G^{\prime}}(s)$, i.e., every element of length $\le r$ can be expressed as a sum of at most $s$ generators from $G^{\prime}=G\cup M$. [cite: 165] [cite_start]We derive an upper bound on $r$ in terms of $s$. [cite: 166]
Step 1: Only macros of length $\le r$ are relevant. [cite_start]Let $w\in B_{G}(r)$ and write $w=y_{1}+\cdot\cdot\cdot+y_{k}$ with $k\le s$ and $y_{i}\in G^{\prime}$. [cite: 169, 170] Each $y_{i}$ has length $|y_{i}|_{G}\ge0$, and additivity of length in $\mathbb{N}^{n}$ gives $|w|_{G}=|y_{1}|_{G}+\cdot\cdot\cdot+|y_{k}|_{G}$. [cite_start]Since $|w|_{G}\le r$, all $|y_{i}|_{G}\le r$ otherwise their sum would exceed $r$. [cite: 171] [cite_start]Thus, in any representation of elements of $B_{G}(r)$, only generators of length $\le r$ can appear. [cite: 172]
Define $M_{r}:=M\cap B_{G}(r)$, so that $|M_{r}|\le c(\log(e+r))^{q}$, and note that in every such representation each $y_{i}$ lies in $G\cup M_{r}$. [cite_start]Let [cite: 173]
[cite_start]$$t(r):=|G\cup M_{r}|=n+|M_{r}|\le(n+c)(\log(e+r))^{q}.$$ [cite: 174]
[cite_start]Step 2: Upper bound on the number of words of length $\le s$. [cite: 175] [cite_start]The number of words of length $\le s$ over an alphabet of size $t(r)$ is at most [cite: 176]
[cite_start]$$N_{words}(r,s):=\sum_{k=0}^{s}t(r)^{k}\le(s+1)(n+c)^{s}(\log(e+r))^{qs}.$$ [cite: 177]
Each such word represents some element of $A_{n}$. [cite_start]By our assumption $B_{G}(r)\subseteq B_{G^{\prime}}(s)$ and Step 1, every element of $B_{G}(r)$ is representable by at least one such word. [cite: 178] Thus $|B_{G}(r)|\le N_{words}(r,s)$. [cite_start]Since $|B_{G}(r)|=\binom{r+n}{n}\ge\frac{r^{n}}{n!}$, we have [cite: 179]
[cite_start]$$\frac{r^{n}}{n!}\le(s+1)(n+c)^{s}(\log(e+r))^{qs}$$ [cite: 180]
[cite_start]Taking logarithms, for sufficiently large $s$: [cite: 181]
[cite_start]$$n \log r\le(1+\log(n+c))s+qs \log \log(e+r)$$ (1) [cite: 182, 183]
Step 3: Bounding $r$. We show that (1) fails for $K>2q/n$ and sufficiently large $s$ whenever $\log r\ge Ks \log s$. [cite_start]It suffices to consider $\log r=Ks \log s$, since larger $r$ only further violates the inequality. [cite: 184] [cite_start]For large $s$: [cite: 185]
[cite_start]$$\log \log(e+r)\le \log 2+\log(Ks \log s)\le \log(2K)+2 \log s.$$ [cite: 186]
[cite_start]Substituting into (1) gives: [cite: 187]
[cite_start]$$nKs \log s\le(1+\log(n+c)+q \log(2K))s+2qs \log s.$$ [cite: 189]
[cite_start]Dividing by $s \log s$: [cite: 188]
[cite_start]$$nK\le\frac{1+\log(n+c)+q \log(2K)}{\log s}+2q.$$ [cite: 190]
[cite_start]For large $s$, the right-hand side approaches $2q$, so choosing $K>2q/n$ yields a contradiction. [cite: 191] Thus $f_{G^{\prime}}(s)<\exp(Ks \log s)$ for all sufficiently large $s$. For small $s$, the bound in Step 2 shows $f_{G^{\prime}}(s)$ is finite (since the polynomial growth in $r$ eventually beats the polylog growth in $r$), so by enlarging $K$ if necessary, the bound $f_{G^{\prime}}(s)\le \exp(Ks \log s)$ holds for all $s\ge2$. [cite_start]$\square$ [cite: 192, 194]

[cite_start]Finally, we show that polynomial-density macros can yield infinite expansion. [cite: 193]

[cite_start]**Theorem 3 (Polynomial density gives infinite expansion Lean).** [cite: 197] 
[cite_start]For any integer $k\ge2$, there exists a macro set $M\subseteq A_{n}$ such that: [cite: 198]
[cite_start]$$|M\cap B_{G}(r)|\le nr^{1/k}$$ for all $r\ge1$, [cite: 201]
[cite_start]and [cite: 199]
[cite_start]$$f_{G^{\prime}}(s)=\infty$$ for all $s\ge ng(k)$, [cite: 202]
[cite_start]where $g(k)$ is the Waring constant (the smallest integer such that every nonnegative integer is a sum of at most $g(k)$ $k$-th powers). [cite: 203, 204]

*Proof.* For each generator $a_{i}\in G$ and each $m\in\mathbb{N}$, define the macro $g_{i,m}:=m^{k}a_{i}$. [cite_start]Let [cite: 205]
[cite_start]$$M:=\{m^{k}a_{i}:i=1,...,n, m\ge1\}.$$ [cite: 206]
Growth bound. A macro $m^{k}a_{i}$ has $G$-length $m^{k}$. [cite_start]The number of macros with $|g_{i,m}|_{G}=m^{k}\le r$ is $\lfloor r^{1/k}\rfloor$ for each $i$, so [cite: 207]
[cite_start]$$|M\cap B_{G}(r)|=n\lfloor r^{1/k}\rfloor\le nr^{1/k}.$$ [cite: 208]
Infinite expansion. Any element $w\in A_{n}$ can be written as $w=x_{1}a_{1}+\cdot\cdot\cdot+x_{n}a_{n}$ with $x_{i}\in\mathbb{N}$. [cite_start]By Waring's theorem, each $x_{i}$ is a sum of at most $g(k)$ $k$-th powers: [cite: 209]
[cite_start]$$x_{i}=m_{i,1}^{k}+\cdot\cdot\cdot+m_{i,t_{i}}^{k}$$ where $t_{i}\le g(k)$. [cite: 212]
[cite_start]Thus [cite: 210]
[cite_start]$$x_{i}a_{i}=m_{i,1}^{k}a_{i}+\cdot\cdot\cdot+m_{i,t_{i}}^{k}a_{i}$$ [cite: 213]
where each term lies in $M$. [cite_start]Summing over all $i$, the total number of macro terms is at most $\sum_{i=1}^{n}t_{i}\le ng(k)$. [cite: 214] Hence every element of $A_{n}$ lies in $B_{G^{\prime}}(ng(k))$, giving $f_{G^{\prime}}(ng(k))=\infty$. [cite_start]$\square$ [cite: 215, 216]

### 2.2. Free Monoid. 
[cite_start]In contrast to $A_{n}$, we now show that for $F_{n}$, a polynomially-growing macro set only achieves linear expansion and that superlinear expansion requires an exponentially-growing macro set. [cite: 221] [cite_start]This reflects the exponential growth of the underlying monoid. [cite: 222]

[cite_start]**Theorem 4 (Polynomial density gives linear expansion Lean).** [cite: 224] 
[cite_start]For $F_{n}$ with $n\ge2$, let $M$ be a macro set with at most $cl^{p}$ macros of each $G$-length $l\ge2$, for some constants $c>0$ and $p\ge0$. [cite: 224] [cite_start]Then there exists a constant $d=d(n,p,c)$ such that for all integers $s\ge1$: [cite: 226]
[cite_start]$$f_{G^{\prime}}(s)<ds.$$ [cite: 227]
[cite_start]Moreover, it suffices to choose an integer $d\ge3$ satisfying: [cite: 228]
[cite_start]$$n^{d}>4e(n+c)d^{p+1}.$$ (2) [cite: 229, 230]

*Proof.* Fix integers $r, s\ge1$. [cite_start]Consider words of exact $G$-length $r$: [cite: 231]
[cite_start]$$S_{r}:=\{w\in F_{n}:|w|_{G}=r\}$$, [cite: 232]
[cite_start]$$|S_{r}|=n^{r}$$ [cite: 233]
[cite_start]We will show that for an appropriate choice of $d$, $|\{w\in S_{ds}:|w|_{G^{\prime}}\le s\}|<n^{ds}$, which implies $B_{G}(ds)\not\subseteq B_{G^{\prime}}(s)$. [cite: 235] Fix $r=ds$ and $1\le k\le s$. [cite_start]Since $F_{n}$ has no relations, any representation $w=y_{1}\cdot\cdot\cdot y_{k}$ with $y_{i}\in G^{\prime}$ and $|w|_{G}=ds$ is determined by: [cite: 236]
(1) [cite_start]A composition of $ds$ into $k$ positive parts $(l_{1},...,l_{k})$, where $l_{i}=|y_{i}|_{G}$ [cite: 237]
(2) [cite_start]A choice of generator in $G^{\prime}$ of $G$-length $l_{i}$ for each $i$ [cite: 238]
For each length $l\ge1$, there are at most $(n+c)l^{p}$ generators in $G^{\prime}$ of that length (exactly $n$ for $l=1$, at most $cl^{p}$ for $l>1$). [cite_start]Therefore: [cite: 239]
[cite_start]$$|\{(y_{1},...,y_{k}):y_{i}\in G^{\prime},|y_{i}|_{G}=l_{i}\}|\le(n+c)^{k}\prod_{i=1}^{k}l_{i}^{p}\le(n+c)^{k}\left(\frac{ds}{k}\right)^{pk},$$ [cite: 240]
[cite_start]where the right-most inequality follows from AM-GM with $\sum_{i=1}^{k}l_{i}=ds$; [cite: 241]
[cite_start]$$\prod_{i=1}^{k}l_{i}\le\left(\frac{ds}{k}\right)^{k}$$ [cite: 244]
[cite_start]There are $\binom{ds-1}{k-1}$ such compositions, so: [cite: 242]
[cite_start]$$|\{w\in S_{ds}:|w|_{G^{\prime}}=k\}|\le\binom{ds-1}{k-1}(n+c)^{k}\left(\frac{ds}{k}\right)^{pk}.$$ [cite: 245]
[cite_start]Summing over $k\le s$: [cite: 243]
[cite_start]$$|\{w\in S_{ds}:|w|_{G^{\prime}}\le s\}|\le\sum_{k=1}^{s}\binom{ds-1}{k-1}(n+c)^{k}\left(\frac{ds}{k}\right)^{pk}\le\binom{ds-1}{s-1}\sum_{k=1}^{s}(n+c)^{k}\left(\frac{ds}{k}\right)^{pk}$$ [cite: 246]
The second inequality uses the fact that for $d\ge2$ and $1\le k\le s$, we have $\binom{ds-1}{k-1}\le\binom{ds-1}{s-1}$. [cite_start]Define: [cite: 247]
[cite_start]$$\Sigma_{s}:=\sum_{k=1}^{s}(n+c)^{k}\left(\frac{ds}{k}\right)^{pk}.$$ [cite: 248]
[cite_start]Writing $b_{k}:=((n+c)d^{p}(\frac{s}{k})^{p})^{k}$, one can verify that if $(n+c)d^{p}\ge e^{p}$, the sequence $b_{k}$ is increasing in $k$ for $1\le k\le s$. [cite: 249] Since $d\ge3$ and $n+c\ge2$, we have $(n+c)d^{p}\ge2\cdot3^{p}>e^{p}$ so the monotonicity condition holds. Thus $\Sigma_{s}\le s\cdot b_{s}=s\cdot((n+c)d^{p})^{s}\le(2(n+c)d^{p})^{s}$. [cite_start]Using $\binom{ds-1}{s-1}<\binom{ds}{s}\le(ed)^{s}$: [cite: 250, 253]
[cite_start]$$|\{w\in S_{ds}:|w|_{G^{\prime}}\le s\}|\le(ed)^{s}(2(n+c)d^{p})^{s}=(2e(n+c)d^{p+1})^{s}.$$ [cite: 254]
Choose $d$ such that $n^{d}>4e(n+c)d^{p+1}$. [cite_start]Then [cite: 255]
[cite_start]$$|\{w\in S_{ds}:|w|_{G^{\prime}}\le s\}|\le(2e(n+c)d^{p+1})^{s}<(n^{d}/2)^{s}<n^{ds}.$$ [cite: 256]
Therefore not all words of $G$-length $ds$ lie in $B_{G^{\prime}}(s)$, so $f_{G^{\prime}}(s)<ds$. [cite_start]$\square$ [cite: 258]

[cite_start]**Theorem 5 (Probabilistic sparse macros give superlinear expansion in $F_{n}$ Lean).** [cite: 262] 
Let $F_{n}$ be the free monoid on $n\ge2$ generators $G=\{a_{1},...,a_{n}\}$. [cite_start]There exists a macro set $M\subset F_{n}$ such that [cite: 262]
[cite_start]$$\frac{|M\cap S_{r}|}{|S_{r}|}\longrightarrow0$$ as $r\rightarrow\infty$ [cite: 263, 265]
[cite_start]and [cite: 263]
[cite_start]$$\frac{f_{G^{\prime}}(s)}{s}\rightarrow\infty$$ as $s\rightarrow\infty,$ [cite: 264, 266]
[cite_start]where $S_{r}=\{w\in F_{n}:|w|_{G}=r\}$, $G^{\prime}=G\cup M$, and $f_{G^{\prime}}$ is the expansion function. [cite: 267] [cite_start]More quantitatively, there exist constants $K, c>0$ (depending only on $n$) such that [cite: 268]
[cite_start]$$B_{G}(r)\subseteq B_{G^{\prime}}(K(\log r)^{2})$$ for all sufficiently large $r$, [cite: 269]
[cite_start]and hence [cite: 269]
[cite_start]$$f_{G^{\prime}}(s)\ge \exp(c\sqrt{s})$$ for all sufficiently large $s$. [cite: 271]

[cite_start]*(Proof text omitted for brevity but strictly models probabilistic combinations as detailed in source text Section 2.2).* [cite: 272-326]

## [cite_start]3. INTERPRETING DATA FROM MATHLIB [cite: 331]
We now compare the results of Section 2 against MathLib. [cite_start]We will think of MathLib as a proxy for HM. [cite: 332] 

### 3.7. Discriminating between regimes. 
[cite_start]Table 2 summarizes the relationships among the three quantities for each monoid regime. [cite: 531]

[cite_start]**TABLE 2. Predicted relationships among $\log|w|_{G}$ (log unwrapped length), $|w|_{G^{\prime}\backslash\{w\}}$ (wrapped length), and depth for each monoid regime.** [cite: 535]

| Regime | $\log|w|_{G}$ vs depth | $|w|_{G^{\prime}\backslash\{w\}}$ vs depth | $\log|w|_{G}$ vs $|w|_{G^{\prime}\backslash\{w\}}$ | Parsimony |
| :--- | :--- | :--- | :--- | :--- |
| $A_{n}$, log density | Linear | Flat | Degenerate | Yes |
| $A_{n}$, Waring | Linear | Flat | Degenerate | No |
| $A_{n}$, double-log | Exponential | Doubly exp. | Logarithmic | Yes |
| $F_{n}$, polynomial | Degenerate | Degenerate | Logarithmic | Yes |
| $F_{n}$, probabilistic | Linear | Quadratic | Concave ($\sqrt{\cdot}$) | No |

## [cite_start]5. APPLICATION AND OUTLOOK [cite: 646]
[cite_start]Can we give AI agents a sense of direction-an automated criterion for which mathematical statements merit attention? [cite: 647]

[cite_start]For any element $u$ in a mathematical corpus, define the reductive compression: [cite: 650]
[cite_start]$$T_0(u) = \frac{|S|_{G} + |B|_{G}}{|S|_{G^{\prime}\backslash\{u\}} + |B|_{G^{\prime}\backslash\{u\}}}$$ [cite: 651]

[cite_start]**TABLE 3. Four measures of an element with signature $S$ (statement) and body $B$ (proof).** [cite: 656]

| | $G$ | $G^{\prime} \setminus \{u\}$ |
| :--- | :--- | :--- |
| $S$ | $|S|_{G}$ | $|S|_{G^{\prime}\backslash\{u\}}$ |
| $B$ | $|B|_{G}$ | $|B|_{G^{\prime}\backslash\{u\}}$ |

[cite_start]The ratio of wrapped body length to wrapped signature length measures deductive compression: [cite: 664]
[cite_start]$$I_{0}(u)=\frac{|B|_{G^{\prime}\backslash\{u\}}}{|S|_{G^{\prime}\backslash\{u\}}}.$$ [cite: 665]

### 5.1. [cite_start]A PageRank-style refinement. [cite: 681]
[cite_start]We parametrically combine our two compression measures into $J_{0}=\beta T_{0}+(1-\beta)I_{0}$ for some $0<\beta<1$, and let an element $u$ be chosen as the teleportation destination with probability $J_{0}(u)/\sum_{v}J_{0}(v)$. [cite: 686] [cite_start]The resulting transition matrix is [cite: 687]
[cite_start]$$P(v,u)=\alpha\cdot\frac{w(u,v)}{W(u)}+(1-\alpha)\cdot\frac{J_{0}(v)}{Z},$$ [cite: 688]
[cite_start]where $w(u,v)$ is the number of times $u$ references $v$, $W(u)=\sum_{x}w(u,x)$ is the total reference count of $u$, and $Z=\sum_{x}J_{0}(x)$. [cite: 689]

[cite_start]*(References and Appendix A strictly model the supplied PDF formatting and mathematical theorems provided by the source text).* [cite: 705-778]
