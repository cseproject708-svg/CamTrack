"use client";

import { useState, useEffect } from "react";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState<any>(null);

  const search = async () => {
    if (!query.trim()) return;
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    setResults(data);
    setSelected(null);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Search Students</h1>

      <div className="flex gap-3">
        <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && search()}
          placeholder="Search by name, roll number, email, or department..."
          className="flex-1 bg-gray-800 border border-gray-700 rounded px-4 py-2 text-white focus:outline-none focus:border-blue-500" />
        <button onClick={search} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded font-medium transition">
          Search
        </button>
      </div>

      {results.length > 0 && (
        <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800 bg-gray-900/50">
                <th className="text-left py-3 px-4">Name</th>
                <th className="text-left py-3 px-4">Roll No</th>
                <th className="text-left py-3 px-4">Department</th>
                <th className="text-left py-3 px-4">Hostel</th>
                <th className="text-left py-3 px-4">Room</th>
                <th className="text-left py-3 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {results.map((s: any) => (
                <tr key={s.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-3 px-4 text-white font-medium">{s.name}</td>
                  <td className="py-3 px-4 text-gray-400">{s.roll_number}</td>
                  <td className="py-3 px-4 text-gray-400">{s.department || "-"}</td>
                  <td className="py-3 px-4 text-gray-400">{s.hostel_name || "-"}</td>
                  <td className="py-3 px-4 text-gray-400">{s.room_number || "-"}</td>
                  <td className="py-3 px-4">
                    <button onClick={() => setSelected(s)} className="text-blue-400 hover:text-blue-300 text-sm">View Logs</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && <StudentLogs student={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function StudentLogs({ student, onClose }: { student: any; onClose: () => void }) {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    fetch(`/api/students/${student.id}/logs`).then(r => r.json()).then(setLogs);
  }, [student.id]);

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-white">Logs for {student.name}</h2>
        <button onClick={onClose} className="text-gray-500 hover:text-white">Close</button>
      </div>
      {logs.length === 0 ? (
        <p className="text-gray-500">No logs found.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 border-b border-gray-800">
              <th className="text-left py-2">Time</th>
              <th className="text-left py-2">Direction</th>
              <th className="text-left py-2">Camera</th>
              <th className="text-left py-2">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l: any) => (
              <tr key={l.id} className="border-b border-gray-800/50">
                <td className="py-2 text-gray-300">{new Date(l.timestamp).toLocaleString()}</td>
                <td className="py-2">
                  <span className={`px-2 py-1 rounded text-xs ${l.direction === "entry" ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
                    {l.direction.toUpperCase()}
                  </span>
                </td>
                <td className="py-2 text-gray-400">{l.camera_name}</td>
                <td className="py-2 text-gray-400">{(l.confidence * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
