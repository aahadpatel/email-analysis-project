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
  const [analysisResult, setAnalysisResult] = useState(null);

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

  const handleAnalyzeEmails = async () => {
    try {
      const response = await api.get("/analyze_emails");
      setAnalysisResult(response.data);
    } catch (error) {
      console.error("Error analyzing emails:", error);
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
              onAnalyze={handleAnalyzeEmails}
              analysisResult={analysisResult}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
