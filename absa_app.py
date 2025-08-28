# absa_converter_rewritten_v2.py

# Import necessary libraries.
import streamlit as st
import pandas as pd
import fitz  # PyMuPDF for PDF text extraction
import json
import base64
import io
import requests # For making API calls
import re

# --- IMPORTANT: PLACE YOUR API KEY HERE ---
# WARNING: Hardcoding the key is not a secure practice for public apps.
# However, it is done here to ensure the app works for you, bypassing local file issues.
# For production, you should use Streamlit's secrets management.
API_KEY = "AIzaSyA41FebmB_P3lsTaNmjXmcBU2c56m3iykw"  # <-- **PASTE YOUR API KEY HERE**

# --- Main App Configuration ---
st.set_page_config(page_title="ABSA PDF to CSV Converter", layout="centered")

# --- Function to interact with the AI ---
def process_with_ai(pdf_text):
    """
    Sends the extracted PDF text to the Gemini API to get structured transaction data.
    This function uses a highly specific and strict prompt to guide the AI,
    making it more robust for messy documents.
    """
    st.info("Using strict AI-based parser.")
    
    # Check if the API key is provided
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        st.error("Please enter a valid API key in the code before running the app.")
        return []

    # The prompt instructs the AI on how to parse the messy PDF text.
    prompt = f"""
    You are a highly specific and strict bank statement transaction parser. Your task is to extract transactions
    from the following ABSA bank statement text.

    The text is very messy. Each transaction might span multiple lines, and the amount columns
    (debit and credit) are often misaligned. You must use a very strict approach to identify transactions.

    A transaction is a line of text that starts with a date in the format 'DD/MM/YYYY' or 'D/MM/YYYY'.
    Ignore any lines that do not start with a date.
    For each transaction, extract the date, a concise description, and the amount.
    The amount must be a number: positive for credits and negative for debits.
    A credit amount will be a number in a credit column and will be positive.
    A debit amount will either be a negative number or a positive number in a debit column, and it should be converted to a negative number.

    The final output must be a clean JSON array of objects, with no extra text or explanation.

    Fields to extract for each transaction object:
    - 'date': The transaction date in 'YYYY-MM-DD' format.
    - 'description': A concise description of the transaction.
    - 'amount': The transaction amount as a number (e.g., 100.50 or -50.00).

    Bank Statement Text:
    {pdf_text}
    """

    # Payload for the API call
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "description": {"type": "string"},
                        "amount": {"type": "number"}
                    },
                    "required": ["date", "description", "amount"]
                }
            }
        }
    }
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={API_KEY}"
    
    try:
        response = requests.post(
            api_url,
            headers={'Content-Type': 'application/json'},
            json=payload
        )
        response.raise_for_status()
        
        api_response_json = response.json()
        if api_response_json and api_response_json.get('candidates'):
            raw_text = api_response_json['candidates'][0]['content']['parts'][0]['text']
            transactions = json.loads(raw_text)
            return transactions
        else:
            st.error("AI processing failed. Please try a different PDF or contact support.")
            return []
    except requests.exceptions.HTTPError as errh:
        st.error(f"HTTP Error: {errh}")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred during API processing: {e}")
        return []

# --- Main App UI Layout ---
def main():
    """
    This function contains the main user interface and logic for the Streamlit app.
    """
    st.title("📄 ABSA PDF to CSV Converter (AI)")
    st.markdown("""
    **This app is specifically for converting ABSA bank statement PDFs to a clean CSV file using a highly-tuned AI parser.**
    
    This tool is designed to handle the unique formatting of ABSA statements with a robust AI.
    """)

    uploaded_files = st.file_uploader(
        "Upload your ABSA PDF bank statements:",
        type="pdf",
        accept_multiple_files=True,
        key="pdf_uploader"
    )

    if uploaded_files:
        if st.button("Convert All to CSV"):
            with st.spinner("🚀 Processing files and extracting transactions... This may take a moment."):
                all_transactions = []
                for uploaded_file in uploaded_files:
                    try:
                        pdf_bytes = uploaded_file.getvalue()
                        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                        
                        full_text = ""
                        for page_num in range(len(pdf_document)):
                            page = pdf_document.load_page(page_num)
                            full_text += page.get_text()
                        
                        pdf_document.close()
                        
                        st.info(f"Processing transactions from: {uploaded_file.name}")
                        
                        transactions = process_with_ai(full_text)
                        all_transactions.extend(transactions)

                    except Exception as e:
                        st.error(f"Error reading PDF {uploaded_file.name}: {e}")
                
                if all_transactions:
                    df = pd.DataFrame(all_transactions, columns=['date', 'description', 'amount'])
                    csv_data = df.to_csv(index=False)
                    csv_bytes = csv_data.encode('utf-8')
                    
                    st.success("Conversion complete! 🎉")
                    st.dataframe(df)
                    
                    st.download_button(
                        label="Download Combined CSV",
                        data=csv_bytes,
                        file_name="absa_transactions.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No transactions could be extracted from any of the uploaded PDFs.")
    else:
        st.info("Please upload your PDF files to begin.")

if __name__ == "__main__":
    main()

