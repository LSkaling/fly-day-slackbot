from flask import Flask, request, send_file
import os
import tempfile

app = Flask(__name__)

# Define the directory to store uploaded .ics files
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create the upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part"
        
        file = request.files['file']

        if file.filename == '':
            return "No selected file"

        if file:
            # Create a temporary file to save the uploaded .ics file
            temp_file = tempfile.NamedTemporaryFile(delete=False, dir=app.config['UPLOAD_FOLDER'], suffix=".ics")
            temp_file.write(file.read())
            temp_file.close()
            
            return f"File uploaded successfully. <a href='/download/{temp_file.name}'>Download</a>"

    return '''
    <!doctype html>
    <title>Upload .ics File</title>
    <h1>Upload .ics File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.run(port=5002, debug=True)