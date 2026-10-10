"use client";

import { useState, useEffect } from "react";

export default function DashboardPage() {
  const [status, setStatus] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      fetch("/api/status").then(r => r.json()),
      fetch("/api/logs/today").then(r => r.json()),
    ])
      .then(([s, l]) => { setStatus(s); setLogs(l); })
      .catch(() => setError("Failed to connect to backend. Make sure the server is running on port 8000."));
  }, []);

  if (error) return <div className="text-red-400 p-8">{error}</div>;
  if (!status) return <div className="text-gray-500 p-8">Loading...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard title="Students Inside" value={status.students_inside} color="green" />
        <StatCard title="Today's Logs" value={status.today_logs} color="blue" />
        <StatCard title="Total Students" value={status.total_students} color="purple" />
        <StatCard title="Cameras" value={status.total_cameras} color="yellow" />
        <StatCard title="Gate Window" value={status.time_window_open ? "Open" : "Closed"} color={status.time_window_open ? "green" : "red"} />
      </div>

      <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
        <h2 className="text-lg font-semibold text-white mb-4">Today&apos;s Activity</h2>
        {logs.length === 0 ? (
          <p className="text-gray-500">No activity today.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-2">Time</th>
                <th className="text-left py-2">Student</th>
                <th className="text-left py-2">Direction</th>
                <th className="text-left py-2">Camera</th>
                <th className="text-left py-2">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {logs.slice(0, 10).map((log: any) => (
                <tr key={log.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 text-gray-300">{new Date(log.timestamp).toLocaleTimeString()}</td>
                  <td className="py-2 text-white">{log.student_name}</td>
                  <td className="py-2">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${log.direction === "entry" ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
                      {log.direction === "entry" ? "ENTER" : "EXIT"}
                    </span>
                  </td>
                  <td className="py-2 text-gray-400">{log.camera_name}</td>
                  <td className="py-2 text-gray-400">{(log.confidence * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function StatCard({ title, value, color }: { title: string; value: any; color: string }) {
  const colors: Record<string, string> = {
    green: "border-green-800 bg-green-900/20",
    blue: "border-blue-800 bg-blue-900/20",
    purple: "border-purple-800 bg-purple-900/20",
    yellow: "border-yellow-800 bg-yellow-900/20",
    red: "border-red-800 bg-red-900/20",
  };
  return (
    <div className={`rounded-lg border p-4 ${colors[color] || colors.blue}`}>
      <p className="text-gray-400 text-sm">{title}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
    </div>
  );
}
