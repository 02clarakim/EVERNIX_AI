"use client";
import { useState, Fragment } from "react";

export default function ResultsTable({ results, csvFile }) {
  const [expandedRows, setExpandedRows] = useState(new Set());

  if (!results || !Array.isArray(results) || results.length === 0) return null;

  // Main columns in order
  const mainColumns = ["symbol", "Company", "sector", "action", "confidence", "score", "rationale"];
  const allColumns = Object.keys(results[0]);
  const extraColumns = allColumns.filter((col) => !mainColumns.includes(col));

  const toggleRow = (symbol) => {
    const newSet = new Set(expandedRows);
    if (newSet.has(symbol)) newSet.delete(symbol);
    else newSet.add(symbol);
    setExpandedRows(newSet);
  };

  const handleDownload = () => {
    if (!csvFile) return;
    window.open(`http://localhost:8000/download/${csvFile}`, "_blank");
  };

  // Capitalize first letter
  const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1);

  // Tailwind colors for action
  const actionColor = (action) => {
    switch ((action || "").toUpperCase()) {
      case "BUY":
        return "bg-green-100 text-green-800 font-semibold";
      case "HOLD":
        return "bg-yellow-100 text-yellow-800 font-semibold";
      case "SELL":
        return "bg-red-100 text-red-800 font-semibold";
      default:
        return "";
    }
  };

  return (
    <div className="mt-10">
      <div className="overflow-x-auto">
        <table className="min-w-full border border-gray-300">
          <thead>
            <tr className="bg-gray-100">
              <th className="px-4 py-2 border"></th>
              {mainColumns.map((h) => (
                <th key={h} className="px-4 py-2 border text-left">
                  {capitalize(h === "name" ? "Company" : h)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.map((row, i) => (
              <Fragment key={row.symbol || i}>
                <tr className="hover:bg-gray-50">
                  <td
                    className="px-4 py-2 border cursor-pointer select-none"
                    onClick={() => toggleRow(row.symbol)}
                  >
                    {expandedRows.has(row.symbol) ? "▼" : "▶"}
                  </td>
                  {mainColumns.map((h) => (
                    <td
                      key={h}
                      className={`px-4 py-2 border ${
                        h === "action" ? actionColor(row[h]) : ""
                      }`}
                    >
                      {row[h] != null ? row[h].toString() : ""}
                    </td>
                  ))}
                </tr>
                {expandedRows.has(row.symbol) && extraColumns.length > 0 && (
                  <tr className="bg-gray-50">
                    <td></td>
                    <td colSpan={mainColumns.length}>
                      <div className="grid grid-cols-2 gap-4 p-2 text-sm">
                        {extraColumns.map((col) => (
                          <div key={col}>
                            <strong>{capitalize(col)}:</strong>{" "}
                            {row[col] != null ? row[col].toString() : ""}
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
          ))}

          </tbody>
        </table>
      </div>

      {/* Download CSV */}
      {csvFile && (
        <div className="text-right mt-4">
          <button
            onClick={handleDownload}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            Download CSV
          </button>
        </div>
      )}
    </div>
  );
}
