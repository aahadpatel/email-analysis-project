import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import ProgressGuide from "./ProgressGuide";

function Dashboard({ onStartAnalysis, analysisStatus, progress, error }) {
  const [lastAnalysisDate, setLastAnalysisDate] = useState(null);

  useEffect(() => {
    fetchLastAnalysisDate();
  }, []);

  const fetchLastAnalysisDate = async () => {
    try {
      const response = await axios.get(
        "http://localhost:5001/last-analysis-date",
        {
          withCredentials: true,
        }
      );
      setLastAnalysisDate(response.data.last_analysis_date);
    } catch (err) {
      console.error("Failed to fetch last analysis date:", err);
    }
  };

  const handleStartAnalysis = (fullReanalysis = false) => {
    onStartAnalysis(fullReanalysis);
  };

  return (
    <div className="relative min-h-screen">
      <div className="space-y-6">
        <div className="justify-center items-center space-y-4">
          <h2 className="text-center text-2xl font-semibold mb-4">
            Welcome! You're authenticated.
          </h2>
          {lastAnalysisDate && (
            <p className="text-center text-lg">
              Last analysis date:{" "}
              <span className="font-semibold">
                {new Date(lastAnalysisDate).toLocaleString()}
              </span>
            </p>
          )}
          <button
            onClick={() => handleStartAnalysis(false)}
            disabled={
              analysisStatus === "starting" || analysisStatus === "in_progress"
            }
            className="w-full py-2 px-4 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow-md focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-opacity-75"
          >
            {analysisStatus === "starting" || analysisStatus === "in_progress"
              ? "Analysis in Progress..."
              : "Analyze New Emails"}
          </button>
          <button
            onClick={() => handleStartAnalysis(true)}
            disabled={
              analysisStatus === "starting" || analysisStatus === "in_progress"
            }
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-md focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-75"
          >
            Full Reanalysis
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
              Found {progress?.num_startups} potential startup(s). Click the
              View Analyzed Startups button for results.
            </span>
          </div>
        )}
        {analysisStatus !== "starting" && analysisStatus !== "in_progress" && (
          <Link
            to="/startups"
            className="block w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-md focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-75 text-center"
          >
            View Analyzed Startups
          </Link>
        )}
      </div>
      <ProgressGuide />
    </div>
  );
}

export default Dashboard;
