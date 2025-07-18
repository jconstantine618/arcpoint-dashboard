import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import openai

# --- CONFIG ---
st.set_page_config(page_title="Franchise Test Dashboard", layout="wide")

# --- CUSTOM STYLING ---
st.markdown("""
    <style>
    .stMultiSelect > div {
        max-width: 100% !important;
    }
    .stMultiSelect label, .stMultiSelect span {
        white-space: normal;
        word-break: break-word;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("Upload & Filters")
uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, engine="openpyxl")
    df = df[['Franchisee', 'Sub Client', 'test name', 'Lab Partner']].dropna(subset=['Franchisee', 'test name'])

    # --- Top 10 Franchisees by Default ---
    unique_tests = sorted(df['test name'].dropna().unique())
    unique_franchisees = sorted(df['Franchisee'].dropna().unique())
    top_10_franchisees = df['Franchisee'].value_counts().head(10).index.tolist()

    # --- Test Filter ---
    st.sidebar.markdown("### Filter by Test Type")
    selected_tests = st.sidebar.multiselect(
        "Select Test Types",
        options=unique_tests,
        default=unique_tests,
        format_func=lambda x: x
    )
    st.sidebar.caption(f"✅ {len(selected_tests)} test types selected")

    # --- Franchisee Filter ---
    st.sidebar.markdown("### Filter by Franchisee(s)")
    selected_franchisees = st.sidebar.multiselect(
        "Select Franchisee(s)",
        options=unique_franchisees,
        default=top_10_franchisees,
        format_func=lambda x: x
    )
    st.sidebar.caption(f"✅ {len(selected_franchisees)} franchisees selected")

    if st.sidebar.button("Run Report"):

        filtered_df = df[
            df['test name'].isin(selected_tests) & 
            df['Franchisee'].isin(selected_franchisees)
        ]

        # --- Franchisee Sample Volume ---
        st.header("Franchisee Sample Volume")
        volume_by_franchisee = filtered_df['Franchisee'].value_counts().reset_index()
        volume_by_franchisee.columns = ['Franchisee', 'Sample Volume']
        volume_by_franchisee = volume_by_franchisee.sort_values('Sample Volume', ascending=False)

        fig1, ax1 = plt.subplots(figsize=(10, 0.4 * len(volume_by_franchisee)))
        ax1.barh(volume_by_franchisee['Franchisee'], volume_by_franchisee['Sample Volume'], color='skyblue')
        ax1.set_xlabel("Sample Volume")
        ax1.set_title("Franchisee Sample Volume")
        ax1.invert_yaxis()
        ax1.tick_params(axis='y', labelsize=10)
        st.pyplot(fig1)

        # --- Most Common Tests ---
        st.header("Most Common Tests")
        test_counts = filtered_df['test name'].value_counts().head(15).sort_values(ascending=True)

        fig2, ax2 = plt.subplots(figsize=(10, 0.4 * len(test_counts)))
        ax2.barh(test_counts.index, test_counts.values, color='orange')
        ax2.set_xlabel("Frequency")
        ax2.set_title("Top 15 Most Common Tests")
        ax2.invert_yaxis()
        ax2.tick_params(axis='y', labelsize=10)
        st.pyplot(fig2)

        # --- Lab Partner Usage ---
        st.header("Lab Partner Usage")
        lab_counts = filtered_df['Lab Partner'].value_counts().sort_values(ascending=True)

        fig3, ax3 = plt.subplots(figsize=(10, 0.4 * len(lab_counts)))
        ax3.barh(lab_counts.index, lab_counts.values, color='green')
        ax3.set_xlabel("Sample Volume")
        ax3.set_title("Lab Partner Usage")
        ax3.invert_yaxis()
        ax3.tick_params(axis='y', labelsize=10)
        st.pyplot(fig3)

        # --- Sub Account vs Franchisee Analysis ---
        st.header("Sub Account vs Franchisee Match (Selected Tests)")
        temp = filtered_df.copy()
        temp['Franchisee_norm'] = temp['Franchisee'].str.lower().str.strip()
        temp['Sub_Client_norm'] = temp['Sub Client'].str.lower().str.strip()
        temp['Different'] = temp['Franchisee_norm'] != temp['Sub_Client_norm']
        diff_counts = temp['Different'].value_counts().rename({
            True: 'Sub Account ≠ Franchisee',
            False: 'Sub Account = Franchisee'
        })

        fig4, ax4 = plt.subplots()
        ax4.pie(diff_counts, labels=diff_counts.index, autopct='%1.1f%%', startangle=140)
        ax4.set_title("Sub Account vs Franchisee Distribution")
        ax4.axis('equal')
        st.pyplot(fig4)

# --- CHATBOT SECTION ---
st.sidebar.title("💬 Ask the Data")
st.sidebar.markdown("Chat with your uploaded data using GPT!")

openai_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")

if openai_key and uploaded_file:
    user_question = st.sidebar.text_area("Ask a question about the data:")

    if user_question:
        try:
            openai.api_key = openai_key
            sample_data = df.head(200).to_csv(index=False)
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
