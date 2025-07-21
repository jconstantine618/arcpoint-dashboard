import streamlit as st
import pandas as pd
import plotly.express as px
import openai
from streamlit_tags import st_tags

# --- CONFIG ---
st.set_page_config(page_title="Franchise Test Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- SIDEBAR ---
st.sidebar.title("Upload & Filters 📊")
uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"], help="Upload your 'june sample volume by location.xlsx' or similar Excel file.")

if uploaded_file:
    # Load data
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
        # Ensure essential columns exist and handle NaNs for core analysis
        required_columns = ['Franchisee', 'Sub Client', 'test name', 'Lab Partner']
        if not all(col in df.columns for col in required_columns):
            st.error(f"Error: Missing one or more required columns. Please ensure your file has columns: {', '.join(required_columns)}")
            st.stop()
        
        df = df[required_columns].dropna(subset=['Franchisee', 'test name'])
        
        if df.empty:
            st.warning("The uploaded file is empty or contains no valid data after filtering for Franchisee and Test Name.")
            st.stop()

    except Exception as e:
        st.error(f"Error loading file: {e}. Please ensure it's a valid Excel file.")
        st.stop()

    # --- Unique lists & defaults ---
    unique_tests = sorted(df['test name'].dropna().unique())
    unique_franchisees = sorted(df['Franchisee'].dropna().unique())

    # Get top N based on sample volume
    top_10_franchisees = df['Franchisee'].value_counts().head(10).index.tolist()
    top_10_tests = df['test name'].value_counts().head(10).index.tolist()

    st.sidebar.markdown("### 💉 Filter by Test Type")
    selected_tests = st_tags(
        label='Select Test Types',
        text='Type or pick from suggestions',
        value=top_10_tests,
        suggestions=unique_tests,
        maxtags=0,
        key='test_tags'
    )

    st.sidebar.markdown("### 🏥 Filter by Franchisee(s)")
    selected_franchisees = st_tags(
        label='Select Franchisees',
        text='Type or pick from suggestions',
        value=top_10_franchisees,
        suggestions=unique_franchisees,
        maxtags=0,
        key='franchisee_tags'
    )
    
    # Add a toggle for sub-account filter
    st.sidebar.markdown("### 👥 Filter by Sub-Account Usage")
    filter_sub_accounts = st.sidebar.checkbox("Show only tests done through Sub Accounts (where Franchisee ≠ Sub Client)", value=False)


    if st.sidebar.button("Run Report 🚀"):
        if not selected_tests or not selected_franchisees:
            st.warning("Please select at least one Test Type and one Franchisee to run the report.")
            st.stop()

        filtered_df = df[
            df['test name'].isin(selected_tests) &
            df['Franchisee'].isin(selected_franchisees)
        ].copy() # Use .copy() to avoid SettingWithCopyWarning
        
        # Apply sub-account filter if checked
        if filter_sub_accounts:
            filtered_df['Franchisee_norm'] = filtered_df['Franchisee'].astype(str).str.lower().str.strip()
            filtered_df['Sub_Client_norm'] = filtered_df['Sub Client'].astype(str).str.lower().str.strip()
            filtered_df = filtered_df[filtered_df['Franchisee_norm'] != filtered_df['Sub_Client_norm']]
            
            if filtered_df.empty:
                st.warning("No data found for the selected filters with the 'Sub Account ≠ Franchisee' condition.")
                st.stop()

        # --- Dashboard Content ---
        st.title("Franchise Performance Dashboard 📈")
        st.markdown("Dive into your franchisee data to uncover patterns and insights.")

        # --- Franchisee Sample Volume ---
        st.header("Franchisee Sample Volume")
        volume_by_franchisee = filtered_df['Franchisee'].value_counts().reset_index()
        volume_by_franchisee.columns = ['Franchisee', 'Sample Volume']
        volume_by_franchisee = volume_by_franchisee.sort_values('Sample Volume', ascending=True) # Sort ascending for Plotly bar chart
        
        fig1 = px.bar(
            volume_by_franchisee, 
            y='Franchisee', 
            x='Sample Volume', 
            orientation='h',
            title='Franchisee Sample Volume',
            labels={'Franchisee': 'Franchisee', 'Sample Volume': 'Total Sample Volume'},
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig1.update_layout(height=max(400, 30 * len(volume_by_franchisee)), showlegend=False) # Adjust height dynamically
        st.plotly_chart(fig1, use_container_width=True)

        # --- Most Common Tests (Top N configurable) ---
        st.header("Most Common Tests")
        top_n_tests = st.slider("Number of Top Tests to Display:", 5, 50, 15)
        test_counts = filtered_df['test name'].value_counts().head(top_n_tests).sort_values(ascending=True)

        fig2 = px.bar(
            test_counts, 
            y=test_counts.index, 
            x=test_counts.values, 
            orientation='h',
            title=f'Top {top_n_tests} Most Common Tests',
            labels={'y': 'Test Name', 'x': 'Frequency'},
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig2.update_layout(height=max(400, 30 * len(test_counts)), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

        # --- Lab Partner Usage ---
        st.header("Lab Partner Usage")
        lab_counts = filtered_df['Lab Partner'].value_counts().sort_values(ascending=True)

        fig3 = px.bar(
            lab_counts, 
            y=lab_counts.index, 
            x=lab_counts.values, 
            orientation='h',
            title='Lab Partner Usage',
            labels={'y': 'Lab Partner', 'x': 'Sample Volume'},
            color_discrete_sequence=px.colors.qualitative.Light
        )
        fig3.update_layout(height=max(400, 30 * len(lab_counts)), showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

        # --- Sub Account vs Franchisee Analysis ---
        st.header("Sub Account vs Franchisee Relationship")
        temp = filtered_df.copy()
        temp['Franchisee_norm'] = temp['Franchisee'].astype(str).str.lower().str.strip()
        temp['Sub_Client_norm'] = temp['Sub Client'].astype(str).str.lower().str.strip()
        temp['Sub_Account_Status'] = temp.apply(lambda row: 'Sub Account Used' if row['Franchisee_norm'] != row['Sub_Client_norm'] else 'Direct Account', axis=1)
        
        sub_account_counts = temp['Sub_Account_Status'].value_counts()

        fig4 = px.pie(
            values=sub_account_counts.values, 
            names=sub_account_counts.index, 
            title='Distribution of Sample Volume by Sub Account Status',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig4, use_container_width=True)

        # --- NEW: Franchisee Sample Volume by Test Type (Top N for selected franchisees) ---
        st.header("Franchisee Sample Volume by Top Test Types 🧪")
        st.markdown("Explore which test types contribute most to each franchisee's volume.")
        
        # Aggregate data for top tests per franchisee
        franchisee_test_volume = filtered_df.groupby(['Franchisee', 'test name']).size().reset_index(name='Sample Volume')
        
        # Get top N tests for each selected franchisee
        top_tests_per_franchisee = franchisee_test_volume.loc[franchisee_test_volume.groupby('Franchisee')['Sample Volume'].rank(method='first', ascending=False) <= 5] # Top 5 tests per franchisee

        if not top_tests_per_franchisee.empty:
            fig5 = px.bar(
                top_tests_per_franchisee,
                x='Sample Volume',
                y='Franchisee',
                color='test name',
                orientation='h',
                title='Franchisee Sample Volume by Test Type (Top 5 per Franchisee)',
                labels={'Franchisee': 'Franchisee', 'Sample Volume': 'Sample Volume', 'test name': 'Test Type'},
                height=max(500, 50 * len(selected_franchisees)),
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig5.update_layout(barmode='stack', yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("No data to display for Franchisee Sample Volume by Test Type with current filters.")

        # --- NEW: Franchisee Sample Volume by Sub Account Status and Test Type ---
        st.header("Franchisee Performance: Sub-Accounts & Test Types 🎯")
        st.markdown("Analyze how sample volume is distributed across sub-account usage and specific test types for each franchisee.")
        
        temp['Sub_Account_Status'] = temp.apply(lambda row: 'Sub Account Used' if row['Franchisee_norm'] != row['Sub_Client_norm'] else 'Direct Account', axis=1)
        
        # Aggregate by Franchisee, Sub_Account_Status, and test name
        franchisee_sub_test_volume = temp.groupby(['Franchisee', 'Sub_Account_Status', 'test name']).size().reset_index(name='Sample Volume')

        if not franchisee_sub_test_volume.empty:
            fig6 = px.sunburst(
                franchisee_sub_test_volume,
                path=['Franchisee', 'Sub_Account_Status', 'test name'],
                values='Sample Volume',
                title='Franchisee Sample Volume by Sub-Account Status and Test Type',
                color='Sample Volume',
                color_continuous_scale=px.colors.sequential.Viridis
            )
            fig6.update_layout(margin=dict(t=0, l=0, r=0, b=0))
            st.plotly_chart(fig6, use_container_width=True)
        else:
            st.info("No data to display for Franchisee Performance: Sub-Accounts & Test Types with current filters.")

else:
    st.info("Please upload an Excel file to get started and analyze your franchisee data.")

# --- CHATBOT SECTION ---
st.sidebar.title("💬 Ask the Data")
st.sidebar.markdown("Chat with your filtered data using GPT!")

openai_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")

if openai_key:
    if uploaded_file and 'filtered_df' in locals(): # Ensure filtered_df exists
        user_question = st.sidebar.text_area("Ask a question about the CURRENTLY FILTERED data:", height=100)

        if user_question:
            try:
                openai.api_key = openai_key
                
                # Provide a more relevant sample of the FILTERED data to the chatbot
                # Consider sending a summary or a larger, relevant slice
                if not filtered_df.empty:
                    # Send up to 500 rows of the filtered data to provide more context
                    chat_data_context = filtered_df.head(500).to_csv(index=False)
                    
                    # Also provide a brief description of the columns for better understanding
                    column_description = "Columns in the data: 'Franchisee' (name of the franchisee), 'Sub Client' (sub-account name, often matches franchisee or is different), 'test name' (type of test), 'Lab Partner' (lab processing the test)."

                    response = openai.ChatCompletion.create(
                        model="gpt-4", # gpt-4 or gpt-3.5-turbo
                        messages=[
                            {"role": "system", "content": f"You are a helpful data analyst assistant specializing in lab testing datasets. Answer questions based on the provided data, which represents filtered lab sample volume by franchisee. Here is a description of the columns: {column_description}"},
                            {"role": "user", "content": f"Here is a sample of the **currently filtered** data:\n{chat_data_context}\n\nUser's question: {user_question}"}
                        ],
                        temperature=0.3,
                        max_tokens=1000 # Increased max_tokens for potentially longer answers
                    )
                    st.sidebar.markdown("**Answer from GPT:**")
                    st.sidebar.success(response.choices[0].message.content.strip())
                else:
                    st.sidebar.info("No filtered data available to query the chatbot. Please run a report first.")
            except openai.error.AuthenticationError:
                st.sidebar.error("OpenAI API Key is invalid. Please check your key.")
            except openai.error.APIError as e:
                st.sidebar.error(f"OpenAI API Error: {e}")
            except Exception as e:
                st.sidebar.error(f"An unexpected error occurred with the chatbot: {e}")
    elif not uploaded_file:
        st.sidebar.info("Please upload a file before asking questions to the chatbot.")
    else:
        st.sidebar.info("Run the report first to filter data before asking questions to the chatbot.")
else:
    st.sidebar.info("Please enter your OpenAI API Key to use the chatbot.")
