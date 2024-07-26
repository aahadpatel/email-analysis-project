import React, { useState } from "react";

const ProgressGuide = () => {
  const [isOpen, setIsOpen] = useState(false);

  const guideContent = [
    {
      term: "Status",
      description: "The current stage of the email analysis process.",
    },
    {
      term: "Processed Emails",
      description:
        "The number of individual emails that have been analyzed out of the total emails found.",
    },
    {
      term: "Analyzed Companies",
      description:
        "The number of unique companies identified from the email domains that have been analyzed.",
    },
    {
      term: "Identified Startups",
      description:
        "The number of companies that our AI has classified as potential startups based on the email content.",
    },
  ];

  return (
    <div className="fixed bottom-0 left-0 w-full bg-gray-100 border-t border-gray-300 p-2">
      <button
        className="text-blue-600 hover:text-blue-800 text-sm font-medium"
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? "Hide Guide" : "Show Guide"}
      </button>
      {isOpen && (
        <div className="mt-2 text-sm">
          {guideContent.map((item, index) => (
            <div key={index} className="mb-2">
              <span className="font-semibold">{item.term}:</span>{" "}
              {item.description}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProgressGuide;
