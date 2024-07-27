# Email Analyzer for Startup Identification

## Overview

The Email Analyzer is a sophisticated tool designed to help venture capital firms identify potential startup investments by analyzing email communications. Built with a Python Flask backend and a React frontend, this application provides a user-friendly interface for processing emails and generating insightful reports.

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

1. Navigate to the `backend` directory:

   ```bash
   cd backend
   ```

1. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

1. Run the Flask server:
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

## Contributing

If you'd like to contribute to this project, please fork the repository and submit a pull request with your proposed changes. Be sure to adhere to the project's coding standards and include relevant tests.

## License

This project is licensed under the [MIT License](LICENSE).
