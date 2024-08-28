import React, { useState, useEffect } from "react";
import axios from "axios";
import { Link } from "react-router-dom";

const StartupsTable = () => {
  const [startups, setStartups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filteredStartups, setFilteredStartups] = useState([]);
  const [interactionFilter, setInteractionFilter] = useState("");
  const [sortColumn, setSortColumn] = useState("name");
  const [sortDirection, setSortDirection] = useState("asc");

  useEffect(() => {
    const fetchStartups = async () => {
      try {
        const response = await axios.get("http://localhost:5001/startups", {
          withCredentials: true,
        });
        setStartups(response.data);
        setFilteredStartups(response.data);
        setLoading(false);
      } catch (err) {
        setError("Failed to fetch startups");
        setLoading(false);
      }
    };

    fetchStartups();
  }, []);

  useEffect(() => {
    filterAndSortStartups();
  }, [interactionFilter, sortColumn, sortDirection, startups]);

  const filterAndSortStartups = () => {
    let filtered = [...startups];

    // Apply interaction filter
    if (interactionFilter !== "") {
      filtered = filtered.filter(
        (startup) => startup.total_interactions >= parseInt(interactionFilter)
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      if (a[sortColumn] < b[sortColumn])
        return sortDirection === "asc" ? -1 : 1;
      if (a[sortColumn] > b[sortColumn])
        return sortDirection === "asc" ? 1 : -1;
      return 0;
    });

    setFilteredStartups(filtered);
  };

  const handleSort = (column) => {
    if (column === sortColumn) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  if (loading) return <div className="text-center mt-8">Loading...</div>;
  if (error)
    return <div className="text-center mt-8 text-red-600">{error}</div>;

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <h1 className="text-3xl font-bold mb-6">Analyzed Startups</h1>
          <Link
            to="/dashboard"
            className="mb-4 inline-block bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            Back to Dashboard
          </Link>
          <div className="mb-4">
            <label htmlFor="interactionFilter" className="mr-2">
              Minimum Interactions:
            </label>
            <input
              type="number"
              id="interactionFilter"
              value={interactionFilter}
              onChange={(e) => setInteractionFilter(e.target.value)}
              className="border rounded px-2 py-1"
            />
          </div>
          <div className="mt-4 overflow-x-auto shadow-md sm:rounded-lg">
            <table className="w-full text-sm text-left text-gray-500">
              <thead className="text-xs text-gray-700 uppercase bg-gray-50">
                <tr>
                  <th
                    scope="col"
                    className="px-6 py-3 cursor-pointer"
                    onClick={() => handleSort("name")}
                  >
                    Name{" "}
                    {sortColumn === "name" &&
                      (sortDirection === "asc" ? "▲" : "▼")}
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3 cursor-pointer"
                    onClick={() => handleSort("first_interaction_date")}
                  >
                    First Interaction{" "}
                    {sortColumn === "first_interaction_date" &&
                      (sortDirection === "asc" ? "▲" : "▼")}
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3 cursor-pointer"
                    onClick={() => handleSort("last_interaction_date")}
                  >
                    Last Interaction{" "}
                    {sortColumn === "last_interaction_date" &&
                      (sortDirection === "asc" ? "▲" : "▼")}
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3 cursor-pointer"
                    onClick={() => handleSort("total_interactions")}
                  >
                    Total Interactions{" "}
                    {sortColumn === "total_interactions" &&
                      (sortDirection === "asc" ? "▲" : "▼")}
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3 cursor-pointer"
                    onClick={() => handleSort("company_contact")}
                  >
                    Company Contact{" "}
                    {sortColumn === "company_contact" &&
                      (sortDirection === "asc" ? "▲" : "▼")}
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-3 cursor-pointer"
                    onClick={() => handleSort("analysis_date")}
                  >
                    Analysis Date{" "}
                    {sortColumn === "analysis_date" &&
                      (sortDirection === "asc" ? "▲" : "▼")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredStartups.map((startup, index) => (
                  <tr
                    key={index}
                    className="bg-white border-b hover:bg-gray-50"
                  >
                    <td className="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">
                      {startup.name}
                    </td>
                    <td className="px-6 py-4">
                      {startup.first_interaction_date}
                    </td>
                    <td className="px-6 py-4">
                      {startup.last_interaction_date}
                    </td>
                    <td className="px-6 py-4">{startup.total_interactions}</td>
                    <td className="px-6 py-4">{startup.company_contact}</td>
                    <td className="px-6 py-4">{startup.analysis_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StartupsTable;
