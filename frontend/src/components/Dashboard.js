import React, { useEffect } from "react";
import ProgressGuide from "./ProgressGuide";

function Dashboard({ onStartAnalysis, analysisStatus, progress, error }) {
  useEffect(() => {
    console.log("Progress prop updated:", progress);
  }, [progress]);
  console.log("Dashboard render - analysisStatus:", analysisStatus);
  console.log("Dashboard render - progress:", progress);
  console.log("Dashboard render - error:", error);
  return (
    <div className="relative min-h-screen">
      <div className="space-y-6">
        <div className="justify-center items-center space-y-4">
          <h2 className="text-center text-2xl font-semibold mb-4">
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
        </div>
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
            {progress.num_startups !== undefined && (
              <p className="text-lg">
                Identified Startups:{" "}
                <span className="font-semibold">{progress.num_startups}</span>
              </p>
            )}
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
              Found {progress?.num_startups} potential startup(s). Check your
              CSV file for results.
            </span>
          </div>
        )}
      </div>
      <ProgressGuide />
    </div>
  );
}

export default Dashboard;
