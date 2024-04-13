import re
import ast
import logging
import tempfile
import os
import pandas as pd
from pdfminer.high_level import extract_text
from docx import Document
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='cv_extraction.log', level=logging.DEBUG)

def extract_text_from_pdf(file_obj):
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file_obj.save(tmp.name)
            text = extract_text(tmp.name)
        os.unlink(tmp.name)  # Delete temporary file
        return text
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        return None

def extract_text_from_docx(file_obj):
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file_obj.save(tmp.name)
            doc = Document(tmp.name)
            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        os.unlink(tmp.name)  # Delete temporary file
        return text
    except Exception as e:
        logging.error(f"Error extracting text from DOCX: {e}")
        return None

def extract_info_from_cv(file):
    filename = file.filename
    try:
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(file)
        elif filename.endswith('.docx'):
            text = extract_text_from_docx(file)
        else:
            return None

        if text:
            email = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
            phone_numbers = re.findall(r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})', text)

            return {
                'Filename': filename,
                'Email': email[0] if email else None,
                'Phone Number': phone_numbers[0] if phone_numbers else None,
                'Text': text
            }
    except Exception as e:
        logging.error(f"Error processing {filename}: {e}")
        return None

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    uploaded_files = request.files.getlist('file[]')
    extracted_data = []
    for file in uploaded_files:
        if file.filename != '':
            logging.info(f"Uploaded file: {file.filename}")
            data = extract_info_from_cv(file)
            if data:
                logging.info(f"Extracted data: {data}")
                extracted_data.append(data)

    if extracted_data:
        return render_template('download.html', data=extracted_data)
    return "Error processing files."

@app.route('/download', methods=['GET'])
def download():
    extracted_data = request.args.getlist('data')
    if extracted_data:
        data_dicts = []
        for data_str in extracted_data:
            data = ast.literal_eval(data_str)
            standardized_data = {'Filename': None, 'Email': None, 'Phone Number': None, 'Text': None}
            standardized_data.update(data)
            data_dicts.append(standardized_data)
        
        if data_dicts:
            df = pd.DataFrame(data_dicts)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                writer = pd.ExcelWriter(temp_file.name, engine='xlsxwriter')
                df.to_excel(writer, index=False)
                writer.close()

                return send_file(temp_file.name, as_attachment=True, download_name='cv_info.xlsx')
    
    return "No data to download."

if __name__ == "__main__":
    app.run(debug=False)
