# absa_strict_ai_app.py

# Import necessary libraries. We'll use Streamlit for the app interface,
# pandas to create the CSV, and PyMuPDF to read the PDF.
import streamlit as st
import pandas as pd
import fitz  # This is the PyMuPDF library
import json
import base64
import io
import requests # We will use the standard requests library for API calls
import os # Import the os module to use environment variables
import re # We'll use regular expressions for text cleaning

# --- Main App Configuration ---
# Set the title and a brief description for your app.
st.set_page_config(page_title="ABSA PDF to CSV Converter (AI)", layout="centered")

# --- Function to interact with the AI ---
def process_with_ai(pdf_text):
    """
    Sends the extracted PDF text to the Gemini API to get structured transaction data.
    This function uses a highly specific and strict prompt to guide the AI,
    making it more robust for messy documents.
    """
    st.info("Using strict AI-based parser.")
    # The prompt is a set of instructions for the AI.
    # It tells the AI exactly what to look for and how to format the output.
    prompt = f"""
    You are a highly specific and strict bank statement transaction parser. Your task is to extract transactions
    from the following bank statement text. This text is from an ABSA bank.

    The text is very messy. Each transaction might span multiple lines, and the amount columns
    (debit and credit) are often misaligned or mixed with the description. You must use a very strict
    approach to identify transactions.

    A transaction is a line of text that starts with a date in the format 'DD/MM/YYYY'.
    Ignore any lines that do not start with a date, such as headers, footers, or account summaries.
    For each transaction, extract the date, description, and amount.
    The amount must be a number: positive for credits and negative for debits.
    A credit amount will be a number in a credit column (often a final column) and will be positive.
    A debit amount will either be a negative number or a positive number in a debit column, and it should be converted to a negative number.

    The final output must be a clean JSON array of objects, with no extra text or explanation.

    Fields to extract for each transaction object:
    - 'date': The transaction date in 'YYYY-MM-DD' format.
    - 'description': A concise description of the transaction.
    - 'amount': The transaction amount as a number (e.g., 100.50 or -50.00).

    Example of expected output format:
    [
      {{ "date": "2021-04-29", "description": "Acb Credit Yoco B5ccc7 Yoco", "amount": 5421.42 }},
      {{ "date": "2021-04-30", "description": "Settlement Acb Credit Yoco Yoco B5ccc7", "amount": 3922.64 }},
      {{ "date": "2021-05-01", "description": "Admin Charge Headoffice See Charge Statement Detail", "amount": -83.00 }}
    ]

    Bank Statement Text:
    {pdf_text}
    """

    # --- API Call to Gemini ---
    # This is where the AI processing happens. We configure it to return JSON directly.
    # The schema is now updated to only include date, description, and amount.
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

    # This URL is the entry point for the AI model.
    api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"
    
    # NOTE: The API key has been hardcoded here for your convenience.
    # For a production application, it is HIGHLY recommended to use
    # Streamlit's secrets management for security.
    api_key = "AIzaSyB6ldpXkgPsfI9xU79_QZKGw6SDwDmVgWM"

    try:
        # We'll now use the standard requests library which works reliably with Streamlit.
        response = requests.post(
            api_url,
            headers={'Content-Type': 'application/json'},
            params={'key': api_key},
            json=payload
        )
        response.raise_for_status() # Raise an exception for bad status codes
        
        # Check if the API response is valid and contains content.
        api_response_json = response.json()
        if api_response_json and api_response_json.get('candidates') and api_response_json['candidates'][0].get('content'):
            raw_text = api_response_json['candidates'][0]['content']['parts'][0]['text']
            # Parse the JSON string into a Python list of dictionaries.
            transactions = json.loads(raw_text)
            return transactions
        else:
            st.error("AI processing failed. Please try a different PDF or contact support.")
            st.json(api_response_json) # Displaying the raw response can help with debugging
            return []
    except requests.exceptions.HTTPError as errh:
        st.error(f"HTTP Error: {errh}")
        return []
    except requests.exceptions.RequestException as err:
        st.error(f"An error occurred during API call: {err}")
        return []
    except json.JSONDecodeError as err:
        st.error(f"Failed to decode JSON response from AI: {err}")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred during AI processing: {e}")
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

    # File uploader widget to let the user upload multiple PDFs.
    uploaded_files = st.file_uploader(
        "Upload your ABSA PDF bank statements:",
        type="pdf",
        accept_multiple_files=True,
        key="pdf_uploader"
    )

    # Check if files have been uploaded by the user.
    if uploaded_files:
        if st.button("Convert All to CSV"):
            with st.spinner("🚀 Processing files and extracting transactions... This may take a moment."):
                all_transactions = []
                # Loop through each uploaded file.
                for uploaded_file in uploaded_files:
                    try:
                        # Read the uploaded PDF file's content in memory.
                        pdf_bytes = uploaded_file.getvalue()
                        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
                        
                        # Extract all text from the PDF.
                        full_text = ""
                        for page_num in range(len(pdf_document)):
                            page = pdf_document.load_page(page_num)
                            full_text += page.get_text()
                        
                        pdf_document.close()
                        
                        st.info(f"Processing transactions from: {uploaded_file.name}")
                        
                        # Call the ABSA-specific parser.
                        transactions = process_with_ai(full_text)
                        all_transactions.extend(transactions)

                    except Exception as e:
                        st.error(f"Error reading PDF {uploaded_file.name}: {e}")
                
                # After processing all files, create a single DataFrame.
                if all_transactions:
                    df = pd.DataFrame(all_transactions, columns=['date', 'description', 'amount'])
                    
                    # Convert DataFrame to CSV.
                    csv_data = df.to_csv(index=False)
                    csv_bytes = csv_data.encode('utf-8')
                    
                    st.success("Conversion complete! 🎉")
                    st.dataframe(df) # Display the DataFrame for a quick preview.
                    
                    # Create a download button for the CSV file.
                    st.download_button(
                        label="Download Combined CSV",
                        data=csv_bytes,
                        file_name="absa_transactions.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No transactions could be extracted from any of the uploaded PDFs.")

    # A simple message to guide the user if no file is uploaded yet.
    else:
        st.info("Please upload your PDF files to begin.")

# Run the main function when the script is executed.
if __name__ == "__main__":
    main()
