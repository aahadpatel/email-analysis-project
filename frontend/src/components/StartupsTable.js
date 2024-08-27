import React, { useState, useEffect } from "react";
import axios from "axios";
import { Link } from "react-router-dom";

const StartupsTable = () => {
  const [startups, setStartups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStartups = async () => {
      try {
        const response = await axios.get("http://localhost:5001/startups", {
          withCredentials: true,
        });
        setStartups(response.data);
        setLoading(false);
      } catch (err) {
        setError("Failed to fetch startups");
        setLoading(false);
      }
    };

    fetchStartups();
  }, []);

  if (loading) return <div className="text-center mt-8">Loading...</div>;
  if (error)
    return <div className="text-center mt-8 text-red-600">{error}</div>;

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Analyzed Startups</h1>
      <Link
        to="/dashboard"
        className="mb-4 inline-block bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
      >
        Back to Dashboard
      </Link>
      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-300">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                First Interaction
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Interaction
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Total Interactions
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Company Contact
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Analysis Date
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {startups.map((startup, index) => (
              <tr key={index}>
                <td className="px-6 py-4 whitespace-nowrap">{startup.name}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {startup.first_interaction_date}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {startup.last_interaction_date}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {startup.total_interactions}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {startup.company_contact}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {startup.analysis_date}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default StartupsTable;
