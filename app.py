import re
import logging
import tempfile
import os
import pandas as pd
from pdfminer.high_level import extract_text
from docx import Document
from flask import Flask, render_template, request, send_file, jsonify

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
            email = re.findall(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
            phone_numbers = re.findall(
                r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})', text)

            # Replace everything except characters, numbers, and single spaces
            text = re.sub(r'[^\w\s]+|_+', '', text)

            # Replace multiple variations of newlines with a single newline
            text = re.sub(r'[\r\n]+', '\n', text)

            # Remove leading and trailing whitespace from each line
            text = '\n'.join(line.strip() for line in text.split('\n'))

            # Remove empty lines
            text = re.sub(r'\n+', '\n', text)

            return {
                "Filename": filename,
                "Email": email[0] if email else None,
                "Phone Number": phone_numbers[0] if phone_numbers else None,
                "Text": text
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
            data = extract_info_from_cv(file)
            if data:
                extracted_data.append(data)

    if extracted_data:
        return render_template('download.html', data=extracted_data)
    return "Error processing files."

@app.route('/download', methods=['POST'])
def download():
    try:
        extracted_data = request.json
        df = pd.DataFrame(extracted_data)
        if not df.empty:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                df.to_excel(temp_file.name, index=False)
                temp_file.seek(0)
                return send_file(temp_file.name, as_attachment=True, download_name='cv_info.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        print(e)

    return jsonify({"message": "Error downloading data."}), 400

if __name__ == "__main__":
    app.run(debug=True)
