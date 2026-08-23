
# Optimizing Credit Allocation and Stress-Testing Bank Exposure Under
# Semicon 2.0: A Machine Learning Framework for Macro-Prudential Risk Management



## Abstract

India's semiconductor policy expansion creates a growing need to evaluate
project concentration, macro-financial vulnerability, and the allocation of
bank credit under adverse conditions. This study develops a transparent
machine-learning and macro-prudential framework covering 36
official semiconductor ecosystem projects.

Because no defensible project-level default, non-performing asset, repayment,
or probability-of-default target was publicly available, the study avoids
constructing synthetic default labels. Instead, it combines unsupervised
structural segmentation with deterministic stress testing and constrained
credit-allocation analysis.

Principal Component Analysis and validated K-Means clustering identified
6 structural ecosystem clusters. The selected solution produced a
silhouette score of 0.3351, a K-Means–hierarchical Adjusted Rand
Index of 0.7909, and bootstrap stability of
0.5810. These results indicate moderate cluster separation with
strong cross-method agreement.

A second analytical layer evaluates 12 semiconductor manufacturing projects
using project-scale, geographic concentration, RBI Electronics-sector credit
conditions, credit-growth volatility, and banking NPA indicators. The
resulting scores are interpreted as relative macro-prudential vulnerability,
not probabilities of default.

The policy-allocation framework was evaluated across 162
alternative configurations. Allocation rankings achieved a mean pairwise
Spearman rank correlation of 0.8918, indicating high robustness.
The preferred risk-heavy specification assigns 80% weight
to vulnerability and 20% to project scale, with maximum
individual-project and state exposure limits of
15% and 35% respectively.
Relative to investment-proportional allocation, this configuration reduced
the constructed portfolio stress index by 23.70%.

The framework provides a reproducible policy-oriented approach for assessing
semiconductor credit concentration under limited public outcome data while
avoiding unsupported claims of project-level default prediction.



## 1. Introduction

India's semiconductor ecosystem is expanding through manufacturing,
assembly, testing, packaging, compound-semiconductor, and semiconductor-design
initiatives. These projects differ substantially in capital requirements,
location, technology, ownership structure, and exposure to sector-wide
financial conditions.

For banks and policy institutions, this creates a macro-prudential challenge.
Large-scale lending concentrated in a small number of firms, technologies,
or states may amplify financial vulnerability if sectoral credit conditions
deteriorate. At the same time, restricting credit purely on the basis of
project size could inhibit strategically important industrial development.

Conventional supervised credit-risk models typically require observed
borrower-level outcomes such as defaults, repayment histories, credit ratings,
loan delinquencies, or non-performing-asset events. Such data were not
available at sufficient project-level coverage for India's emerging
semiconductor ecosystem.

This research therefore asks a different question:

**How can machine-learning-based structural analysis, RBI-linked stress
testing, and constrained portfolio allocation be combined to support
macro-prudential semiconductor credit decisions when borrower-level default
labels are unavailable?**

The study deliberately separates structural segmentation from financial
vulnerability. Clusters are used to characterize ecosystem heterogeneity,
while the stress model evaluates relative exposure to adverse financial
conditions. A final optimization layer examines whether credit can be
distributed in a manner that reduces modelled portfolio stress while
maintaining project and geographic diversification.



## 2. Research Objectives

The study has five objectives:

1. Construct a verified project-level database of India's semiconductor
   manufacturing and semiconductor-design ecosystem.

2. Identify structural similarities and differences among semiconductor
   projects using unsupervised machine learning.

3. Develop an RBI-linked macro-prudential vulnerability framework for
   semiconductor manufacturing projects.

4. Evaluate how manufacturing-project vulnerability changes under
   progressively adverse stress scenarios.

5. Develop and test a constrained credit-allocation framework that balances
   vulnerability, economic scale, project diversification, and state-level
   concentration.



## 3. Data

The final analytical ecosystem contains 36 official semiconductor
projects. These consist of 12 manufacturing projects and 24 semiconductor
design projects.

Manufacturing observations include semiconductor fabs, OSAT/ATMP facilities,
advanced packaging, compound-semiconductor projects, and related manufacturing
activities. Semiconductor-design observations are drawn from projects under
the Design Linked Incentive framework.

Project-level variables include company, project scope, project type, state,
financial measure, technology characteristics, application categories,
technology-partner indicators, concentration measures, and within-scope
financial rankings.

Manufacturing observations are additionally linked to RBI Electronics-sector
credit indicators and banking NPA variables. These RBI observations are used
as macro-financial conditions and not as project-specific borrower outcomes.

A critical methodological distinction is maintained between manufacturing
investment and DLI project outlay. These variables represent different
financial concepts and are therefore normalized within project scope rather
than treated as directly equivalent measures of bank exposure.



## 4. Methodology

### 4.1 Structural Feature Engineering

Project features were constructed to represent four broad dimensions:
financial scale, geographic concentration, organizational concentration,
and technological/application characteristics.

Financial variables were ranked and normalized within project scope in order
to avoid treating manufacturing investment and design-project outlay as
directly equivalent quantities.

### 4.2 Principal Component Analysis

Standardized structural features were transformed using Principal Component
Analysis. Components were retained until at least 85% of cumulative variance
was explained.

### 4.3 K-Means Clustering

K-Means models were evaluated for multiple values of k. Model selection did
not rely solely on the silhouette coefficient. Calinski-Harabasz,
Davies-Bouldin, cluster-size constraints, hierarchical-clustering agreement,
and bootstrap stability were also evaluated.

The validated solution contained 6 clusters.

### 4.4 Hierarchical Validation

Ward hierarchical clustering was independently fitted to the PCA-transformed
data. Agreement between K-Means and hierarchical labels was evaluated using
the Adjusted Rand Index.

### 4.5 Macro-Prudential Stress Model

The manufacturing stress-testing framework uses six risk-direction
components:

- project financial scale,
- state-level financial concentration,
- Electronics-sector credit growth,
- Electronics-sector credit-growth volatility,
- gross-NPA growth,
- and NPA addition pressure.

All variables are transformed so that larger values represent greater
relative vulnerability.

The framework is deterministic and scenario-based. It is not trained against
a default target and therefore must not be interpreted as a probability of
default.

### 4.6 Stress Scenarios

Four states are evaluated:

- Baseline
- Mild stress
- Moderate stress
- Severe stress

Macro-financial components move progressively toward the adverse boundary
under increasing scenario severity, while structural project characteristics
remain unchanged.

### 4.7 Credit-Allocation Framework

Credit allocation combines a vulnerability-adjusted attractiveness signal
with project-scale information.

The preferred tested configuration assigns:

- 80% weight to vulnerability,
- 20% weight to economic scale,
- a 15% maximum project exposure,
- and a 35% maximum state exposure.

These are scenario-derived analytical parameters rather than regulatory
limits.

### 4.8 Sensitivity Analysis

A total of 162 policy configurations were evaluated by varying
credit budget assumptions, project exposure limits, state limits, minimum
allocations, and risk-versus-scale weights.

Spearman rank correlation was used to measure whether the relative allocation
ordering remained stable across these assumptions.



## 5. Results

### 5.1 Ecosystem Segmentation

The validated clustering solution identified 6 structural semiconductor
ecosystem segments.

The silhouette coefficient was 0.3351. This represents moderate
rather than strong geometric separation and therefore the clusters should be
interpreted as exploratory structural segments rather than discrete risk
classes.

Cross-method agreement was considerably stronger. The Adjusted Rand Index
between K-Means and Ward hierarchical clustering was
0.7909, indicating that the two independent methods produced
broadly similar partitions.

Bootstrap ARI was 0.5810, suggesting moderate stability under
resampling.

**Table 1. Cluster Validation Results**

|   ecosystem_projects |   selected_clusters |   silhouette_score |   hierarchical_ari |   bootstrap_ari | interpretation                                                                                         |
|---------------------:|--------------------:|-------------------:|-------------------:|----------------:|:-------------------------------------------------------------------------------------------------------|
|                   36 |                   6 |             0.3351 |             0.7909 |           0.581 | Moderately separated structural segmentation with strong cross-method agreement and moderate stability |

**Table 2. Cluster Distribution**

|   cluster |   projects |   share_pct |
|----------:|-----------:|------------:|
|         0 |          5 |     13.8889 |
|         1 |          6 |     16.6667 |
|         2 |          5 |     13.8889 |
|         3 |          3 |      8.3333 |
|         4 |         14 |     38.8889 |
|         5 |          3 |      8.3333 |

### 5.2 Manufacturing Stress Testing

The manufacturing sample contains 12 projects. Stress testing produced
progressively adverse portfolio-level vulnerability conditions across the
baseline, mild, moderate, and severe scenarios.

Mean vulnerability scores were:

- Baseline: 53.145
- Mild: 54.989
- Moderate: 57.756
- Severe: 62.367

The highest-ranked manufacturing project in the final robust vulnerability
framework was **Tata Electronics Private Limited**, associated with
**Semiconductor Fab** activity in **Gujarat**.

This ranking should not be interpreted as an assertion that the company is
likely to default. It indicates high relative exposure within the constructed
macro-prudential framework.

**Table 3. Stress-Scenario Results**

| scenario   |    mean |   median |   minimum |   maximum |     std |
|:-----------|--------:|---------:|----------:|----------:|--------:|
| baseline   | 53.1449 |  48.7406 |   31.8861 |   80.5503 | 12.9344 |
| mild       | 54.9893 |  50.4631 |   36.8101 |   82.4953 | 12.4629 |
| moderate   | 57.7559 |  53.0468 |   44.1961 |   85.4128 | 11.8885 |
| severe     | 62.3668 |  58.6562 |   52.5    |   90.2752 | 11.3416 |

**Table 4. Manufacturing Vulnerability Ranking**

|   robust_vulnerability_rank | company                                                    | project_type                      | state          |   investment_crore |   baseline_score |   severe_score |   relative_severe_increase_pct | ranking_stability   |
|----------------------------:|:-----------------------------------------------------------|:----------------------------------|:---------------|-------------------:|-----------------:|---------------:|-------------------------------:|:--------------------|
|                           1 | Tata Electronics Private Limited                           | Semiconductor Fab                 | Gujarat        |              91526 |          80.5503 |        90.2752 |                        12.073  | Highly Stable       |
|                           2 | Crystal Matrix Limited                                     | Compound Semiconductor Fab + ATMP | Gujarat        |               3068 |          66.1635 |        70.9853 |                         7.2877 | Highly Stable       |
|                           3 | Suchi Semicon Private Limited                              | OSAT                              | Gujarat        |                868 |          65.5618 |        70.3836 |                         7.3546 | Highly Stable       |
|                           4 | CG Power and Industrial Solutions Limited                  | OSAT                              | Gujarat        |               7584 |          57.5925 |        67.3174 |                        16.8856 | Highly Stable       |
|                           5 | Kaynes Technology India Limited                            | OSAT                              | Gujarat        |               3307 |          56.4228 |        66.1476 |                        17.2356 | Highly Stable       |
|                           6 | Tata Electronics Private Limited                           | OSAT                              | Assam          |              27120 |          51.0815 |        60.8063 |                        19.0379 | Highly Stable       |
|                           7 | Micron Technology Inc.                                     | ATMP                              | Gujarat        |              22516 |          31.8861 |        56.5061 |                        77.2121 | Weight Sensitive    |
|                           7 | Vama Sundari Investments (Delhi) Private Limited / Foxconn | OSAT                              | Uttar Pradesh  |               3706 |          46.3997 |        53.8997 |                        16.1639 | Highly Stable       |
|                           9 | SiCSem Private Limited                                     | Compound Semiconductor Fab + ATMP | Odisha         |               2066 |          45.9865 |        53.4865 |                        16.3091 | Highly Stable       |
|                          10 | 3D Glass Solutions Inc.                                    | Advanced Packaging                | Odisha         |               1943 |          45.9528 |        53.4528 |                        16.3211 | Highly Stable       |
|                          11 | Advanced System in Package Technologies Private Limited    | OSAT                              | Andhra Pradesh |                480 |          45.1416 |        52.6416 |                        16.6144 | Highly Stable       |
|                          12 | Continental Device India Private Limited                   | Semiconductor Manufacturing       | Punjab         |                117 |          45      |        52.5    |                        16.6667 | Highly Stable       |

### 5.3 Credit Allocation

The constrained allocation framework was tested across
162 alternative policy configurations.

The mean pairwise Spearman rank correlation across allocation scenarios was
0.8918. This indicates high stability of the relative allocation
ordering under changes in the modelling assumptions.

The preferred specification places 80% weight on relative
vulnerability and 20% on economic scale.

The configuration also limits individual-project exposure to
15% and state concentration to
35%.

Relative to investment-proportional allocation, the preferred configuration
reduced the model's portfolio stress index by
23.70%.

Importantly, this percentage represents a reduction in the constructed
stress index. It does not represent a reduction in observed defaults,
non-performing assets, or monetary losses.

**Table 5. Credit-Allocation Policy Result**

|   policy_scenarios_tested |   recommended_risk_weight |   recommended_scale_weight |   max_project_share |   max_state_share |   minimum_project_share |   portfolio_stress_index |   stress_reduction_pct |   mean_spearman_rank_correlation | ranking_robustness   |
|--------------------------:|--------------------------:|---------------------------:|--------------------:|------------------:|------------------------:|-------------------------:|-----------------------:|---------------------------------:|:---------------------|
|                       162 |                       0.8 |                        0.2 |                0.15 |              0.35 |                    0.01 |                   58.684 |                 23.705 |                           0.8918 | HIGH                 |

**Table 6. Allocation Robustness**

|   robust_allocation_rank | company                                                    |   mean_allocation_share |   mean_allocation_rank |   best_allocation_rank |   worst_allocation_rank |   rank_range | allocation_stability   |
|-------------------------:|:-----------------------------------------------------------|------------------------:|-----------------------:|-----------------------:|------------------------:|-------------:|:-----------------------|
|                        1 | Vama Sundari Investments (Delhi) Private Limited / Foxconn |                  0.1069 |                 1.7778 |                      1 |                       3 |            2 | Highly Stable          |
|                        2 | SiCSem Private Limited                                     |                  0.1042 |                 3      |                      2 |                       4 |            2 | Highly Stable          |
|                        3 | Micron Technology Inc.                                     |                  0.1019 |                 3.1111 |                      1 |                       7 |            6 | Policy Sensitive       |
|                        4 | 3D Glass Solutions Inc.                                    |                  0.1039 |                 4      |                      3 |                       5 |            2 | Highly Stable          |
|                        5 | Tata Electronics Private Limited                           |                  0.1033 |                 4.3333 |                      1 |                       7 |            6 | Policy Sensitive       |
|                        6 | Advanced System in Package Technologies Private Limited    |                  0.097  |                 5.3333 |                      4 |                       6 |            2 | Highly Stable          |
|                        7 | Continental Device India Private Limited                   |                  0.0885 |                 6.8889 |                      5 |                       9 |            4 | Moderately Stable      |
|                        8 | CG Power and Industrial Solutions Limited                  |                  0.0726 |                 7.7778 |                      7 |                       8 |            1 | Highly Stable          |
|                        9 | Kaynes Technology India Limited                            |                  0.0704 |                 8.7778 |                      8 |                       9 |            1 | Highly Stable          |
|                       10 | Crystal Matrix Limited                                     |                  0.0597 |                10      |                     10 |                      10 |            0 | Highly Stable          |
|                       11 | Suchi Semicon Private Limited                              |                  0.0538 |                11.3333 |                     11 |                      12 |            1 | Highly Stable          |
|                       12 | Tata Electronics Private Limited                           |                  0.0377 |                11.6667 |                     11 |                      12 |            1 | Highly Stable          |



## 6. Discussion

The empirical results support three main conclusions.

First, India's semiconductor ecosystem is structurally heterogeneous.
The 6-cluster solution demonstrates that manufacturing and design projects
cannot be treated as a homogeneous policy portfolio. Differences in project
scale, technology, application, geographic concentration, and organizational
structure create multiple identifiable ecosystem segments.

Second, structural importance and financial vulnerability are not equivalent.
A project may be strategically important or economically large while also
creating greater portfolio concentration. For this reason, the study does not
use cluster membership as a direct measure of credit risk.

Third, portfolio construction matters materially. Investment-proportional
lending tends to concentrate financing in the largest capital projects.
The stress-aware allocation framework instead introduces a balance between
economic scale and relative vulnerability.

The 23.70% decline in the constructed portfolio stress
index indicates that diversification constraints and vulnerability-aware
allocation can materially alter the portfolio's modelled exposure to adverse
conditions.

The high mean Spearman correlation of 0.8918 is particularly
important. The policy ordering does not disappear when individual assumptions
are changed. This suggests that the core allocation result is not solely a
consequence of one arbitrarily selected set of weights.



## 7. Policy Implications

The framework suggests several implications for financial institutions and
industrial-policy authorities.

### 7.1 Avoid Purely Size-Based Credit Allocation

Project size is economically relevant but should not be the only determinant
of financing. Large projects can create disproportionate single-name and
geographic concentration.

### 7.2 Integrate Sector-Level Macro Indicators

RBI sectoral credit growth, credit volatility, and banking NPA dynamics can
provide useful macro-financial context even when project-specific default
data are unavailable.

### 7.3 Apply Geographic Concentration Controls

Semiconductor projects are geographically concentrated in a limited number
of states. Portfolio-level state exposure should therefore be evaluated
alongside individual-company exposure.

### 7.4 Use Stress Testing Before Credit Expansion

Credit-allocation decisions should be evaluated under adverse scenarios
rather than relying exclusively on current sectoral conditions.

### 7.5 Preserve Human and Institutional Review

The framework is intended as a decision-support system. Final credit decisions
would still require borrower-level financial statements, leverage, collateral,
cash-flow projections, sponsor quality, project implementation progress,
technology risk, and lender due diligence.



## 8. Limitations

The study has several important limitations.

- **No observed project-level default/NPA target**: Supervised probability-of-default modelling was not methodologically justified. Mitigation: Used unsupervised segmentation, deterministic stress testing, and sensitivity analysis instead.
- **Small manufacturing sample**: Only 12 official manufacturing observations are available. Mitigation: Avoided high-dimensional supervised ML and used transparent relative vulnerability analysis.
- **RBI banking variables are sector-level**: They do not represent actual project-specific bank exposure. Mitigation: Used them strictly as macro-prudential stress channels.
- **Credit allocation is hypothetical**: The model does not reproduce actual bank lending decisions. Mitigation: All budgets and concentration limits are explicitly treated as policy scenarios.
- **Cluster separation is moderate**: Clusters should not be interpreted as perfectly distinct classes. Mitigation: Validated with hierarchical agreement and bootstrap stability.

The most important limitation is the absence of a sufficiently broad observed
project-level credit-outcome target. For this reason, the study deliberately
does not report ROC-AUC, accuracy, F1 score, predicted default probabilities,
or expected-loss estimates.

The small manufacturing sample also limits statistical generalization.
The results should therefore be interpreted as a policy-oriented analytical
framework rather than a fully calibrated banking credit-risk model.



## 9. Conclusion

This study develops a hybrid machine-learning and macro-prudential framework
for evaluating India's emerging semiconductor ecosystem under conditions of
limited borrower-level credit data.

Rather than constructing an artificial default label, the methodology
separates the problem into three analytical layers.

First, PCA and validated clustering identify structural heterogeneity across
36 semiconductor ecosystem projects.

Second, an RBI-linked stress-testing framework evaluates relative
macro-prudential vulnerability across 12 manufacturing projects.

Third, a constrained allocation framework examines how credit can be
distributed while balancing vulnerability, economic scale, project
concentration, and geographic concentration.

The preferred policy configuration was robust across 162
alternative scenarios, with a mean pairwise Spearman correlation of
0.8918. It reduced the modelled portfolio stress index by
23.70% relative to investment-proportional allocation.

The key contribution of the study is therefore not a claim to predict actual
semiconductor defaults. Instead, it demonstrates how verified project data,
sectoral banking indicators, interpretable machine learning, scenario stress
testing, and constrained allocation can be combined into a transparent
decision-support framework for semiconductor credit policy.

Future research should incorporate borrower-level debt, credit ratings,
cash-flow information, implementation milestones, and observed repayment or
default outcomes as these data become available.



## Appendix A — Claims That Are Safe to Use

- The ecosystem contains 36 verified analytical project observations.
- Structural clustering produced six validated exploratory segments.
- Cluster separation is moderate, not strong.
- K-Means and hierarchical clustering show strong agreement.
- Manufacturing stress scores represent relative vulnerability.
- The vulnerability score is not a probability of default.
- RBI indicators represent macro-financial conditions, not project-specific NPAs.
- Credit-allocation budgets are hypothetical scenario parameters.
- The policy model does not estimate the optimal aggregate amount of bank lending.
- Stress reduction refers to the modelled portfolio stress index.
- The allocation framework should be treated as decision support rather than an
  automated lending rule.
