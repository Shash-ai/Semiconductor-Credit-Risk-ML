# 🏦 Semiconductor Credit Risk ML

## Optimizing Credit Allocation and Stress-Testing Bank Exposure Under Semicon 2.0

### A Machine Learning Framework for Macro-Prudential Risk Management

---

## 📌 Overview

India's semiconductor ecosystem is expanding rapidly through large-scale fabrication, OSAT/ATMP, advanced packaging, compound semiconductor, and semiconductor design investments.

These projects are highly capital-intensive and may require substantial financing from banks and financial institutions. Traditional credit assessment alone may not fully capture risks arising from project scale, geographic concentration, macroeconomic stress, sector-specific vulnerabilities, and portfolio concentration.

This project develops a **Machine Learning-enabled Bank Credit Decision-Support Framework** for analysing semiconductor financing exposure in India.

Rather than attempting to predict default without sufficient historical default data, the framework combines:

- Machine Learning
- Structural risk segmentation
- Macro-financial stress testing
- Monte Carlo tail-risk analysis
- Borrower financial evidence
- External credit-rating evidence
- Portfolio concentration analysis
- Credit allocation optimization
- Indicative credit-risk grading
- Early-warning monitoring

The objective is to help demonstrate how banks could analyse, stress-test, prioritize, and monitor semiconductor credit exposure under India's emerging semiconductor ecosystem.

---

# 🎯 Research Objective

The central research question is:

> **How can machine learning, macro-financial stress testing, and portfolio optimization be combined to support bank credit allocation and risk management for India's semiconductor sector?**

The framework aims to:

1. Build a verified dataset of Indian semiconductor projects.
2. Identify structural patterns using unsupervised machine learning.
3. Evaluate project vulnerability under adverse economic scenarios.
4. Measure severe-tail vulnerability using Monte Carlo simulation.
5. Incorporate borrower-level financial and external credit evidence.
6. Analyse portfolio and geographic concentration.
7. Optimize hypothetical bank credit allocation under risk constraints.
8. Translate analytical results into interpretable credit decision-support signals.
9. Develop an early-warning and monitoring framework.

---

# 📊 Dataset

The verified semiconductor ecosystem dataset contains:

| Dataset | Observations |
|---|---:|
| Semiconductor Manufacturing Projects | 12 |
| DLI Semiconductor Design Projects | 24 |
| **Total Verified Ecosystem** | **36** |

The manufacturing portfolio includes semiconductor fabs, OSAT/ATMP facilities, compound semiconductor projects, advanced packaging facilities, and related manufacturing investments.

Data verification was prioritized throughout the project.

No synthetic default labels were created, and unknown financial or project information was not intentionally fabricated.

---

# 🧠 Why Unsupervised Machine Learning?

A major limitation encountered during the research was the absence of a sufficiently large and reliable historical dataset containing observed:

- Defaults
- NPAs
- Non-default outcomes
- Loan repayment performance
- Recovery outcomes

Creating artificial default labels would make a supervised credit-default model statistically misleading.

Therefore, the project primarily uses **unsupervised machine learning and stress-based decision support**.

This allows the research to analyse structural vulnerability without falsely claiming to predict actual defaults.

---

# ⚙️ Methodology

The analytical architecture is:

```text
Verified Semiconductor Ecosystem
              ↓
      Data Engineering
              ↓
       PCA Dimension Reduction
              ↓
      Validated Clustering
              ↓
 Structural Risk Segmentation
              ↓
 Macro-Financial Stress Testing
              ↓
   Monte Carlo Tail-Risk Analysis
              ↓
 Borrower Fundamental Evidence
              ↓
 External Credit-Rating Evidence
              ↓
 Portfolio Concentration Analysis
              ↓
 Credit Allocation Optimization
              ↓
 Indicative Bank Credit Grades
              ↓
 Credit & Exposure Posture
              ↓
 Early-Warning System
              ↓
 Bank Credit Committee Support
```

---

# 🤖 Machine Learning Layer

## PCA

Principal Component Analysis (PCA) is used to reduce dimensionality while retaining the majority of information contained in the modelling features.

The final structural model retained approximately:

**85% of explained variance.**

---

## Clustering

Multiple cluster configurations were evaluated rather than arbitrarily selecting a value of K.

The validated clustering architecture produced:

- **Recommended K:** 6
- **Silhouette Score:** ~0.335
- **Hierarchical Agreement (ARI):** ~0.791
- **Bootstrap Stability ARI:** ~0.581

The clusters represent structural groups of semiconductor projects rather than default categories.

---

# ⚡ Macro-Financial Stress Testing

The 12 manufacturing projects are subjected to four stress environments:

- Baseline
- Mild
- Moderate
- Severe

The stress framework evaluates how relative vulnerability changes when adverse macro-financial conditions intensify.

The framework is designed for **relative vulnerability analysis**, not prediction of actual monetary credit losses.

---

# 🎲 Monte Carlo Tail-Risk Analysis

Deterministic stress scenarios are complemented by Monte Carlo simulation.

This enables the framework to evaluate uncertainty beyond a small number of predefined scenarios and analyse metrics such as:

- Median simulated vulnerability
- P90 vulnerability
- P95 vulnerability
- P99 vulnerability
- Tail-risk ranking
- Probability of appearing among the most vulnerable exposures

This provides an additional layer of robustness for stress analysis.

---

# 🏢 Borrower Credit Evidence

Project vulnerability and borrower creditworthiness are treated as separate concepts.

Where verified information is available, the framework incorporates borrower-level indicators such as:

- Profitability
- Leverage
- Liquidity
- Interest coverage
- Cash-flow strength
- External credit evidence

Missing borrower information is treated as an **information limitation**, rather than automatically assuming that the company is financially healthy.

---

# 💰 Credit Allocation Optimization

The framework evaluates hypothetical bank-credit allocation under constraints including:

- Total lending budget
- Maximum project exposure
- Maximum geographic/state exposure
- Minimum project allocation
- Risk versus scale preferences

A large sensitivity analysis was conducted across **162 policy scenarios**.

The allocation framework demonstrated high ranking consistency across alternative assumptions, with mean pairwise Spearman rank correlation of approximately:

**ρ = 0.892**

This suggests that the relative allocation recommendations are reasonably robust to changes in policy assumptions within the tested framework.

---

# 🏦 Bank Credit Decision-Support Layer

The analytical outputs are translated into bank-oriented decision-support signals.

Each manufacturing exposure can receive:

### Indicative Research Risk Grade

```text
A → Lower relative vulnerability
B → Moderate-low relative vulnerability
C → Moderate relative vulnerability
D → Elevated relative vulnerability
E → Higher relative vulnerability
```

These grades are **not official bank or credit-rating-agency ratings**.

The framework additionally generates:

- Borrower Credit Strength
- Project Stress Vulnerability
- Portfolio Concentration Signal
- Credit Posture
- Exposure Posture
- Monitoring Priority
- Primary Risk Drivers
- Risk Mitigants
- Stress Grade Migration

---

# 🚨 Early-Warning System

The project includes an interpretable monitoring framework:

```text
🟢 GREEN  → Standard monitoring

🟠 AMBER  → Enhanced monitoring

🔴 RED    → Priority credit review
```

The purpose is to translate quantitative risk analysis into signals that could be understood by a credit analyst or credit committee.

---

# 🏦 Credit Committee Framework

The final layer converts model outputs into a structured credit-review register.

It helps answer questions such as:

- Which projects require enhanced review?
- Which exposures are most vulnerable under severe stress?
- Where is portfolio concentration excessive?
- Which borrowers have insufficient credit information?
- Which exposures require stronger mitigants?
- Which projects require higher monitoring priority?

The framework therefore acts as **decision support**, while keeping the final lending decision with human credit professionals.

---

# 📊 Interactive Dashboard

An interactive **Streamlit dashboard** accompanies the analytical framework.

The dashboard contains:

- 📊 Portfolio Overview
- 🏦 Credit Committee Register
- 🔎 Individual Project Analysis
- ⚡ Stress Testing
- 🎲 Monte Carlo Analysis
- 💰 Credit Allocation
- 🧠 Methodology & Data Overview

To run the dashboard:

```bash
pip install -r requirements.txt
```

Then:

```bash
streamlit run 07_Dashboard/bank_credit_dashboard.py
```

---

# 🗂️ Repository Structure

```text
Semiconductor-Credit-Risk-ML/
│
├── 01_Raw_Data/
│
├── 02_Processed_Data/
│
├── 03_Modeling/
│
├── 04_Optimization/
│
├── 05_Final_Results/
│
├── 06_Research_Paper/
│
├── 07_Dashboard/
│   └── bank_credit_dashboard.py
│
├── 99_Audit/
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

# 🔬 Key Contributions

This project contributes an integrated framework combining:

### 1. Sector-Specific Credit Analytics

The framework is specifically designed around India's emerging semiconductor financing ecosystem.

### 2. Verified Project-Level Dataset

Manufacturing and semiconductor-design projects are maintained as distinct project categories.

### 3. Responsible ML Design

The project deliberately avoids constructing artificial default labels when reliable observed outcomes are unavailable.

### 4. Multi-Layer Risk Analysis

Risk is evaluated through structural, macroeconomic, borrower, tail-risk, and portfolio perspectives.

### 5. Portfolio Optimization

The project goes beyond ranking vulnerability by investigating how hypothetical bank capital could be allocated under concentration and risk constraints.

### 6. Explainable Decision Support

Model outputs are translated into interpretable credit grades, monitoring signals, risk drivers, and credit postures.

---

# ⚠️ Important Limitations

This project is an **academic research prototype**, not a production banking model.

The framework does **not** estimate:

- Probability of Default (PD)
- Loss Given Default (LGD)
- Exposure at Default (EAD)
- Expected Credit Loss (ECL)
- Actual future NPA probability

It also does not autonomously approve or reject loans.

A production-grade banking model would require substantially larger historical loan-level datasets containing actual repayment, default, recovery, collateral, and borrower information.

The A–E grades generated by this framework are therefore **indicative research categories only**.

---

# 🔮 Future Scope

Future extensions could include:

- Historical bank loan-performance data
- Supervised Probability-of-Default modelling
- PD/LGD/EAD architecture
- Expected Credit Loss modelling
- Dynamic borrower financial statements
- Real-time macroeconomic indicators
- Automated credit-rating monitoring
- Scenario-based portfolio loss estimation
- Explainable AI techniques such as SHAP
- Integration with bank credit-origination systems

With sufficient historical credit outcomes, the current framework could serve as the foundation for a fully supervised semiconductor credit-risk model.

---

# 🛠️ Technology Stack

```text
Python
Pandas
NumPy
Scikit-learn
SciPy
Matplotlib
Plotly
Streamlit
Jupyter Notebook
Git / GitHub
```

---

# 📚 Research Positioning

The project lies at the intersection of:

**Machine Learning × Banking × Credit Risk × Semiconductor Policy × Portfolio Optimization × Macro-Prudential Risk**

Rather than asking only:

> *Which semiconductor project is risky?*

the framework asks:

> **How should a bank identify, stress-test, allocate, monitor, and review credit exposure to a strategically important but capital-intensive emerging industry?**

---

# 📜 Disclaimer

This repository is intended for academic and research purposes.

Nothing in this repository constitutes financial advice, an official credit rating, an investment recommendation, or a lending recommendation.

All model-generated grades and decision-support outputs should be interpreted within the assumptions and limitations documented in the research.

---

## Project Status

**Technical modelling:** Completed  
**Bank decision-support framework:** Completed  
**Stress-testing framework:** Completed  
**Portfolio optimization:** Completed  
**Interactive dashboard:** Completed  
**Research paper:** In development
