# Streamlit Community Cloud Deployment

## Deployment type

Zero-cost research / bank-pilot prototype.

This deployment must not be represented as a production-validated
bank credit model.

---

## GitHub repository

Deploy from the existing Semiconductor Credit Risk ML repository.

Branch:

main

Entrypoint:

app/community_main.py

---

## Community Cloud

Open:

share.streamlit.io

Choose:

Create app

Then select:

- Existing GitHub repository
- Branch: main
- Main file path: app/community_main.py

---

## Privacy

For mentor / panel / bank demonstrations, configure the application as:

Only specific people can view this app

Invite authorized reviewers through Streamlit Community Cloud.

---

## Secrets

Do not commit:

.streamlit/secrets.toml

Any real secrets must be entered through:

App Settings -> Secrets

---

## Updates

Push updated project files to the main GitHub branch.

Community Cloud will redeploy from the updated repository.

---

## Security boundary

Community Cloud access control is sufficient for an academic or
controlled demonstration.

It must not be treated as the final hosting architecture for
confidential bank customer data.

---

## Model boundary

The application:

- does not estimate regulatory PD;
- does not estimate LGD;
- does not estimate EAD;
- does not calculate regulatory ECL;
- does not automatically approve or reject credit.

Human credit judgement remains mandatory.
