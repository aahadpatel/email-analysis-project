import React from "react";

function Dashboard({ onAnalyze, analysisResult }) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold mb-4">
        Welcome! You're authenticated.
      </h2>
      <button
        onClick={onAnalyze}
        className="w-full py-2 px-4 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow-md focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-opacity-75"
      >
        Analyze Emails
      </button>
      {analysisResult && (
        <div className="mt-6 space-y-4">
          <p className="text-lg">
            Number of startup-related emails found:{" "}
            <span className="font-semibold">{analysisResult.num_startups}</span>
          </p>
          <p className="text-lg">
            CSV file path:{" "}
            <span className="font-semibold">{analysisResult.csv_path}</span>
          </p>
          {analysisResult.startup_details && (
            <div className="mt-6">
              <h3 className="text-xl font-semibold mb-4">
                Startup Email Details:
              </h3>
              {analysisResult.startup_details.map((detail, index) => (
                <div key={index} className="bg-gray-100 p-4 rounded-lg mb-4">
                  <p className="font-semibold">Subject: {detail.subject}</p>
                  <p>Sender: {detail.sender}</p>
                  <p className="mt-2">
                    AI Explanation: {detail.ai_explanation}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Dashboard;
