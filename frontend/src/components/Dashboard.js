import React from "react";

function Dashboard({ onStartAnalysis, analysisStatus, analysisError }) {
  const isAnalyzing =
    analysisStatus === "starting" || analysisStatus === "in_progress";

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold mb-4">
        Welcome! You're authenticated.
      </h2>
      <button
        onClick={onStartAnalysis}
        disabled={isAnalyzing}
        className={`w-full py-2 px-4 ${
          isAnalyzing ? "bg-gray-400" : "bg-green-600 hover:bg-green-700"
        } text-white font-semibold rounded-lg shadow-md focus:outline-none focus:ring-2 focus:ring-green-400 focus:ring-opacity-75`}
      >
        {isAnalyzing ? "Analysis in Progress..." : "Analyze Emails"}
      </button>
      {analysisStatus && (
        <div className="mt-6 space-y-4">
          <p className="text-lg">
            Status: <span className="font-semibold">{analysisStatus}</span>
          </p>
          {analysisStatus.includes("Analysis complete") && (
            <>
              <p className="text-lg">
                Number of startup-related emails found:{" "}
                <span className="font-semibold">
                  {
                    analysisStatus.match(
                      /Found (\d+) startup-related emails/
                    )[1]
                  }
                </span>
              </p>
              {/* You might want to add a way to display or download the CSV file */}
            </>
          )}
        </div>
      )}
      {analysisError && (
        <div
          className="mt-6 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative"
          role="alert"
        >
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{analysisError}</span>
        </div>
      )}
      {/* You might want to add a way to display startup details here once the analysis is complete */}
    </div>
  );
}

export default Dashboard;
