import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import openai

# --- CONFIG ---
st.set_page_config(page_title="Franchise Test Dashboard", layout="wide")

# --- SIDEBAR ---
st.sidebar.title("Upload & Filters")

uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, engine="openpyxl")
    df = df[['Franchisee', 'Sub Client', 'test name', 'Lab Partner']].dropna(subset=['Franchisee', 'test name'])

    # Sidebar filters
    unique_tests = sorted(df['test name'].dropna().unique())
    unique_franchisees = sorted(df['Franchisee'].dropna().unique())

    selected_tests = st.sidebar.multiselect("Filter by Test Type", unique_tests, default=unique_tests)
    selected_franchisees = st.sidebar.multiselect("Filter by Franchisee(s)", unique_franchisees, default=unique_franchisees)

    if st.sidebar.button("Run Report"):
        filtered_df = df[df['test name'].isin(selected_tests) & df['Franchisee'].isin(selected_franchisees)]

        # --- CHARTS ---

        st.header("Franchisee Sample Volume")
        volume_by_franchisee = filtered_df['Franchisee'].value_counts().reset_index()
        volume_by_franchisee.columns = ['Franchisee', 'Sample Volume']
        volume_by_franchisee = volume_by_franchisee.sort_values('Sample Volume', ascending=False)
        st.bar_chart(volume_by_franchisee.set_index('Franchisee'))

        st.header("Most Common Tests")
        test_counts = filtered_df['test name'].value_counts().head(15).sort_values(ascending=False)
        st.bar_chart(test_counts)

        st.header("Lab Partner Usage")
        lab_counts = filtered_df['Lab Partner'].value_counts().sort_values(ascending=False)
        st.bar_chart(lab_counts)

        st.header("Sub Account vs Franchisee Match (Selected Tests)")
        temp = filtered_df.copy()
        temp['Franchisee_norm'] = temp['Franchisee'].str.lower().str.strip()
        temp['Sub_Client_norm'] = temp['Sub Client'].str.lower().str.strip()
        temp['Different'] = temp['Franchisee_norm'] != temp['Sub_Client_norm']
        diff_counts = temp['Different'].value_counts().rename({True: 'Sub Account ≠ Franchisee', False: 'Sub Account = Franchisee'})
        st.pie_chart(diff_counts)

# --- CHATBOT SECTION ---
st.sidebar.title("💬 Ask the Data")
st.sidebar.markdown("Chat with your uploaded data using GPT!")

openai_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")

if openai_key and uploaded_file:
    user_question = st.sidebar.text_area("Ask a question about the data:")

    if user_question:
        try:
            openai.api_key = openai_key
            sample_data = df.head(200).to_csv(index=False)  # Provide sample to GPT
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful data analyst assistant. Answer questions based on the uploaded lab testing dataset."},
                    {"role": "user", "content": f"Here is a sample of the data:\\n{sample_data}"},
                    {"role": "user", "content": user_question}
                ],
                temperature=0.3,
                max_tokens=500
            )
            st.sidebar.markdown("**Answer:**")
            st.sidebar.success(response.choices[0].message.content.strip())
        except Exception as e:
            st.sidebar.error(f"Error: {str(e)}")
