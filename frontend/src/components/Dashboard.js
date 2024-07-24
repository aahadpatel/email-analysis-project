import React from "react";

function Dashboard({ onStartAnalysis, analysisStatus, progress, error }) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold mb-4">
        Welcome! You're authenticated.
      </h2>
      <button
        onClick={onStartAnalysis}
        disabled={
          analysisStatus === "starting" || analysisStatus === "in_progress"
        }
        className="w-full py-2 px-4 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow-md focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-opacity-75"
      >
        {analysisStatus === "starting" || analysisStatus === "in_progress"
          ? "Analysis in Progress..."
          : "Analyze Emails"}
      </button>
      {progress && (
        <div className="mt-6 space-y-4">
          <p className="text-lg">
            Status: <span className="font-semibold">{progress.status}</span>
          </p>
          <p className="text-lg">
            Processed Emails:{" "}
            <span className="font-semibold">
              {progress.processed_emails} / {progress.total_emails}
            </span>
          </p>
          <p className="text-lg">
            Analyzed Companies:{" "}
            <span className="font-semibold">
              {progress.analyzed_companies} / {progress.total_companies}
            </span>
          </p>
        </div>
      )}
      {error && (
        <div
          className="mt-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative"
          role="alert"
        >
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
      )}
      {analysisStatus === "completed" && (
        <div
          className="mt-6 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative"
          role="alert"
        >
          <strong className="font-bold">Analysis Completed: </strong>
          <span className="block sm:inline">
            Check your CSV file for results.
          </span>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
