# Model Card

## Project Title

**Optimizing Credit Allocation and Stress-Testing Bank Exposure Under Semicon 2.0:  
A Machine Learning Framework for Macro-Prudential Risk Management**

---

## 1. Model Purpose

This research prototype supports bank credit-risk assessment for India's semiconductor sector.

It is designed to help analysts:

- identify structurally similar semiconductor projects,
- assess relative project vulnerability,
- stress-test exposure under adverse macro-financial conditions,
- analyze borrower financial strength where verified data is available,
- evaluate portfolio concentration,
- support credit allocation,
- generate indicative credit-review signals,
- support monitoring and early-warning workflows.

---

## 2. Intended Users

Primary intended users:

- bank credit analysts,
- risk-management teams,
- credit committees,
- portfolio-risk teams,
- academic researchers,
- policy and sector-risk researchers.

---

## 3. Model Scope

The current research dataset includes:

- 12 semiconductor manufacturing projects,
- 24 semiconductor design/DLI projects,
- 36 verified ecosystem observations in total.

The bank-credit decision-support layer focuses primarily on the 12 manufacturing projects.

---

## 4. Analytical Architecture

The framework consists of:

1. Data cleaning and verification
2. Feature engineering
3. PCA dimensionality reduction
4. Validated clustering
5. Deterministic stress testing
6. Monte Carlo tail-risk analysis
7. Borrower financial evidence
8. External credit-rating evidence
9. Portfolio concentration analysis
10. Credit-allocation optimization
11. Indicative bank risk grading
12. Early-warning monitoring
13. Credit-committee decision support

---

## 5. Model Outputs

Main outputs include:

- structural cluster,
- relative vulnerability rank,
- severe-stress score,
- Monte Carlo P95 tail-risk score,
- borrower credit-strength signal,
- portfolio concentration signal,
- indicative A-E research grade,
- credit posture,
- exposure posture,
- monitoring priority,
- GREEN / AMBER / RED early-warning status.

---

## 6. Important Methodological Boundary

This framework does NOT estimate:

- Probability of Default (PD),
- Loss Given Default (LGD),
- Exposure at Default (EAD),
- Expected Credit Loss (ECL),
- actual future NPA probability.

The A-E grades are internal research decision-support categories only.

They are not official bank ratings or credit-rating-agency ratings.

---

## 7. Why Supervised Default Prediction Was Not Used

A reliable project-level historical default/non-default dataset was not available for the verified semiconductor observations.

Artificial default labels were intentionally not created.

The project therefore uses unsupervised machine learning, stress testing, and evidence-based decision support instead of presenting a statistically unsupported default classifier.

---

## 8. Model Validation

The framework includes:

- PCA explained variance review,
- silhouette analysis,
- hierarchical clustering agreement,
- bootstrap clustering stability,
- deterministic stress scenarios,
- Monte Carlo tail-risk analysis,
- cross-method rank comparison,
- allocation sensitivity testing,
- external borrower evidence where available,
- panel review.

---

## 9. Known Limitations

Key limitations include:

- small sector-specific sample size,
- incomplete borrower financial coverage,
- lack of historical project-level default outcomes,
- limited longitudinal project performance data,
- stress assumptions are analytical rather than regulatory scenarios,
- external credit evidence is only available for some entities,
- research grades are not calibrated against actual default frequencies.

---

## 10. Human Oversight

The system is not designed to autonomously approve or reject loans.

Final lending decisions must remain with qualified and authorized credit professionals.

---

## 11. Appropriate Use

Appropriate uses:

- exploratory credit-risk assessment,
- relative exposure comparison,
- stress-testing research,
- portfolio-concentration analysis,
- pilot credit-review support,
- academic research.

Inappropriate uses:

- automated sanction decisions,
- regulatory capital calculations,
- official PD estimation,
- official credit ratings,
- replacement of bank underwriting policy.

---

## 12. Current Status

**Research prototype / pre-pilot stage**

The next intended stage is controlled expert review and limited bank-pilot testing using non-production or anonymized data.