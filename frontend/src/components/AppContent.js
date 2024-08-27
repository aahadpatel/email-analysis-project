import React from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";
import Unauthorized from "./components/Unauthorized";
import AuthError from "./components/AuthError";
import ResultsTable from "./components/ResultsTable";

function AppContent({
  isAuthenticated,
  analysisStatus,
  progress,
  error,
  handleLogin,
  testCORS,
  handleStartAnalysis,
}) {
  const navigate = useNavigate();

  const checkProgress = async () => {
    try {
      console.log("Checking progress...");
      const response = await api.get("/check_progress");
      console.log("Progress update received:", response.data);
      setProgress(response.data);

      if (response.data.status === "Completed") {
        setAnalysisStatus("completed");
        navigate("/results"); // Redirect to results page
        return;
      } else if (response.data.status === "Error") {
        setAnalysisStatus("error");
        setError("Analysis failed: " + response.data.current_step);
        return;
      }

      // Continue checking progress if not completed or error
      setTimeout(checkProgress, 2000);
    } catch (error) {
      console.error("Error checking progress:", error);
      if (error.message === "Network Error") {
        setTimeout(checkProgress, 5000);
      } else {
        setError("Failed to check progress: " + error.message);
        setAnalysisStatus(null);
      }
    }
  };

  return (
    <Routes>
      <Route
        path="/"
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <Login onLogin={handleLogin} onTestCORS={testCORS} />
          )
        }
      />
      <Route
        path="/dashboard"
        element={
          isAuthenticated ? (
            <Dashboard
              onStartAnalysis={handleStartAnalysis}
              analysisStatus={analysisStatus}
              progress={progress}
              error={error}
            />
          ) : (
            <Navigate to="/" replace />
          )
        }
      />
      <Route
        path="/results"
        element={
          isAuthenticated ? <ResultsTable /> : <Navigate to="/" replace />
        }
      />
      <Route path="/unauthorized" element={<Unauthorized />} />
      <Route path="/auth-error" element={<AuthError />} />
    </Routes>
  );
}

export default AppContent;
