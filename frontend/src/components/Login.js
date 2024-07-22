import React from "react";
import LoginButton from "./LoginButton";

function Login({ onLogin, onTestCORS }) {
  return (
    <div className="text-center">
      <h2 className="text-2xl font-semibold mb-4">Please log in to continue</h2>
      <LoginButton onLogin={onLogin} onTestCORS={onTestCORS} />
    </div>
  );
}

export default Login;
