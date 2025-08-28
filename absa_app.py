# absa_app.py

# Import necessary libraries. We'll use Streamlit for the app interface,
# pandas to create the CSV, and PyMuPDF to read the PDF.
import streamlit as st
import pandas as pd
import fitz  # This is the PyMuPDF library
import re # We'll use regular expressions for text cleaning

# --- Main App Configuration ---
# Set the title and a brief description for your app.
st.set_page_config(page_title="ABSA PDF to CSV Converter", layout="centered")

# --- Function to parse ABSA PDFs using a rule-based approach ---
def parse_absa_pdf(pdf_text):
    """
    Parses transactions from ABSA PDFs using a more robust set of regular expressions.
    This approach is designed to handle the inconsistent formatting of this specific PDF.
    """
    st.info("Using enhanced rule-based parser for ABSA file.")
    transactions = []
    
    # This pattern is more targeted. It looks for a date at the beginning of a line,
    # then captures the description and the two amount columns (debit and credit).
    # The regex is now more lenient with whitespace and line breaks.
    # It accounts for the "Acb Credit" and "Ibank Payment To" patterns.
    absa_pattern = re.compile(
        r'(\d{1,2}/\d{1,2}/\d{4})\s+' # Date at the start of the line
        r'(.+?)' # Non-greedy description
        r'(\s+[\d\s,.-]+)\s*$' # Debit or Credit amount at the end of the line
    )

    # A more specific pattern to capture the debit and credit columns when they are separated.
    absa_pattern_split = re.compile(
        r'(\d{1,2}/\d{1,2}/\d{4})' # Date
        r'(.+?)' # Description
        r'(\d{1,2}/\d{1,2}/\d{4})?' # Optional second date if the line wraps
        r'([\d\s,.-]+)?\s*' # Optional charge or debit amount
        r'([\d\s,.-]+)\s*$' # Credit amount at the end
    )
    
    # Split the text into lines to process each transaction individually.
    lines = pdf_text.split("\n")
    
    for line in lines:
        if "statement no" in line.lower() or "transaction description" in line.lower() or "page" in line.lower():
            continue # Skip headers and other non-transaction lines

        # Remove extra spaces and make the line more manageable.
        line = re.sub(r'\s+', ' ', line).strip()
        
        # First, try to match the split debit/credit pattern
        match = absa_pattern_split.search(line)
        if match:
            try:
                date_str = match.group(1).strip()
                description = match.group(2).strip()
                debit_str = match.group(4)
                credit_str = match.group(5)
                
                amount = 0.0
                if credit_str and credit_str.strip() != "":
                    amount = float(credit_str.replace(" ", "").replace(",", ""))
                elif debit_str and debit_str.strip() != "":
                    amount = -abs(float(debit_str.replace(" ", "").replace(",", "").replace("-", "")))
                else:
                    continue # Skip transactions without a clear amount

                transactions.append({
                    "date": pd.to_datetime(date_str, format="%d/%m/%Y").strftime("%Y-%m-%d"),
                    "description": description,
                    "amount": amount
                })
            except (ValueError, IndexError):
                continue

    # If no transactions found with the split pattern, try the combined pattern.
    if not transactions:
        for line in lines:
            line = re.sub(r'\s+', ' ', line).strip()
            match = absa_pattern.search(line)
            if match:
                try:
                    date_str = match.group(1).strip()
                    description = match.group(2).strip()
                    amount_str = match.group(3).strip()
                    
                    amount = float(amount_str.replace(" ", "").replace(",", "").replace("-", ""))
                    if "-" in amount_str:
                        amount = -abs(amount)
                    
                    transactions.append({
                        "date": pd.to_datetime(date_str, format="%d/%m/%Y").strftime("%Y-%m-%d"),
                        "description": description,
                        "amount": amount
                    })
                except (ValueError, IndexError):
                    continue

    st.success(f"Found {len(transactions)} transactions with enhanced rule-based parser.")
    return transactions

# --- Main App UI Layout ---
def main():
    """
    This function contains the main user interface and logic for the Streamlit app.
    """
    st.title("📄 ABSA PDF to CSV Converter")
    st.markdown("""
    **This app is specifically for converting ABSA bank statement PDFs to a clean CSV file.**
    
    This tool is designed to handle the unique formatting of ABSA statements using a robust, rule-based parser.
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
                        transactions = parse_absa_pdf(full_text)
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

