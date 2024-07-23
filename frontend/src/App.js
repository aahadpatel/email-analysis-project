import React, { useState, useEffect } from "react";
import axios from "axios";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";

const api = axios.create({
  baseURL: "http://localhost:5001",
  timeout: 5000,
  withCredentials: true,
});

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);

  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        const response = await api.get("/check_auth");
        setIsAuthenticated(response.data.is_authenticated);
      } catch (error) {
        console.error("Error checking auth status:", error);
      }
    };

    checkAuthStatus();
  }, []);

  const handleLogin = async () => {
    try {
      const response = await api.get("/login");
      window.location.href = response.data.authorization_url;
    } catch (error) {
      console.error("Error during login:", error);
    }
  };

  const testCORS = async () => {
    try {
      const response = await api.get("/test");
      console.log("CORS Test Response:", response.data);
    } catch (error) {
      console.error("CORS Test Error:", error);
    }
  };

  const handleStartAnalysis = async () => {
    try {
      setAnalysisStatus("starting");
      setAnalysisError(null);
      const response = await api.post("/start_analysis");
      const taskId = response.data.task_id;
      setAnalysisStatus("in_progress");
      checkAnalysisProgress(taskId);
    } catch (error) {
      console.error("Error starting analysis:", error);
      setAnalysisError("Failed to start analysis: " + error.message);
      setAnalysisStatus(null);
    }
  };

  const checkAnalysisProgress = async (taskId) => {
    try {
      const response = await api.get(`/analysis_progress/${taskId}`);
      const status = response.data.status;
      setAnalysisStatus(status);

      if (status === "in_progress") {
        // Check again in 2 seconds
        setTimeout(() => checkAnalysisProgress(taskId), 2000);
      } else if (status === "completed") {
        setAnalysisStatus(
          `Analysis complete. Found ${response.data.num_startups} startup-related emails.`
        );
      } else if (status === "error") {
        setAnalysisError("Analysis failed: " + response.data.error);
        setAnalysisStatus(null);
      }
    } catch (error) {
      console.error("Error checking analysis progress:", error);
      setAnalysisError("Failed to check progress: " + error.message);
      setAnalysisStatus(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 py-6 flex flex-col justify-center sm:py-12">
      <div className="relative py-3 sm:max-w-xl sm:mx-auto">
        <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 to-light-blue-500 shadow-lg transform -skew-y-6 sm:skew-y-0 sm:-rotate-6 sm:rounded-3xl"></div>
        <div className="relative px-4 py-10 bg-white shadow-lg sm:rounded-3xl sm:p-20">
          <h1 className="text-4xl font-bold mb-5 text-center text-gray-800">
            Email Analysis App
          </h1>
          {!isAuthenticated ? (
            <Login onLogin={handleLogin} onTestCORS={testCORS} />
          ) : (
            <Dashboard
              onStartAnalysis={handleStartAnalysis}
              analysisStatus={analysisStatus}
              analysisError={analysisError}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
