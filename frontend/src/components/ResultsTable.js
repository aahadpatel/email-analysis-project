import React, { useState, useEffect } from "react";
import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:5001",
  timeout: 5000,
  withCredentials: true,
});

function ResultsTable() {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        const response = await api.get("/companies");
        setCompanies(response.data);
        setLoading(false);
      } catch (err) {
        setError("Failed to fetch companies");
        setLoading(false);
      }
    };

    fetchCompanies();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white">
        <thead className="bg-gray-800 text-white">
          <tr>
            <th className="py-2 px-4 text-left">Name</th>
            <th className="py-2 px-4 text-left">First Interaction</th>
            <th className="py-2 px-4 text-left">Last Interaction</th>
            <th className="py-2 px-4 text-left">Total Interactions</th>
            <th className="py-2 px-4 text-left">Company Contact</th>
          </tr>
        </thead>
        <tbody className="text-gray-700">
          {companies.map((company, index) => (
            <tr key={index} className={index % 2 === 0 ? "bg-gray-100" : ""}>
              <td className="py-2 px-4">{company.name}</td>
              <td className="py-2 px-4">{company.first_interaction_date}</td>
              <td className="py-2 px-4">{company.last_interaction_date}</td>
              <td className="py-2 px-4">{company.total_interactions}</td>
              <td className="py-2 px-4">{company.company_contact}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ResultsTable;
