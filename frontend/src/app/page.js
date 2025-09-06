"use client";

import { useState } from "react";
import AgentCard from "../../components/AgentCard";
import UniverseSelector from "../../components/UniverseSelector";
import ResultsTable from "../../components/ResultsTable";

export default function Home() {
  const [agents] = useState([
    { id: "buffett", name: "Buffett", description: "Long-term value investing, focusing on high-quality companies at reasonable prices" },
    { id: "ackman", name: "Ackman", description: "Activist and trend-aware investing, targeting high-conviction opportunities" },
    { id: "oversight", name: "Oversight", description: "Ensemble oversight of agents" },
  ]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [universe, setUniverse] = useState([]);
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;


  const handleGenerate = async () => {
    if (!selectedAgent || universe.length === 0) {
      alert("Please select an agent and at least one company.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent: selectedAgent, universe, include_oversight: true }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      setResults({
        selected: data.selected_results,
        selected_csv: data.selected_csv,
        oversight: data.oversight_results,
        oversight_csv: data.oversight_csv,
      });
    } catch (err) {
      console.error("Failed to fetch results:", err);
      alert("Failed to fetch results from backend. Check console for details.");
    }
    setLoading(false);
  };

  return (
    <main className="max-w-5xl mx-auto py-12 space-y-8 px-4">
      <h1 className="text-3xl font-bold text-center">EVERNIX Investment Agents</h1>

      {/* Agent Cards (only Buffett and Ackman) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {agents
          .filter((a) => a.id === "buffett" || a.id === "ackman")
          .map((a) => (
            <AgentCard
              key={a.id}
              name={a.name}
              description={a.description}
              selected={selectedAgent === a.id}
              onSelect={() => setSelectedAgent(a.id)}
            />
          ))}
      </div>

      {/* Universe Selector */}
      <UniverseSelector onChange={setUniverse} />

      {/* Generate Button */}
      <div className="text-center">
        <button
          onClick={handleGenerate}
          disabled={loading}
          className={`bg-[#003366] text-white px-6 py-3 rounded-lg shadow hover:bg-blue-700 transition ${
            loading ? "opacity-50 cursor-not-allowed" : ""
          }`}
        >
          {loading ? "Generating..." : "Generate"}
        </button>
      </div>

      {/* Selected Agent Results */}
      {results.selected?.length > 0 && (
        <div className="space-y-2">
          <ResultsTable results={results.selected} />
          {results.selected_csv && (
            <div className="text-right">
              <a
                href={`${apiUrl}/download/${results.selected_csv}`}
                className="inline-block bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition"
                download
              >
                Download CSV
              </a>
            </div>
          )}
        </div>
      )}

      {/* Oversight Results */}
      {results.oversight?.length > 0 && (
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">Oversight Agent Result</h2>
          <ResultsTable results={results.oversight} />
        </div>
      )}
    </main>
  );
}
