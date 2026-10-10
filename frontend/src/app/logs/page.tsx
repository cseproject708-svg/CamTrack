"use client";

import { useState, useEffect } from "react";

export default function LogsPage() {
  const [logs, setLogs] = useState([]);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    const fetchLogs = () => fetch("/api/logs?limit=200").then(r => r.json()).then(setLogs);
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  const filtered = filter === "all" ? logs : logs.filter((l: any) => l.direction === filter);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Gate Logs</h1>

      <div className="flex gap-3">
        {["all", "entry", "exit"].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded text-sm font-medium transition ${filter === f ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>
            {f.toUpperCase()}
          </button>
        ))}
        <span className="ml-auto text-gray-500 text-sm self-center">{filtered.length} records</span>
      </div>

      <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400 border-b border-gray-800 bg-gray-900/50">
              <th className="text-left py-3 px-4">Time</th>
              <th className="text-left py-3 px-4">Student</th>
              <th className="text-left py-3 px-4">Roll No</th>
              <th className="text-left py-3 px-4">Direction</th>
              <th className="text-left py-3 px-4">Camera</th>
              <th className="text-left py-3 px-4">Confidence</th>
              <th className="text-left py-3 px-4">Liveness</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((log: any) => (
              <tr key={log.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="py-3 px-4 text-gray-300">{new Date(log.timestamp).toLocaleString()}</td>
                <td className="py-3 px-4 text-white">{log.student_name}</td>
                <td className="py-3 px-4 text-gray-400">{log.roll_number}</td>
                <td className="py-3 px-4">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${log.direction === "entry" ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
                    {log.direction === "entry" ? "ENTRY" : "EXIT"}
                  </span>
                </td>
                <td className="py-3 px-4 text-gray-400">{log.camera_name}</td>
                <td className="py-3 px-4 text-gray-400">{(log.confidence * 100).toFixed(1)}%</td>
                <td className="py-3 px-4">
                  <span className={`text-xs ${log.is_live ? "text-green-400" : "text-red-400"}`}>
                    {log.is_live ? "Live" : "Spoof"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
