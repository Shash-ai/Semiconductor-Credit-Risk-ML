# Cloud-safe repository root
PROJECT_ROOT = Path(__file__).resolve().parents[1]

from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
st.markdown('\n<style>\n\n.block-container {\n    padding-top: 1.4rem;\n    padding-bottom: 3rem;\n}\n\n[data-testid="stMetric"] {\n    border: 1px solid rgba(128,128,128,0.25);\n    border-radius: 12px;\n    padding: 14px;\n}\n\n[data-testid="stSidebar"] {\n    border-right: 1px solid rgba(128,128,128,0.20);\n}\n\n.dashboard-note {\n    opacity: 0.72;\n    font-size: 0.88rem;\n}\n\n</style>\n', unsafe_allow_html=True)
DEFAULT_ROOT = PROJECT_ROOT

def find_latest(root, filenames):
    if isinstance(filenames, str):
        filenames = [filenames]
    matches = []
    for filename in filenames:
        matches.extend(root.rglob(filename))
    matches = [p for p in matches if p.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)

@st.cache_data(show_spinner=False)
def read_csv_safe(path_string):
    if not path_string:
        return None
    path = Path(path_string)
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        df.columns = df.columns.astype(str).str.strip()
        return df
    except Exception:
        return None

def first_col(df, candidates):
    if df is None:
        return None
    for col in candidates:
        if col in df.columns:
            return col
    return None

def safe_text(value, default='Not available'):
    if pd.isna(value):
        return default
    value = str(value).strip()
    if value == '':
        return default
    return value

def numeric(df, column):
    if df is None or column not in df.columns:
        return pd.Series(np.nan, index=df.index if df is not None else [])
    return pd.to_numeric(df[column], errors='coerce')

def merge_optional(base, other, columns):
    if other is None:
        return base
    if 'project_id' not in other.columns:
        return base
    available = [c for c in columns if c in other.columns]
    if 'project_id' not in available:
        available.insert(0, 'project_id')
    temp = other[available].drop_duplicates(subset=['project_id'])
    new_columns = [c for c in temp.columns if c == 'project_id' or c not in base.columns]
    try:
        return base.merge(temp[new_columns], on='project_id', how='left', validate='one_to_one')
    except Exception:
        return base
st.sidebar.title('🏦 Credit Risk')
st.sidebar.caption('Indian Semiconductor Financing')
root_string = st.sidebar.text_input('Project folder', str(DEFAULT_ROOT))
if not PROJECT_ROOT.exists():
    st.error(f'Project folder not found:\n\n{PROJECT_ROOT}')
    st.stop()
bank_path = find_latest(PROJECT_ROOT, ['FINAL_Bank_Credit_Decision_Support_Full.csv', 'Bank_Credit_Decision_Support_Full.csv'])
committee_path = find_latest(PROJECT_ROOT, 'Final_Bank_Credit_Committee_Register.csv')
stress_path = find_latest(PROJECT_ROOT, ['Robust_Stress_Test_Full.csv', 'Final_Robust_Vulnerability_Ranking.csv', 'Final_Manufacturing_Model_Results.csv'])
scenario_path = find_latest(PROJECT_ROOT, 'Corrected_Stress_Scenario_Summary.csv')
monte_path = find_latest(PROJECT_ROOT, 'Monte_Carlo_Project_Risk_Summary.csv')
allocation_path = find_latest(PROJECT_ROOT, ['Project_Allocation_Stability.csv', 'Final_Project_Allocation_Robustness.csv'])
ecosystem_path = find_latest(PROJECT_ROOT, 'Semiconductor_Ecosystem_Master.csv')
manufacturing_path = find_latest(PROJECT_ROOT, 'Semiconductor_Master_Canonical.csv')
dli_path = find_latest(PROJECT_ROOT, 'DLI_Design_Projects_Canonical.csv')
bank = read_csv_safe(str(bank_path) if bank_path else None)
committee = read_csv_safe(str(committee_path) if committee_path else None)
stress = read_csv_safe(str(stress_path) if stress_path else None)
scenario = read_csv_safe(str(scenario_path) if scenario_path else None)
monte = read_csv_safe(str(monte_path) if monte_path else None)
allocation = read_csv_safe(str(allocation_path) if allocation_path else None)
ecosystem = read_csv_safe(str(ecosystem_path) if ecosystem_path else None)
manufacturing = read_csv_safe(str(manufacturing_path) if manufacturing_path else None)
dli = read_csv_safe(str(dli_path) if dli_path else None)
if bank is None:
    st.error('\nFinal bank-credit model could not be located.\n\nExpected one of:\n\n• FINAL_Bank_Credit_Decision_Support_Full.csv\n\n• Bank_Credit_Decision_Support_Full.csv\n')
    st.stop()
if 'project_id' not in bank.columns:
    st.error('Final bank model does not contain project_id.')
    st.stop()
dashboard = bank.copy()
dashboard = merge_optional(dashboard, stress, ['project_id', 'baseline_score', 'mild_score', 'moderate_score', 'severe_score', 'robust_vulnerability_rank'])
dashboard = merge_optional(dashboard, monte, ['project_id', 'median_simulated_score', 'mean_simulated_score', 'p90_score', 'p95_score', 'p99_score', 'tail_risk_rank', 'probability_top_3', 'probability_top_5'])
dashboard = merge_optional(dashboard, allocation, ['project_id', 'robust_allocation_rank', 'mean_allocation_share', 'allocation_stability', 'rank_range'])
st.sidebar.divider()
filtered = dashboard.copy()
if 'state' in dashboard.columns:
    states = sorted(dashboard['state'].dropna().astype(str).unique())
    selected_states = st.sidebar.multiselect('State', states, default=states)
    if selected_states:
        filtered = filtered[filtered['state'].astype(str).isin(selected_states)]
if 'indicative_model_risk_grade' in dashboard.columns:
    available_grades = [grade for grade in ['A', 'B', 'C', 'D', 'E'] if grade in set(dashboard['indicative_model_risk_grade'].astype(str))]
    selected_grades = st.sidebar.multiselect('Indicative Grade', available_grades, default=available_grades)
    if selected_grades:
        filtered = filtered[filtered['indicative_model_risk_grade'].astype(str).isin(selected_grades)]
if 'early_warning_status' in dashboard.columns:
    available_ews = [status for status in ['GREEN', 'AMBER', 'RED'] if status in set(dashboard['early_warning_status'].astype(str))]
    selected_ews = st.sidebar.multiselect('Early Warning', available_ews, default=available_ews)
    if selected_ews:
        filtered = filtered[filtered['early_warning_status'].astype(str).isin(selected_ews)]
st.title('🏦 Semiconductor Bank Credit-Risk Dashboard')
st.caption('Machine-learning-enabled decision support for Indian semiconductor financing')
st.info('Research prototype — indicative grades are not probability-of-default estimates, official credit ratings or automated lending decisions.')
overview_tab, committee_tab, project_tab, stress_tab, monte_tab, allocation_tab, methodology_tab = st.tabs(['📊 Portfolio', '🏦 Credit Committee', '🔎 Project Analysis', '⚡ Stress Testing', '🎲 Monte Carlo', '💰 Allocation', '🧠 Methodology'])
with overview_tab:
    st.subheader('Portfolio Overview')
    investment_col = first_col(filtered, ['investment_crore'])
    if investment_col:
        total_investment = numeric(filtered, investment_col).sum()
    else:
        total_investment = np.nan
    high_monitoring = 0
    if 'monitoring_priority' in filtered.columns:
        high_monitoring = int(filtered['monitoring_priority'].astype(str).str.upper().eq('HIGH').sum())
    red_count = 0
    if 'early_warning_status' in filtered.columns:
        red_count = int(filtered['early_warning_status'].astype(str).str.upper().eq('RED').sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Bank Exposures', len(filtered))
    c2.metric('Project Investment', f'₹{total_investment:,.0f} Cr' if pd.notna(total_investment) else 'N/A')
    c3.metric('High Monitoring', high_monitoring)
    c4.metric('RED Warnings', red_count)
    st.divider()
    left, right = st.columns(2)
    with left:
        if 'indicative_model_risk_grade' in filtered.columns:
            grades = filtered['indicative_model_risk_grade'].astype(str).value_counts().reindex(['A', 'B', 'C', 'D', 'E'], fill_value=0).reset_index()
            grades.columns = ['Grade', 'Projects']
            fig = px.bar(grades, x='Grade', y='Projects', text_auto=True, title='Indicative Credit Grades')
            st.plotly_chart(fig, use_container_width=True)
    with right:
        if 'early_warning_status' in filtered.columns:
            ews = filtered['early_warning_status'].astype(str).value_counts().reindex(['GREEN', 'AMBER', 'RED'], fill_value=0).reset_index()
            ews.columns = ['Status', 'Projects']
            fig = px.bar(ews, x='Status', y='Projects', text_auto=True, title='Early-Warning System')
            st.plotly_chart(fig, use_container_width=True)
    if 'state' in filtered.columns and investment_col:
        state_data = filtered.copy()
        state_data['_investment'] = numeric(state_data, investment_col)
        state_data = state_data.groupby('state', as_index=False)['_investment'].sum().sort_values('_investment', ascending=False)
        fig = px.bar(state_data, x='state', y='_investment', title='Semiconductor Investment Exposure by State', labels={'state': 'State', '_investment': 'Investment (₹ crore)'})
        st.plotly_chart(fig, use_container_width=True)
with committee_tab:
    st.subheader('Credit Committee Decision Register')
    st.caption('Projects are shown with model-supported credit, exposure and monitoring guidance.')
    committee_source = committee.copy() if committee is not None else filtered.copy()
    committee_columns = ['credit_committee_review_rank', 'company', 'project_type', 'state', 'investment_crore', 'indicative_model_risk_grade', 'borrower_credit_strength_class', 'project_stress_vulnerability_class', 'portfolio_concentration_class', 'credit_posture', 'exposure_posture', 'monitoring_priority', 'early_warning_status', 'committee_review_category', 'primary_risk_drivers', 'primary_risk_mitigants']
    committee_columns = [col for col in committee_columns if col in committee_source.columns]
    if 'credit_committee_review_rank' in committee_source.columns:
        committee_source = committee_source.sort_values('credit_committee_review_rank')
    elif 'indicative_model_risk_grade' in committee_source.columns:
        order = {'E': 1, 'D': 2, 'C': 3, 'B': 4, 'A': 5}
        committee_source['_grade_order'] = committee_source['indicative_model_risk_grade'].astype(str).map(order).fillna(99)
        committee_source = committee_source.sort_values('_grade_order')
    st.dataframe(committee_source[committee_columns], use_container_width=True, hide_index=True)
    csv_data = committee_source[committee_columns].to_csv(index=False).encode('utf-8')
    st.download_button('⬇️ Download Committee Register', data=csv_data, file_name='Bank_Credit_Committee_Register.csv', mime='text/csv')
with project_tab:
    st.subheader('Individual Project Credit Assessment')
    project_labels = {}
    for _, item in dashboard.iterrows():
        company = safe_text(item.get('company'))
        project_type = safe_text(item.get('project_type'))
        label = f'{company} — {project_type}'
        if label in project_labels:
            label = f"{label} — {item['project_id']}"
        project_labels[label] = item['project_id']
    selected_project = st.selectbox('Select Project', sorted(project_labels.keys()))
    selected_id = project_labels[selected_project]
    selected_row = dashboard[dashboard['project_id'] == selected_id].iloc[0]
    st.markdown(f"## {safe_text(selected_row.get('company'))}")
    st.caption(f"{safe_text(selected_row.get('project_type'))} | {safe_text(selected_row.get('state'))}")
    a, b, c, d = st.columns(4)
    a.metric('Indicative Grade', safe_text(selected_row.get('indicative_model_risk_grade')))
    b.metric('Borrower Strength', safe_text(selected_row.get('borrower_credit_strength_class')))
    c.metric('Stress Vulnerability', safe_text(selected_row.get('project_stress_vulnerability_class')))
    d.metric('Early Warning', safe_text(selected_row.get('early_warning_status')))
    st.divider()
    left, right = st.columns(2)
    with left:
        st.markdown('### 🏦 Credit Decision')
        st.write('**Credit posture:**', safe_text(selected_row.get('credit_posture')))
        st.write('**Exposure posture:**', safe_text(selected_row.get('exposure_posture')))
        st.write('**Monitoring priority:**', safe_text(selected_row.get('monitoring_priority')))
        st.write('**Stress grade migration:**', safe_text(selected_row.get('stress_grade_migration')))
        st.write('**Portfolio concentration:**', safe_text(selected_row.get('portfolio_concentration_class')))
    with right:
        st.markdown('### 🔍 Explainability')
        st.write('**Primary risk drivers:**')
        st.write(safe_text(selected_row.get('primary_risk_drivers')))
        st.write('**Primary mitigants:**')
        st.write(safe_text(selected_row.get('primary_risk_mitigants')))
        st.write('**Credit information quality:**', safe_text(selected_row.get('credit_information_quality')))
        st.write('**External credit signal:**', safe_text(selected_row.get('external_credit_signal')))
    available_metrics = []
    metric_candidates = [('Project Stress', 'project_stress_vulnerability_score'), ('Borrower Strength', 'borrower_credit_strength_score'), ('Concentration', 'portfolio_concentration_signal_score'), ('P95 Tail Risk', 'p95_score')]
    for title, column in metric_candidates:
        if column in dashboard.columns and pd.notna(selected_row.get(column)):
            available_metrics.append((title, column))
    if available_metrics:
        st.divider()
        metric_boxes = st.columns(len(available_metrics))
        for box, (title, column) in zip(metric_boxes, available_metrics):
            try:
                value = float(selected_row[column])
                box.metric(title, f'{value:.2f}')
            except Exception:
                pass
with stress_tab:
    st.subheader('Macro-Financial Stress Testing')
    stress_columns = {'Baseline': 'baseline_score', 'Mild': 'mild_score', 'Moderate': 'moderate_score', 'Severe': 'severe_score'}
    available_stress = {scenario_name: column for scenario_name, column in stress_columns.items() if column in dashboard.columns}
    if len(available_stress) >= 2:
        company_options = sorted(dashboard['company'].dropna().astype(str).unique())
        stress_company = st.selectbox('Select company', company_options, key='stress_company')
        company_rows = dashboard[dashboard['company'].astype(str) == stress_company]
        if len(company_rows):
            stress_row = company_rows.iloc[0]
            chart_rows = []
            for scenario_name, column in available_stress.items():
                value = pd.to_numeric(stress_row.get(column), errors='coerce')
                if pd.notna(value):
                    chart_rows.append({'Scenario': scenario_name, 'Stress Score': float(value)})
            chart_df = pd.DataFrame(chart_rows)
            if len(chart_df):
                fig = px.line(chart_df, x='Scenario', y='Stress Score', markers=True, title=f'Stress Migration — {stress_company}')
                st.plotly_chart(fig, use_container_width=True)
                if 'Baseline' in set(chart_df['Scenario']) and 'Severe' in set(chart_df['Scenario']):
                    baseline = float(chart_df.loc[chart_df['Scenario'] == 'Baseline', 'Stress Score'].iloc[0])
                    severe = float(chart_df.loc[chart_df['Scenario'] == 'Severe', 'Stress Score'].iloc[0])
                    increase = severe - baseline
                    c1, c2, c3 = st.columns(3)
                    c1.metric('Baseline', f'{baseline:.2f}')
                    c2.metric('Severe', f'{severe:.2f}')
                    c3.metric('Stress Increase', f'{increase:+.2f}')
    elif scenario is not None:
        st.info('Project-level stress scores were not located. Showing portfolio scenario summary instead.')
        st.dataframe(scenario, use_container_width=True, hide_index=True)
    else:
        st.warning('Detailed stress-test output was not found.')
with monte_tab:
    st.subheader('Monte Carlo Tail-Risk Analysis')
    if monte is None:
        st.warning('Monte Carlo project summary was not found.')
    else:
        company_col = first_col(monte, ['company'])
        p95_col = first_col(monte, ['p95_score', 'p95_simulated_score'])
        if company_col and p95_col:
            monte_chart = monte.copy()
            monte_chart[p95_col] = pd.to_numeric(monte_chart[p95_col], errors='coerce')
            monte_chart = monte_chart.dropna(subset=[p95_col]).sort_values(p95_col, ascending=False)
            fig = px.bar(monte_chart, x=company_col, y=p95_col, title='95th Percentile Tail Vulnerability', labels={company_col: 'Company', p95_col: 'P95 Risk Score'})
            st.plotly_chart(fig, use_container_width=True)
        monte_columns = [col for col in ['company', 'tail_risk_rank', 'median_simulated_score', 'mean_simulated_score', 'p90_score', 'p95_score', 'p99_score', 'probability_top_3', 'probability_top_5'] if col in monte.columns]
        st.dataframe(monte[monte_columns] if monte_columns else monte, use_container_width=True, hide_index=True)
with allocation_tab:
    st.subheader('Credit Allocation & Concentration')
    if allocation is not None:
        company_col = first_col(allocation, ['company'])
        allocation_col = first_col(allocation, ['mean_allocation_share', 'recommended_allocation_share'])
        if company_col and allocation_col:
            allocation_chart = allocation.copy()
            allocation_chart[allocation_col] = pd.to_numeric(allocation_chart[allocation_col], errors='coerce')
            allocation_chart = allocation_chart.dropna(subset=[allocation_col]).sort_values(allocation_col, ascending=False)
            fig = px.bar(allocation_chart, x=company_col, y=allocation_col, title='Recommended Credit Allocation Share', labels={company_col: 'Company', allocation_col: 'Allocation Share'})
            st.plotly_chart(fig, use_container_width=True)
        allocation_columns = [col for col in ['company', 'robust_allocation_rank', 'mean_allocation_share', 'allocation_stability', 'rank_range'] if col in allocation.columns]
        st.dataframe(allocation[allocation_columns] if allocation_columns else allocation, use_container_width=True, hide_index=True)
    elif 'portfolio_concentration_signal_score' in dashboard.columns:
        concentration_columns = [col for col in ['company', 'portfolio_concentration_signal_score', 'portfolio_concentration_class', 'exposure_posture'] if col in dashboard.columns]
        concentration = dashboard[concentration_columns].copy()
        concentration['portfolio_concentration_signal_score'] = pd.to_numeric(concentration['portfolio_concentration_signal_score'], errors='coerce')
        concentration = concentration.sort_values('portfolio_concentration_signal_score', ascending=False)
        fig = px.bar(concentration, x='company', y='portfolio_concentration_signal_score', title='Portfolio Concentration Signal')
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(concentration, use_container_width=True, hide_index=True)
    else:
        st.warning('Allocation output was not found.')
with methodology_tab:
    st.subheader('Research Framework')
    c1, c2, c3 = st.columns(3)
    c1.metric('Verified Ecosystem', len(ecosystem) if ecosystem is not None else 'N/A')
    c2.metric('Manufacturing Projects', len(manufacturing) if manufacturing is not None else len(bank))
    c3.metric('DLI Design Projects', len(dli) if dli is not None else 'N/A')
    architecture = pd.DataFrame([{'Layer': 'Structural ML', 'Method': 'PCA + validated clustering', 'Banking Purpose': 'Segment semiconductor exposures'}, {'Layer': 'Macro Stress', 'Method': 'Deterministic stress scenarios', 'Banking Purpose': 'Measure adverse-scenario vulnerability'}, {'Layer': 'Tail Risk', 'Method': 'Monte Carlo simulation', 'Banking Purpose': 'Assess severe-tail exposure'}, {'Layer': 'Borrower Fundamentals', 'Method': 'Verified financial evidence', 'Banking Purpose': 'Assess borrower strength'}, {'Layer': 'External Credit', 'Method': 'CRA/public evidence', 'Banking Purpose': 'Independent credit evidence'}, {'Layer': 'Portfolio', 'Method': 'Constrained allocation', 'Banking Purpose': 'Manage concentration'}, {'Layer': 'Bank Decision Support', 'Method': 'A–E + EWS', 'Banking Purpose': 'Credit review and monitoring'}])
    st.dataframe(architecture, use_container_width=True, hide_index=True)
    st.markdown('### Files Detected')
    detected_files = pd.DataFrame([{'Dataset': 'Final Bank Model', 'Status': 'FOUND' if bank_path else 'MISSING'}, {'Dataset': 'Credit Committee', 'Status': 'FOUND' if committee_path else 'MISSING'}, {'Dataset': 'Stress Testing', 'Status': 'FOUND' if stress_path else 'MISSING'}, {'Dataset': 'Monte Carlo', 'Status': 'FOUND' if monte_path else 'MISSING'}, {'Dataset': 'Allocation', 'Status': 'FOUND' if allocation_path else 'MISSING'}, {'Dataset': 'Ecosystem Master', 'Status': 'FOUND' if ecosystem_path else 'MISSING'}])
    st.dataframe(detected_files, use_container_width=True, hide_index=True)
    st.warning('\nMethodological boundary:\n\nThe framework does NOT estimate Probability of Default (PD),\nLoss Given Default (LGD), Exposure at Default (EAD),\nExpected Credit Loss (ECL), or actual future NPA probability.\n\nThe A–E grades are research decision-support categories.\n')
st.divider()
st.caption('Semiconductor Credit Risk ML • Bank Credit Decision-Support Research Prototype')
