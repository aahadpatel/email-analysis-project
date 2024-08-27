import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:5001", // Adjust this if your backend is on a different port
  withCredentials: true,
});

export const loginUser = async (credentials) => {
  try {
    const response = await api.post("/login", credentials);
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const testCORS = async () => {
  try {
    const response = await api.get("/test-cors");
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const startAnalysis = async () => {
  try {
    const response = await api.post("/start-analysis");
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const getAnalysisStatus = async () => {
  try {
    const response = await api.get("/analysis-status");
    return response.data;
  } catch (error) {
    throw error;
  }
};

export default api;
