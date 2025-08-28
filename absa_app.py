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
    Parses transactions from ABSA PDFs using a robust, multi-line regular expression.
    This is designed to handle the highly inconsistent formatting of this specific PDF.
    """
    st.info("Using multi-line rule-based parser for ABSA file.")
    transactions = []
    
    # This pattern is more forgiving and looks for a transaction across multiple lines.
    # The re.DOTALL flag is crucial to make '.' match newlines.
    absa_pattern_multiline = re.compile(
        r'(\d{1,2}/\d{1,2}/\d{4})\s' # Date
        r'(.*?)' # Non-greedy description, including newlines
        r'([\d\s,.-]+)\s*$' # Matches the amount at the end of a block
    )
    
    # Clean the entire text block first.
    # The original PDF has many line breaks that mess up the extraction.
    cleaned_text = re.sub(r'[\r\n]+', ' ', pdf_text)

    # Re-introduce newlines in a more consistent way to define transaction blocks.
    # This is a guess based on the PDF's layout where a balance often signals a new line.
    cleaned_text = re.sub(r'(\s\d{1,3}(,\d{3})*(\.\d{2}))', r'\n\1', cleaned_text)
    
    # Now, try to match the pattern on the cleaned text.
    matches = absa_pattern_multiline.findall(cleaned_text)

    for match in matches:
        try:
            date_str = match[0].strip()
            description = match[1].strip()
            amount_str = match[2].strip()

            amount = float(amount_str.replace(" ", "").replace(",", "").replace("-", ""))
            
            # Since the amounts are in separate columns, we need to determine the sign.
            # We look for keywords like "Debit" or "Charge" to identify negative amounts.
            if "Debit Amount" in cleaned_text or "Charge" in description or "-" in amount_str:
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


