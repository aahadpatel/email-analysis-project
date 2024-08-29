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
  const [deleteConfirmation, setDeleteConfirmation] = useState(null);
  const [totalStartups, setTotalStartups] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [startupsPerPage] = useState(10); // You can adjust this number as needed

  useEffect(() => {
    const fetchStartups = async () => {
      try {
        const response = await axios.get("http://localhost:5001/startups", {
          withCredentials: true,
        });
        const startupsWithIds = response.data.map((startup) => ({
          ...startup,
          id: startup.id || startup.name,
        }));
        setStartups(startupsWithIds);
        setFilteredStartups(startupsWithIds);
        setTotalStartups(startupsWithIds.length);
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

    if (interactionFilter !== "") {
      filtered = filtered.filter(
        (startup) => startup.total_interactions >= parseInt(interactionFilter)
      );
    }

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

  const handleDeleteClick = (startup) => {
    setDeleteConfirmation(startup);
  };

  const confirmDelete = async () => {
    try {
      if (!deleteConfirmation || !deleteConfirmation.name) {
        throw new Error("Invalid startup selected for deletion");
      }
      await axios.delete(
        `http://localhost:5001/startups/${encodeURIComponent(
          deleteConfirmation.name
        )}`,
        {
          withCredentials: true,
        }
      );
      const updatedStartups = startups.filter(
        (s) => s.name !== deleteConfirmation.name
      );
      setStartups(updatedStartups);
      setFilteredStartups(
        filteredStartups.filter((s) => s.name !== deleteConfirmation.name)
      );
      setTotalStartups(updatedStartups.length);
      setDeleteConfirmation(null);
    } catch (err) {
      console.error("Failed to delete startup:", err);
      setError(`Failed to delete startup: ${err.message}`);
    }
  };

  const cancelDelete = () => {
    setDeleteConfirmation(null);
  };

  const extractCSV = () => {
    // Define the headers
    const headers = [
      "Name",
      "First Interaction Date",
      "Last Interaction Date",
      "Total Interactions",
      "Company Contact",
      "Analysis Date",
    ];

    // Convert the data to CSV format
    const csvContent = [
      headers.join(","), // Add headers as the first row
      ...filteredStartups.map((startup) =>
        [
          startup.name,
          startup.first_interaction_date,
          startup.last_interaction_date,
          startup.total_interactions,
          startup.company_contact,
          startup.analysis_date,
        ].join(",")
      ),
    ].join("\n");

    // Create a Blob with the CSV content
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });

    // Create a download link and trigger the download
    const link = document.createElement("a");
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute("href", url);
      link.setAttribute("download", "startups_data.csv");
      link.style.visibility = "hidden";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  // Calculate pagination values
  const indexOfLastStartup = currentPage * startupsPerPage;
  const indexOfFirstStartup = indexOfLastStartup - startupsPerPage;
  const currentStartups = filteredStartups.slice(
    indexOfFirstStartup,
    indexOfLastStartup
  );
  const totalPages = Math.ceil(filteredStartups.length / startupsPerPage);

  // Change page
  const paginate = (pageNumber) => setCurrentPage(pageNumber);

  if (loading) return <div className="text-center mt-8">Loading...</div>;
  if (error)
    return <div className="text-center mt-8 text-red-600">{error}</div>;

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <h1 className="text-3xl font-bold mb-6">Analyzed Startups</h1>
          <div className="flex justify-between items-center mb-4">
            <Link
              to="/dashboard"
              className="inline-block bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            >
              Back to Dashboard
            </Link>
            <button
              onClick={extractCSV}
              className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded"
            >
              Extract CSV
            </button>
          </div>
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
          <div className="mb-4">
            <p>
              Total number of startups: <strong>{totalStartups}</strong>
            </p>
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
                  <th scope="col" className="px-6 py-3">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {currentStartups.map((startup) => (
                  <tr
                    key={startup.id}
                    className="bg-white border-b hover:bg-gray-50"
                  >
                    <td className="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">
                      <a
                        href={`https://${startup.name}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        {startup.name}
                      </a>
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
                    <td className="px-6 py-4">
                      <button
                        onClick={() => handleDeleteClick(startup)}
                        className="font-medium text-red-600 hover:underline"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredStartups.length > 1 && (
            <div className="mt-4 flex justify-center">
              <nav
                className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px"
                aria-label="Pagination"
              >
                <button
                  onClick={() => paginate(currentPage - 1)}
                  disabled={currentPage === 1}
                  className={`relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 ${
                    currentPage === 1 ? "cursor-not-allowed" : ""
                  }`}
                >
                  Previous
                </button>
                {[...Array(totalPages).keys()].map((number) => (
                  <button
                    key={number + 1}
                    onClick={() => paginate(number + 1)}
                    className={`relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium ${
                      currentPage === number + 1
                        ? "text-blue-600 bg-blue-50"
                        : "text-gray-700 hover:bg-gray-50"
                    }`}
                  >
                    {number + 1}
                  </button>
                ))}
                <button
                  onClick={() => paginate(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className={`relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 ${
                    currentPage === totalPages ? "cursor-not-allowed" : ""
                  }`}
                >
                  Next
                </button>
              </nav>
            </div>
          )}

          {deleteConfirmation && (
            <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
              <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
                <h3 className="text-lg font-bold">Confirm Deletion</h3>
                <p className="mt-2">
                  Are you sure you want to delete {deleteConfirmation.name}?
                </p>
                <div className="mt-3 flex justify-end space-x-2">
                  <button
                    onClick={cancelDelete}
                    className="px-4 py-2 bg-gray-300 text-black rounded hover:bg-gray-400"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmDelete}
                    className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StartupsTable;
