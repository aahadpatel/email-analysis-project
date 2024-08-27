# Email Analyzer for Startup Identification

## Overview

The Email Analyzer is a tool designed to help venture capital firms identify potential startup investments by analyzing email communications since existing CRMs aren't ideal. Built with a Python Flask backend and a React frontend, this application provides a user-friendly interface for processing emails and generating a CSV. The output CSV is structured with the following columns:

- **First Interaction Date:** The date of the first interaction with the startup.
- **Last Interaction Date:** The date of the last interaction with the startup.
- **Company:** The name of the startup.
- **Interactions:** The number of interactions with the startup.
- **Last Interaction:** A snippet of the last interaction with the startup.
- **AI Explanation:** A summary of the AI's reasoning for why the company we're speaking to is a startup.

I'll most likely add database functionality in the future, but for now the output is just saved to a CSV. I'm not currently storing any data.

## Features

- **Email Analysis:** Analyzes emails from your Gmail inbox to identify potential startup companies.
- **AI-Powered Analysis:** Utilizes OpenAI's GPT-3.5 Turbo to interpret email content and determine if the sender is likely a startup.
- **Batch Processing:** Efficiently processes multiple emails in batches to optimize performance and cost.
- **CSV Report Generation:** Outputs results in a CSV format, including key information about identified startups.
- **Progress Tracking:** Real-time updates on the analysis process through the frontend interface.

## Technologies Used

- **Backend:** Python, Flask, Google Gmail API, OpenAI API
- **Frontend:** JavaScript, React
- **Data Processing:** AsyncIO for asynchronous operations
- **AI Model:** OpenAI's GPT-3.5 Turbo

## Installation

### Backend

1. Clone the repository:

   ```bash
   git clone https://github.com/aahadpatel/email-analysis-project
   ```

2. Navigate to the `backend` directory:

   ```bash
   cd backend
   ```

3. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Set up the configuration:

- Edit `config/settings.py` to set the correct environment variables (see Configuration section below for more details)

6. Create a `.env` file in the `backend` directory and set a `SECRET_KEY` and `OPENAI_API_KEY`.

7. Run the Flask server:
   ```bash
   flask run --port=INSERT_PORT
   ```

### Frontend

1. Navigate to the `frontend` directory:

   ```bash
   cd frontend
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Start the React development server:
   ```bash
   npm start
   ```

## Usage

1. Open your browser and navigate to `http://localhost:3000` to access the frontend interface.
2. Follow the instructions in the app to input email data and initiate the scraping process.
3. View and analyze the extracted information through the provided UI elements.

## Configuration

The application uses a configuration file and client secrets for authentication. Follow these steps to set up the necessary files:

1. Create a `backend/instance` folder in your project directory.

2. Inside the `backend/instance` folder, create two files:

   - `client_secret.json`
   - `config.py`

3. In the `client_secret.json` file, add your Google OAuth 2.0 client credentials. The file should have the following structure:

   ```json
   {
     "web": {
       "client_id": "YOUR_CLIENT_ID",
       "project_id": "YOUR_PROJECT_ID",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token",
       "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
       "client_secret": "YOUR_CLIENT_SECRET",
       "redirect_uris": ["http://localhost:5000/oauth2callback"],
       "javascript_origins": ["http://localhost:3000"]
     }
   }
   ```

   Replace `YOUR_CLIENT_ID`, `YOUR_PROJECT_ID`, and `YOUR_CLIENT_SECRET` with your actual Google OAuth 2.0 credentials.

4. In the `config.py` file, add any additional configuration variables specific to your instance. For example:

   ```python
   SECRET_KEY = 'your_secret_key_here'
   OPENAI_API_KEY = 'your_openai_api_key_here'
   ```

   Make sure to replace `'your_secret_key_here'` and `'your_openai_api_key_here'` with your actual secret key and OpenAI API key.

The application uses a main configuration file located at `backend/config/settings.py`. This file contains important settings such as:

- `MAX_EMAILS`: The maximum number of emails to process.
- `INTERNAL_DOMAINS`: The list of internal domains to filter out.
- `BLACKLISTED_DOMAINS`: The list of blacklisted domains to filter out.
- `OPENAI_API_KEY`: The API key for the OpenAI API.
- `SECRET_KEY`: The secret key for the Flask application.

This is an example of what the configuration file should look like:

```python
import os

MAX_EMAILS = 100
# domains we do not want to process
BLACKLISTED_DOMAINS = {'gmail.com', 'yahoo.com', 'hotmail.com'}
# if the email thread is between any of these domains, we don't want to process it
INTERNAL_DOMAINS = {'mucker.com', 'muckercapital.com'}
# pulling from .env file located at backend/.env
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
```

## Contributing

If you'd like to contribute to this project, please fork the repository and submit a pull request with your proposed changes. Be sure to adhere to the project's coding standards and include relevant tests.

## License

This project is licensed under the [MIT License](LICENSE).
