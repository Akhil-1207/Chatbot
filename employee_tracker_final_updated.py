import streamlit as st
import pandas as pd
import plotly.express as px
import uuid
from streamlit_autorefresh import st_autorefresh

# Set page configuration with a custom background
st.set_page_config(page_title="Employee Performance Dashboard", layout="wide")
st.markdown(
    """
    <style>
    .reportview-container {
        background: #F5F5F5;
    }
    .sidebar .sidebar-content {
        background: #2E2E2E;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Employee Performance Dashboard")
st.markdown("Interactive visualizations of employee performance metrics.")

# Load data from Google Sheets
sheet_url = "https://docs.google.com/spreadsheets/d/1OxU_4C8zAp_3sqcmj2dnn4YB7N6xcI6PUPLWSG-yl4E/export?format=csv"
df = pd.read_csv(sheet_url)

# Preprocessing
df['Hire_Date'] = pd.to_datetime(df['Hire_Date'], errors='coerce')
df['Years_At_Company'] = (pd.Timestamp.now() - df['Hire_Date']).dt.days / 365.25
df['Performance_Level'] = df['Performance_Score'].apply(lambda x: 'Low' if x < 3 else 'Medium' if x == 3 else 'High')
df['Satisfaction_Level'] = df['Employee_Satisfaction_Score'].apply(lambda x: 'Low' if x < 3 else 'Medium' if x == 3 else 'High')

def retention_level(index):
    if index < 0.8:
        return 'Low'
    elif 0.8 <= index < 1.5:
        return 'Medium'
    else:
        return 'High'

df['Retention_Risk_Level'] = df['Retension risk index'].apply(retention_level)

def remote_category(val):
    if val == 0:
        return 'Work From Office'
    elif val == 100:
        return 'Work From Home'
    else:
        return 'Hybrid'

df['Remote_Work_Category'] = df['Remote_Work_Frequency'].apply(remote_category)

# Sidebar filters
st.sidebar.header("Filters")
departments = df['Department'].dropna().unique().tolist()
job_titles = df['Job_Title'].dropna().unique().tolist()
remote_options = ['All', 'Work From Home', 'Work From Office', 'Hybrid']
employee_ids = ['All'] + df['Employee_ID'].dropna().astype(str).unique().tolist()

selected_employee = st.sidebar.selectbox("Select Employee ID", employee_ids)
selected_department = st.sidebar.selectbox("Select Department", ["All"] + departments)
selected_job = st.sidebar.selectbox("Select Job Title", ["All"] + job_titles)
selected_remote = st.sidebar.selectbox("Select Remote Work Type", remote_options)
date_range = st.sidebar.date_input("Filter by Hire Date Range", [df['Hire_Date'].min(), df['Hire_Date'].max()])

# Apply filters
filtered_df = df.copy()
if selected_employee != "All":
    filtered_df = filtered_df[filtered_df['Employee_ID'] == selected_employee]
if selected_department != "All":
    filtered_df = filtered_df[filtered_df['Department'] == selected_department]
if selected_job != "All":
    filtered_df = filtered_df[filtered_df['Job_Title'] == selected_job]
if selected_remote != "All":
    filtered_df = filtered_df[filtered_df['Remote_Work_Category'] == selected_remote]
if len(date_range) == 2:
    filtered_df = filtered_df[(filtered_df['Hire_Date'] >= pd.to_datetime(date_range[0])) &
                              (filtered_df['Hire_Date'] <= pd.to_datetime(date_range[1]))]

# KPI Cards
remote_efficiency_column = None
for col in df.columns:
    if col.lower().replace(" ", "_") == 'remote_work_efficiency':
        remote_efficiency_column = col
        break

if remote_efficiency_column:
    remote_work_efficiency_avg = filtered_df[remote_efficiency_column].mean() if not filtered_df.empty else 0
else:
    st.warning("Remote Work Efficiency column not found in the Google Sheet.")
    remote_work_efficiency_avg = 0

productivity_avg = filtered_df['Productivity score'].mean() if not filtered_df.empty else 0

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
        <div style="background-color:black; padding:20px; border-radius:10px">
            <h3 style="color:white; text-align:center;">Remote Work Efficiency</h3>
            <h1 style="color:white; text-align:center;">{remote_work_efficiency_avg:.2f}</h1>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div style="background-color:black; padding:20px; border-radius:10px">
            <h3 style="color:white; text-align:center;">Productivity Score</h3>
            <h1 style="color:white; text-align:center;">{productivity_avg:.2f}</h1>
        </div>
    """, unsafe_allow_html=True)

# First row of charts
st.subheader("Performance Overview")
col3, col4 = st.columns(2)

with col3:
    # Remote Work Efficiency by Department Chart
    st.markdown("**Remote Work Efficiency by Department**")
    remote_efficiency = filtered_df.groupby(['Department', 'Remote_Work_Category'])['Productivity score'].mean().reset_index()
    fig_remote = px.bar(remote_efficiency, x='Department', y='Productivity score', color='Remote_Work_Category',
                        barmode='group', color_discrete_map={'Work From Home': '#1E90FF', 'Work From Office': '#696969', 'Hybrid': '#228B22'})
    fig_remote.update_traces(marker=dict(line=dict(color='#000000', width=1)))
    fig_remote.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=20, r=20, t=30, b=20))
    fig_remote.update_yaxes(range=[0, filtered_df['Productivity score'].max() * 1.1 if not filtered_df.empty else 5])
    st.plotly_chart(fig_remote, use_container_width=True)

with col4:
    # Treemap
    st.markdown("**Performance Level Distribution by Job Title**")
    tree_data = filtered_df.groupby(['Job_Title', 'Performance_Level'])['Employee_ID'].count().reset_index()
    tree_data.rename(columns={'Employee_ID': 'Number_of_Employees'}, inplace=True)
    fig_tree = px.treemap(tree_data, path=['Job_Title', 'Performance_Level'], values='Number_of_Employees',
                          color='Performance_Level', color_discrete_map={'Low': '#FF4040', 'Medium': '#FFA500', 'High': '#228B22'})
    fig_tree.update_traces(hovertemplate='%{label}<br>Count: %{value}', textinfo="label+value+percent parent")
    fig_tree.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_tree, use_container_width=True)

# Second row of charts
st.subheader("Retention and Work Type")
col5, col6 = st.columns(2)

with col5:
    # Retention Risk Bar Chart
    st.markdown("**Employee Count by Retention Risk Level and Job Title**")
    retention_count = filtered_df.groupby(['Job_Title', 'Retention_Risk_Level'])['Employee_ID'].count().reset_index()
    retention_count.rename(columns={'Employee_ID': 'Number_of_Employees'}, inplace=True)
    fig_ret = px.bar(retention_count, x='Job_Title', y='Number_of_Employees', color='Retention_Risk_Level',
                     color_discrete_map={'Low': '#8B0000', 'Medium': '#FFA500', 'High': '#006400'})
    fig_ret.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_ret, use_container_width=True)

with col6:
    # Remote Work Pie Chart
    st.markdown("**Remote Work Type Distribution**")
    remote_data = filtered_df['Remote_Work_Category'].value_counts().reset_index()
    remote_data.columns = ['Remote_Work_Category', 'Count']
    fig_pie = px.pie(remote_data, names='Remote_Work_Category', values='Count',
                     color_discrete_map={'Work From Home': '#1E90FF', 'Work From Office': '#696969', 'Hybrid': '#228B22'})
    fig_pie.update_traces(hovertemplate='%{label}: %{value} employees (%{percent})', textposition='inside',
                          textinfo='percent+label')
    fig_pie.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_pie, use_container_width=True)

# Third row: Satisfaction Chart only
st.subheader("Employee Satisfaction")
# Center the chart by using a single column with padding
st.markdown("**Average Employee Satisfaction by Department**")
sat_avg = filtered_df.groupby('Department')['Employee_Satisfaction_Score'].mean().reset_index()
fig_sat = px.bar(sat_avg, x='Department', y='Employee_Satisfaction_Score',
                 color='Department', color_discrete_sequence=px.colors.qualitative.Plotly)
fig_sat.update_traces(marker=dict(line=dict(color='#000000', width=1)))
fig_sat.update_yaxes(range=[0, 5])
fig_sat.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
st.plotly_chart(fig_sat, use_container_width=True)

# Performance Trend Line Chart
st.subheader("Performance Score Trend by Years at Company")
filtered_df['Years_Bin'] = pd.cut(filtered_df['Years_At_Company'], bins=10).apply(lambda x: x.mid)
trend_data = filtered_df.groupby(['Years_Bin', 'Job_Title'])['Performance_Score'].mean().reset_index()
fig_line = px.line(trend_data, x='Years_Bin', y='Performance_Score', color='Job_Title')
fig_line.update_traces(mode='lines+markers')
fig_line.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
st.plotly_chart(fig_line, use_container_width=True)

# Employee Details Table
st.subheader("Employee Details")
details_columns = ['Employee_ID', 'Department', 'Job_Title', 'Performance_Level',
                   'Satisfaction_Level', 'Remote_Work_Category', 'Retention_Risk_Level']
st.dataframe(filtered_df[details_columns], use_container_width=True, height=200)

# Auto-refresh
st_autorefresh(interval=60000, key="refresh")

# Data Alerts
st.sidebar.header("Data Alerts")
alert_option = st.sidebar.selectbox("Show Data Alerts", ["None", "Critical Alerts"])

if alert_option == "Critical Alerts":
    alerts_df = filtered_df[(filtered_df["Satisfaction_Level"] == "Low") & (filtered_df["Retention_Risk_Level"] == "High")]
    departments_with_alerts = alerts_df['Department'].dropna().unique().tolist()
    
    if departments_with_alerts:
        selected_dept = st.sidebar.selectbox("Select Department for Alerts", ["All"] + departments_with_alerts)
        dept_alerts = alerts_df[alerts_df['Department'] == selected_dept] if selected_dept != "All" else alerts_df
        
        if not dept_alerts.empty:
            st.sidebar.markdown("### Alert Details")
            alert_indices = list(dept_alerts.index)
            selected_index = st.sidebar.slider("Select Employee Alert", 0, len(alert_indices) - 1, 0)
            alert = dept_alerts.iloc[selected_index]
            st.error(f"🚨 Alert: Employee {alert['Employee_ID']} from {alert['Department']} has Low Satisfaction and High Retention Risk (Job Title: {alert['Job_Title']})")