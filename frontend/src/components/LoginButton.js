import React from "react";

const LoginButton = ({ onLogin, onTestCORS }) => {
  return (
    <div className="space-y-4">
      <button
        onClick={onLogin}
        className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-md focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-75"
      >
        Sign in with Gmail
      </button>
      <button
        onClick={onTestCORS}
        className="w-full py-2 px-4 bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold rounded-lg shadow-md focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-opacity-75"
      >
        Test CORS
      </button>
    </div>
  );
};

export default LoginButton;
