import streamlit as st
import pandas as pd
import plotly.express as px
import openai

# --- CONFIG ---
st.set_page_config(page_title="Franchise Test Dashboard", layout="wide", initial_sidebar_state="expanded")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR ---
st.sidebar.title("Upload Data 📊") # Updated title for clarity
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

    # --- Display charts based on the entire uploaded dataset. ---
    
    # Assign the full DataFrame to filtered_df for chart generation
    filtered_df = df.copy() 

    # --- Dashboard Content ---
    st.title("Franchise Performance Dashboard 📈")
    st.markdown("Dive into your franchisee data to uncover patterns and insights.")

    # Prepare temp DataFrame for sub-account analysis (used for both combined chart and pie chart)
    temp = filtered_df.copy()
    temp['Franchisee_norm'] = temp['Franchisee'].astype(str).str.lower().str.strip()
    temp['Sub_Client_norm'] = temp['Sub Client'].astype(str).str.lower().str.strip()
    temp['Sub_Account_Status'] = temp.apply(lambda row: 'Sub Account Used' if row['Franchisee_norm'] != row['Sub_Client_norm'] else 'Direct Account', axis=1)

    # --- Calculate Percentage of Samples from Sub Accounts with Different Names ---
    # This calculation is now done here to be merged into the main volume_by_franchisee DataFrame
    sub_account_summary = temp.groupby('Franchisee')['Sub_Account_Status'].value_counts(normalize=True).unstack(fill_value=0)
    if 'Sub Account Used' in sub_account_summary.columns:
        sub_account_summary['% Sub Account Used'] = (sub_account_summary['Sub Account Used'] * 100).round(2)
    else:
        sub_account_summary['% Sub Account Used'] = 0.0 # If no sub accounts used at all
    
    # --- Franchisee Sample Volume (Enhanced with Top Test Info AND Sub-Account %) ---
    st.header("Franchisee Sample Volume (with Top Test & Sub-Account %)") # Updated header
    volume_by_franchisee = filtered_df['Franchisee'].value_counts().reset_index()
    volume_by_franchisee.columns = ['Franchisee', 'Sample Volume']

    # Calculate top test and its volume for each franchisee
    franchisee_test_volume = filtered_df.groupby(['Franchisee', 'test name']).size().reset_index(name='Test Volume')
    # Find the test with the max volume for each franchisee
    idx = franchisee_test_volume.groupby('Franchisee')['Test Volume'].idxmax()
    top_test_per_franchisee = franchisee_test_volume.loc[idx].set_index('Franchisee')
    top_test_per_franchisee.columns = ['Top Test Name', 'Top Test Volume'] # Rename columns for clarity

    # Merge top test info into the main volume_by_franchisee DataFrame
    volume_by_franchisee = volume_by_franchisee.set_index('Franchisee').join(top_test_per_franchisee).reset_index()

    # NEW: Merge sub-account percentage into the main volume_by_franchisee DataFrame
    volume_by_franchisee = volume_by_franchisee.set_index('Franchisee').join(sub_account_summary[['% Sub Account Used']]).reset_index()
    
    # Fill NaN for % Sub Account Used with 0.0 if a franchisee had no sub-account usage
    volume_by_franchisee['% Sub Account Used'] = volume_by_franchisee['% Sub Account Used'].fillna(0.0)

    # Create a combined label for the Y-axis
    volume_by_franchisee['Franchisee_Label'] = volume_by_franchisee.apply(
        lambda row: f"{row['Franchisee']} ({row['% Sub Account Used']:.2f}% Sub-Acct)", axis=1
    )

    volume_by_franchisee = volume_by_franchisee.sort_values('Sample Volume', ascending=True) # Sort ascending for Plotly bar chart
    
    # Create the base bar chart for total sample volume
    fig1 = px.bar(
        volume_by_franchisee, 
        y='Franchisee_Label', # Use the new combined label for the Y-axis
        x='Sample Volume', 
        orientation='h',
        title='Franchisee Sample Volume and Sub-Account Usage', # Updated chart title
        labels={'Franchisee_Label': 'Franchisee (Sub-Account %)', 'Sample Volume': 'Total Sample Volume'},
        color_discrete_sequence=[px.colors.qualitative.Pastel[0]] # Base color for total volume
    )
    
    # Add a second trace for the 'Top Test Volume' as an overlay
    fig1.add_trace(
        px.bar(
            volume_by_franchisee,
            y='Franchisee_Label',
            x='Top Test Volume',
            orientation='h',
            color_discrete_sequence=[px.colors.qualitative.Bold[0]] # Different color for top test volume
        ).data[0] # Extract the data from the temporary bar chart
    )

    fig1.update_layout(
        height=max(400, 30 * len(volume_by_franchisee)), 
        showlegend=False, # We'll manage legend manually if needed, for simplicity keep off
        barmode='overlay' # Overlay the bars
    )
    
    # Enhance tooltip to show top test information and sub-account percentage
    fig1.update_traces(hovertemplate="<b>Franchisee</b>: %{customdata[0]}<br>" + # Use original Franchisee from customdata
                                     "<b>Total Sample Volume</b>: %{x}<br>" +
                                     "<b>Top Test</b>: %{customdata[1]}<br>" +
                                     "<b>Top Test Volume</b>: %{customdata[2]}<br>" +
                                     "<b>% Sub Account Used</b>: %{customdata[3]:.2f}%<extra></extra>",
                       selector=dict(name='Sample Volume')) # Apply to the first trace (total volume)

    # Add custom data for the second trace (Top Test Volume) for its tooltip
    fig1.data[1].customdata = volume_by_franchisee[['Franchisee', 'Top Test Name', 'Top Test Volume', '% Sub Account Used']].values
    fig1.data[1].hovertemplate = "<b>Franchisee</b>: %{customdata[0]}<br>" + \
                                  "<b>Top Test Volume</b>: %{x}<br>" + \
                                  "<b>Top Test Name</b>: %{customdata[1]}<extra></extra>"


    st.plotly_chart(fig1, use_container_width=True)

    # --- Most Common Tests (Top N configurable) ---
    st.header("Most Common Tests")
    # Using a default value for the slider since there are no filters to apply first
    top_n_tests = st.slider("Number of Top Tests to Display:", 5, 50, 15, key='top_n_tests_slider') 
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
        color_discrete_sequence=px.colors.qualitative.Set2 # CORRECTED: Changed 'Light' to 'Set2'
    )
    fig3.update_layout(height=max(400, 30 * len(lab_counts)), showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

    # --- Sub Account vs Franchisee Analysis (Pie Chart remains for overall distribution) ---
    st.header("Overall Sub Account vs Franchisee Relationship") # Updated header for clarity
    # temp DataFrame is already prepared above
    sub_account_counts = temp['Sub_Account_Status'].value_counts()

    fig4 = px.pie(
        values=sub_account_counts.values, 
        names=sub_account_counts.index, 
        title='Distribution of Sample Volume by Sub Account Status',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig4, use_container_width=True)

    # --- Franchisee Sample Volume by Test Type (Top N for all franchisees) ---
    st.header("Franchisee Sample Volume by Top Test Types 🧪")
    st.markdown("Explore which test types contribute most to each franchisee's volume.")
    
    # Aggregate data for top tests per franchisee
    # franchisee_test_volume is already calculated above for the top test feature
    
    # Get top N tests for each franchisee (top 5 for each)
    top_tests_per_franchisee_chart = franchisee_test_volume.loc[franchisee_test_volume.groupby('Franchisee')['Test Volume'].rank(method='first', ascending=False) <= 5] 

    if not top_tests_per_franchisee_chart.empty:
        fig5 = px.bar(
            top_tests_per_franchisee_chart, # Use the new DataFrame for the chart
            x='Test Volume', 
            y='Franchisee',
            color='test name', # Changed back to 'test name' as it's the column in this dataframe
            orientation='h',
            title='Franchisee Sample Volume by Test Type (Top 5 per Franchisee)',
            labels={'Franchisee': 'Franchisee', 'Test Volume': 'Sample Volume', 'test name': 'Test Type'},
            height=max(500, 50 * len(filtered_df['Franchisee'].unique())), # Adjust height based on unique franchisees in full data
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig5.update_layout(barmode='stack', yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("No data to display for Franchisee Performance: Sub-Accounts & Test Types.")

    # --- NEW: Franchisee Sample Volume by Sub Account Status and Test Type ---
    st.header("Franchisee Performance: Sub-Accounts & Test Types 🎯")
    st.markdown("Analyze how sample volume is distributed across sub-account usage and specific test types for each franchisee.")
    
    # temp is already created above and contains the 'Sub_Account_Status' column
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
        st.info("No data to display for Franchisee Performance: Sub-Accounts & Test Types.")

else:
    st.info("Please upload an Excel file to get started and analyze your franchisee data.")

# --- CHATBOT SECTION (MOVED TO MAIN AREA) ---
st.header("💬 Ask the Data") # Changed to st.header
st.markdown("Chat with your uploaded data using GPT!") # Changed to st.markdown

# MODIFICATION: Retrieve OpenAI API key from Streamlit secrets
openai_api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else None

if openai_api_key: # Check if key is available from secrets
    if uploaded_file and 'filtered_df' in locals(): # filtered_df now holds the full df
        # Display chat messages in the main area
        # Using st.expander to make the chat history collapsible and manageable
        with st.expander("Chat History", expanded=True): # Changed to st.expander
            for message in st.session_state.messages:
                # Use st.chat_message for better UI in the main area
                with st.chat_message(message["role"]): # Changed to st.chat_message
                    st.markdown(message["content"])

        # Use a form to ensure all inputs are cleared on submission
        with st.form("chat_form"): # Changed to st.form
            user_question = st.text_area("Ask a question about the UPLOADED data:", height=100, key="chat_input_form")
            submit_button = st.form_submit_button("Ask GPT") # Changed to st.form_submit_button

            if submit_button and user_question:
                # Append user question to messages
                st.session_state.messages.append({"role": "user", "content": user_question})
                
                # Show spinner while thinking
                with st.spinner("Thinking..."): # Changed to st.spinner
                    try:
                        openai.api_key = openai_api_key 
                        
                        if not filtered_df.empty:
                            chat_data_context = filtered_df.head(500).to_csv(index=False)
                            column_description = "Columns in the data: 'Franchisee' (name of the franchisee), 'Sub Client' (sub-account name, often matches franchisee or is different), 'test name' (type of test), 'Lab Partner' (lab processing the test)."

                            response = openai.ChatCompletion.create(
                                model="gpt-4", 
                                messages=[
                                    {"role": "system", "content": f"You are a helpful data analyst assistant specializing in lab testing datasets. Answer questions based on the provided data, which represents lab sample volume by franchisee. Here is a description of the columns: {column_description}"},
                                    {"role": "user", "content": f"Here is a sample of the **currently uploaded** data:\n{chat_data_context}\n\nUser's question: {user_question}"}
                                ],
                                temperature=0.3,
                                max_tokens=1000 
                            )
                            gpt_response = response.choices[0].message.content.strip()
                            st.session_state.messages.append({"role": "assistant", "content": gpt_response})
                        else:
                            st.session_state.messages.append({"role": "assistant", "content": "No data available to query the chatbot. Please upload a file first."})
                    except openai.error.AuthenticationError:
                        st.session_state.messages.append({"role": "assistant", "content": "OpenAI API Key is invalid. Please check your key in Streamlit secrets."})
                    except openai.error.APIError as e:
                        st.session_state.messages.append({"role": "assistant", "content": f"OpenAI API Error: {e}"})
                    except Exception as e:
                        st.session_state.messages.append({"role": "assistant", "content": f"An unexpected error occurred with the chatbot: {e}"})
                
                # MODIFICATION: Removed st.experimental_rerun() here.
                # The form submission itself triggers a rerun, and the chat history will update.

    elif not uploaded_file:
        st.info("Please upload a file before asking questions to the chatbot.") # Changed to st.info
    else:
        st.info("Upload a file to enable the chatbot.") # Changed to st.info
else:
    st.warning("OpenAI API Key not found in Streamlit secrets. Please add it to your `.streamlit/secrets.toml` file.") # Changed to st.warning
