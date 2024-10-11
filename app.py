from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import pandas as pd
import re
import os

app = Flask(__name__)

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})

# Set the Google API key
GOOGLE_API_KEY = "AIzaSyDnio5ITdIdAp0gxV1mEpe_o6igx0RwOxQ"
genai.configure(api_key=GOOGLE_API_KEY)

@app.route('/run-scorecard', methods=['POST'])
def run_scorecard():
    # Check if both 'batsman_file' and 'bowler_file' are in the request
    if 'batsman_file' not in request.files or 'bowler_file' not in request.files:
        return jsonify({'error': 'Both batsman and bowler files are required'}), 400

    batsman_file = request.files['batsman_file']
    bowler_file = request.files['bowler_file']

    # Save both files temporarily
    batsman_path = os.path.join("uploads", batsman_file.filename)
    bowler_path = os.path.join("uploads", bowler_file.filename)
    batsman_file.save(batsman_path)
    bowler_file.save(bowler_path)

    # **Process batsman image**
    batsman_sample_file = genai.upload_file(path=batsman_path, display_name="Batsman Scorecard")
    batsman_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")
    batsman_response = batsman_model.generate_content([batsman_sample_file,
        "I want each batsman name, 4s, 6s, balls faced and total runs in this exact format, name '\n' 4s: '\n' 6s: '\n' ballsFaced: '\n' totalRuns: '\n'. Don't use single or double quotation marks."])

    batsman_text = batsman_response.text.replace(" ", "")
    batsman_pattern = re.compile(
        r'(?P<name>[A-Za-z.]+)\n4s:(?P<fours>\d*)\n6s:(?P<sixes>\d*)\nballsFaced:(?P<balls_faced>\d*)\ntotalRuns:(?P<total_runs>\d*)')
    batsman_matches = batsman_pattern.findall(batsman_text)
    df_batsman_info = pd.DataFrame(batsman_matches, columns=['name', 'fours', 'sixes', 'balls_faced', 'total_runs'])

    # **Process bowler image**
    bowler_sample_file = genai.upload_file(path=bowler_path, display_name="Bowler Scorecard")
    bowler_model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")
    bowler_response = bowler_model.generate_content([bowler_sample_file,
        "I want each bowler name, overs, runs and wickets in this exact format, name '\n' overs: '\n' runs: '\n' wickets: '\n'. Don't use single or double quotation marks."])

    bowler_text = bowler_response.text.replace(" ", "")
    bowler_pattern = re.compile(r'(?P<name>[A-Za-z.]+)\novers:(?P<overs>\d*)\nruns:(?P<runs>\d*)\nwickets:(?P<wickets>\d*)')
    bowler_matches = bowler_pattern.findall(bowler_text)
    df_bowler_info = pd.DataFrame(bowler_matches, columns=['name', 'overs', 'runs', 'wickets'])

    # **Merge batsman and bowler data**
    df = pd.merge(df_batsman_info, df_bowler_info, on='name', how='outer')

    # Convert columns to appropriate data types, replacing NaN with 0 or a suitable default
    df['fours'] = pd.to_numeric(df['fours'], errors='coerce').fillna(0).astype(int)
    df['sixes'] = pd.to_numeric(df['sixes'], errors='coerce').fillna(0).astype(int)
    df['balls_faced'] = pd.to_numeric(df['balls_faced'], errors='coerce').fillna(0).astype(
        int)
    df['total_runs'] = pd.to_numeric(df['total_runs'], errors='coerce').fillna(0).astype(int)

    df['overs'] = pd.to_numeric(df['overs'], errors='coerce').fillna(0).astype(int)
    df['runs'] = pd.to_numeric(df['runs'], errors='coerce').fillna(0).astype(int)
    df['wickets'] = pd.to_numeric(df['wickets'], errors='coerce').fillna(0).astype(int)

    # Clean up: Remove the uploaded files
    os.remove(batsman_path)
    os.remove(bowler_path)
    print(df)

    # Convert DataFrame to JSON and return as a response
    return jsonify(df.to_dict(orient="records"))

# if __name__ == "__main__":
#     # Create uploads folder if it doesn't exist
#     uploads_dir = os.path.join(os.getcwd(), 'uploads')
#     if not os.path.exists(uploads_dir):
#         os.makedirs(uploads_dir)
#     app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)

if __name__ == "__main__":
    # Create uploads folder if it doesn't exist
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)