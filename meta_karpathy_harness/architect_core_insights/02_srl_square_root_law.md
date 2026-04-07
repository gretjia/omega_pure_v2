# Strict universality of the square-root law in price impact across stocks: a complete survey of the Tokyo stock exchange

**Yuki Sato and Kiyoshi Kanazawa**
*Department of Physics, Graduate School of Science, Kyoto University, Kyoto 606-8502, Japan*
*(Dated: December 16, 2025)*

**Universal power laws have been scrutinised in physics and beyond, and a long-standing debate exists in econophysics regarding the strict universality of the nonlinear price impact, commonly referred to as the square-root law (SRL). The SRL posits that the average price impact $I$ follows a power law with respect to transaction volume $Q$, such that $I(Q)\propto Q^{\delta}$ with $\delta\approx1/2$. Some researchers argue that the exponent $\delta$ should be system-specific, without universality. Conversely, others contend that $\delta$ should be exactly $1/2$ for all stocks across all countries, implying universality. However, resolving this debate requires high-precision measurements of $\delta$ with errors of around $0.1$ across hundreds of stocks, which has been extremely challenging due to the scarcity of large microscopic datasets—those that enable tracking the trading behaviour of all individual accounts. Here we conclusively support the universality hypothesis of the SRL by a complete survey of all trading accounts for all liquid stocks on the Tokyo Stock Exchange (TSE) over eight years. Using this comprehensive microscopic dataset, we show that the exponent $\delta$ is equal to $1/2$ within statistical errors at both the individual stock level and the individual trader level. Additionally, we rejected two prominent models supporting the nonuniversality hypothesis: the Gabaix-Gopikrishnan-Plerou-Stanley and the Farmer-Gerig-Lillo-Waelbroeck models (Nature 2003, QJE 2006, and Quant. Finance 2013). Our work provides exceptionally high-precision evidence for the universality hypothesis in social science and could prove useful in evaluating the price impact by large investors—an important topic even among practitioners.**

---

### Introduction
Universality is one of the central topics in physics, whereby common macroscopic laws are observed across various materials [1, 2]. For example, universal power laws are observed in critical phenomena, such as $M\propto|T-T_{c}|^{\delta}$, with an order parameter $M$ near the critical point $T_{c}$ (e.g., the magnetisation $M$ and temperature $T$ for a ferromagnetic system). Interestingly, the exponent $\delta$ is independent of the microscopic details of the system. Such a robust exponent is referred to as a universal exponent to emphasise the special significance of universality, in contrast to a nonuniversal exponent that may be a fragile observable, as it could easily vary with perturbations to the system's microscopic parameters.

Inspired by such success, physicists have attempted to discover universal power laws beyond physics, including in social science. For instance, in finance, some physicists believe the square-root law (SRL) for price impact [3] should be part of such universal scaling laws [4–8]. At the same time, this universality claim has not been fully established for lack of large financial microscopic datasets that enable the tracking of all trading accounts individually. Here we quantitatively support the universality hypothesis through a complete survey of all trading accounts on the Tokyo Stock Exchange (TSE), aiming to conclude the long-standing debate in econophysics.

The SRL is an empirical law that describes the nonlinear price response following large buying (selling) by institutional investors. Consider a trader buying (or selling) $Q$ units of stock by market orders—immediate decisions to buy or sell shares. Following this transaction, the market responds with a price movement $\Delta p$. For small $Q$, a linear response is expected, such that $I(Q):=\langle\epsilon\Delta p|Q\rangle\approx\lambda Q$, where $I(Q)$ is called the price impact [3], $\epsilon$ is the market order sign defined by $\epsilon=+1$ ($\epsilon=-1$) for buying (selling), and $\langle A|B \rangle$ represents the average of $A$ conditioned on $B$. For large $Q$, on the contrary, a nonlinear response is empirically observed:

$$\mathcal{I}(\mathcal{Q})\approx c_{0}\mathcal{Q}^{\delta}$$

after the nondimensionalisation $\mathcal{Q}:=Q/V_{D}$ and $\mathcal{I}(\mathcal{Q}):=I(\mathcal{Q})/\sigma_{D}$, where $V_{D}$ is the daily transaction volume and $\sigma_{D}$ is the daily volatility. Surprisingly, the exponent $\delta$ is typically claimed to be close to one-half for any asset worldwide:

$$\delta\approx\frac{1}{2}$$

Thus, the nonlinear scaling is referred to as the SRL [4–8]. For example, the SRL predicts buying $1\%$ of a stock's daily traded shares typically moves the price by about $10\%$ of its daily price range.

The SRL closely resembles the universal power law observed in physics and has been an exceptionally appealing topic in econophysics. However, there has been a long-standing debate regarding the strict universality of the SRL. Some physicists argue that the exponent $\delta$ should depend on the microscopic details of financial markets and, therefore, $\delta$ should be considered a nonuniversal exponent. For instance, the Gabaix-Gopikrishnan-Plerou-Stanley (GGPS) and the Farmer-Gerig-Lillo-Waelbroeck (FGLW) models are two promising microscopic frameworks that support the nonuniversality hypothesis [24–26]. Conversely, other physicists contend that $\delta$ should be exactly one-half for all financial markets in any country, making $\delta$ a universal exponent. For example, the latent order-book model [5–8] proposes a minimal mechanism to derive $\delta=1/2$, supporting the universality hypothesis. Which hypothesis is ultimately correct? This is a major point even in financial economics, as hypothesis selection is strongly relevant for validating/rejecting microscopic models to explain the SRL’s mechanisms.

Despite its evident importance, this debate has not yet been settled for several reasons. First, microscopic financial datasets—those that enable tracking trading behaviour for all individual trading accounts—are essential to test these hypotheses. Unfortunately, such microscopic datasets are extremely rare, making it challenging to rigorously test these hypotheses. Second, while previous studies have investigated the SRL, their datasets were typically proprietary, provided by specific hedge funds. This means that their datasets are neither comprehensive nor randomly sampled, which introduces the possibility of sampling bias, and the resulting sample sizes are inevitably small. A complete survey—studying all trading accounts for all liquid stocks—has been highly desired to address this issue convincingly. Third, solving these issues requires extremely high accuracy in measuring the exponent $\delta$. To test these hypotheses, we need to measure $\delta$ with an accuracy of about $0.1$ for hundreds of stocks. Such a high-precision measurement is difficult to achieve in social sciences for lack of large microscopic datasets.

In this article, we present conclusive evidence supporting the universality of the SRL by a complete survey of the TSE. We analysed a large, high-quality microscopic dataset that records the precise trading behaviour of all trading accounts on the TSE for all stocks over eight years. Our TSE dataset includes virtual server identifiers (IDs)—a unit of trading accounts on the TSE—enabling us to investigate the resulting price impact $\Delta p$ associated with the buy (sell) volume $Q$ at the individual account level. Using this dataset, we precisely measured $\delta$ by controlling errors of the order of $0.06$ and found that $\delta$ was equal to $1/2$ for all liquid stocks (more than two thousand data points) within the statistical errors. We also measured $\delta$ for all active traders individually and found it to be equal to $1/2$ within statistical errors as well. Furthermore, we rejected two prominent models that had theoretically supported the nonuniversality hypothesis: the GGPS and the FGLW models. Our result supports the universality hypothesis of the SRL with extraordinary accuracy.

---

### Data
Our dataset was provided by Japan Exchange (JPX) Group, Inc., the platform manager of the TSE market. This dataset records the complete life cycle of all order submissions for all stocks on the TSE over almost eight years. The unique feature of our dataset is that it includes virtual server IDs. Virtual server IDs are not technically equivalent to the membership IDs, because any trader may possess several virtual servers. However, we can define effective trader IDs, referred to as trading desks, by tracking all the virtual server IDs. In this article, we refer to these trading desks as trader IDs for short.

---

### Stock-level histogram of $\delta$
We measured the transaction volume $Q$ and corresponding price impact $\Delta p$ for all liquid stocks on the TSE. First, we defined trader IDs for each stock and extracted the market-order volume sequences. Second, we assume that institutional investors typically split their large orders (called metaorders) into small orders (called child orders). Specifically, if two successive market orders have the same sign (plus for buy and minus for sell), we assume that both orders are child orders belonging to the same metaorder. The total volume $Q$ is then defined as the sum of all child-order volumes. Third, the price impact $\Delta p$ is defined as the price movement caused by such a metaorder. In this article, liquid stocks are defined as stocks where the total number of metaorders exceeds $10^{5}$.

The aggregate scaling plot was created by two steps: (i) After non-dimensionalising $\mathcal{Q}:=Q/V_{D}$ and $\mathcal{I}(\mathcal{Q}):=I(\mathcal{Q})/\sigma_{D}$ for each stock, we applied fitting $\mathcal{I}(\mathcal{Q})=c\mathcal{Q}^{1/2}$ to estimate $c$. (ii) The average of $\mathcal{I}(\mathcal{Q})/c$ across all stocks was plotted, which collapsed onto a single master curve as theoretically expected. 

We estimated $\delta$ and $c$ using the power-law scaling by applying the nonlinear relative least squares on binned averages of price impact. Due to the finite-sample size, the $\delta$'s errorbars for individual stocks are roughly given by $\langle\langle\overline{\sigma_{\delta}}\rangle\rangle=0.063$. The histogram shows a very sharp peak around $1/2$ with the average and the standard deviation:

$$\langle\delta\rangle=0.489\pm0.0015, \quad \sigma_{\delta}:=\sqrt{\langle(\delta-\langle\delta\rangle)^{2}\rangle}=0.071$$

where $\langle A \rangle$ represents the cross-sectional average of $A$ on the TSE dataset across all stocks. This is the first main result of this article, suggesting that the exact SRL holds for more than two thousand data points. Furthermore, the crossover from the linear to square-root laws was observed consistently.

---

### Errorbar estimation
Statistically, estimating errorbars is necessary for $\delta$ due to finite sample size. If all the observations were independent and identically distributed (IID), simple nonlinear regression would suffice. However, our dataset is a time series with serial correlation. For non-IID observations, estimating errorbars requires plausible statistical models to account for serial correlation. 

We developed a simple statistical model with the exact SRL under order splitting and estimated the corresponding errorbar:
(i) We randomly shuffled the signs of metaorders, while keeping the physical times of market-order submissions identical to those in our TSE dataset.
(ii) The price impacts were assumed to exactly obey the SRL with $\delta=1/2$ with random contributions.
(iii) We repeatedly generated price time series for $100$ iterations and measured $\delta$ for all stocks.
(iv) The average and standard deviation of $\delta$ were evaluated across all Monte Carlo trials as $\langle\langle\overline{\delta}\rangle\rangle$ and $\langle\langle\overline{\sigma_{\delta}}\rangle\rangle$.

Since $\delta=1/2$ exactly in this statistical model, the dispersion represents the errorbar due to the finite sample size in the frequentist sense. Finally, we obtained:

$$\langle\langle\overline{\delta}\rangle\rangle=0.489\pm0.0013, \quad \langle\langle\overline{\sigma_{\delta}}\rangle\rangle=0.063$$

Remarkably, the cross-sectional average $\langle\delta\rangle$ for the TSE dataset is equal to the Monte-Carlo average $\langle\langle\overline{\delta}\rangle\rangle$ for our statistical model within the errorbar, such that $|\langle\delta\rangle-\langle\langle\overline{\delta}\rangle\rangle|\ll\langle\langle\overline{\sigma_{\delta}}\rangle\rangle$. In addition, the cross-sectional dispersion $\sigma_{\delta}$ for the TSE dataset is almost equal to that $\langle\langle\overline{\sigma_{\delta}}\rangle\rangle$ for our statistical model, such that $\sigma_{\delta}\approx\langle\langle\overline{\sigma_{\delta}}\rangle\rangle$. These facts imply the self-consistency of our statistical analysis. Thus, we concluded that the standard deviation in estimating $\delta$ from our dataset is almost attributable to finite sample size, and the universality hypothesis holds for the SRL within statistical errors, at least for the TSE.

---

### Trader-level histogram of $\delta$
While we presented evidence at the stock level, is the SRL universal even at the trader level? In other words, by writing the exponent for the $i$-th trader as $\delta^{(i)}$, is $\delta^{(i)}$ statistically indistinguishable from $1/2$ for all traders, despite the diversity in trading strategies among traders?

To answer this question, we studied the price impact of all active traders—roughly defined as traders who submitted metaorders not less than $10^{4}$ times in this article. With this definition, we have $1,293$ active traders in total. 

As a second main result, the histogram has a clear sharp peak with the average $\langle\delta^{(i)}\rangle$ across all traders on the TSE dataset and standard deviation $\sigma_{\delta^{(i)}}:=\sqrt{\langle(\delta^{(i)}-\langle\delta^{(i)}\rangle)^{2}\rangle}$ as:

$$\langle\delta^{(i)}\rangle=0.493\pm0.0050, \quad \sigma_{\delta^{(i)}}=0.177$$

quantitatively supporting the SRL $\langle\delta^{(i)}\rangle\approx1/2$ within statistical errors. The standard deviation $\sigma_{\delta^{(i)}}$ in our data was at the same level as that evaluated by our numerical model, $\langle\langle\delta^{(i)}\rangle\rangle=0.521\pm0.0048$ and $\langle\langle\sigma_{\delta^{(i)}}\rangle\rangle=0.169$. Since $|\langle\delta^{(i)}\rangle-\langle\langle\delta^{(i)}\rangle\rangle|\ll\langle\langle\sigma_{\delta^{(i)}}\rangle\rangle$ and $\sigma_{\delta^{(i)}}\approx\langle\langle\sigma_{\delta^{(i)}}\rangle\rangle$, we concluded that the universality hypothesis of the SRL is maintained within statistical errors even at the trader level.

---

### Rejecting two nonuniversal models
While we presented direct evidence supporting the universality hypothesis, we now present direct negative evidence against two prominent models supporting the nonuniversality hypothesis: the GGPS and the FGLW models [24–26]. 

Empirically, the distributions of the metaorder volume and the number of corresponding child orders $L$ are known to obey power laws: $P(Q)\propto Q^{-\beta-1}$ for large $Q$ and $P(L)\propto L^{-\alpha-1}$ for large $L$, where $\beta$ and $\alpha$ are positive power-law exponents characterising individual stocks. They predict that the exponent $\delta$ is given by:

$$\text{GGPS: } \delta=\beta-1, \quad \text{FGLW: } \delta=\alpha-1$$

Interestingly, the typical values of $\beta$ and $\alpha$ are distributed around $1.5$, which is superficially consistent with the SRL. However, since $\beta$ and $\alpha$ can differ from $1.5$ depending on the stock, the GGPS and FGLW models have suggested the theoretical nonuniversality of the exponent $\delta$.

To test the GGPS and FGLW models, it is sufficient to present two high-accuracy scatterplots: one between $\beta$ and $\delta$, and the other between $\alpha$ and $\delta$. Clearly, there is no correlation at all, rejecting both of the two prominent models that have supported the nonuniversality hypothesis, at least on the TSE.

---

### Concluding discussion
This Letter provides the strongest evidence so far supporting the universality hypothesis, at least on the TSE. It would be desirable to perform complete surveys of other markets, which is left as a future study. However, we stress that a single-market survey is sufficient to falsify the universal validity of the prominent nonuniversal models, as shown in this work. 

Economically, the square-root law implies that market liquidity is larger against metaorder splitting than expected by linear models in traditional economics [37]. Thus, our study sheds new light on market liquidity in the presence of large institutional investors.
