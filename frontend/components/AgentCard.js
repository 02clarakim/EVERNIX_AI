// components/AgentCard.jsx
"use client";

export default function AgentCard({ name, description, selected, onSelect }) {
  return (
    <div
      onClick={onSelect}
      className={`
        cursor-pointer p-6 rounded-lg border transition
        ${selected ? "border-blue-700 bg-blue-50" : "border-gray-300 hover:border-gray-500"}
        hover:shadow-md
      `}
    >
      <h2 className="text-xl font-semibold mb-2">{name}</h2>
      <p className="text-gray-600 text-sm">{description}</p>
    </div>
  );
}
