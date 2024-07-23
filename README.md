# Email Scraper Web App

## Overview

The Email Scraper Web App is a powerful tool designed to streamline the process of extracting and analyzing information from emails. Built with a Python Flask backend and a React frontend, this application provides a user-friendly interface for scraping emails and processing data efficiently.

## Features

- **Email Scraping:** Currently extracts email information from the latest ten emails in your gmail inbox including date, subject, sender, and the first 100 characters from the email body. The long term goal would be for us to use this tool to analyze each email using existing LLMs.
- **Data Extraction:** Automatically parse and organize data into structured formats.
- **Frontend Interface:** Intuitive React-based UI for easy interaction and visualization of extracted data.
- **Backend Processing:** Robust Flask-based server handling data extraction and processing tasks.

## Technologies Used

- **Backend:** Python, Flask
- **Frontend:** JavaScript, React
- **Data Storage:** Not storing anything currently!

## Installation

### Backend

1. Clone the repository:

   ```bash
   git clone <repository-url>
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

5. Run the Flask server:
   ```bash
   python app.py
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
