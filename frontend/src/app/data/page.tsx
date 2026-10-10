"use client";

import { useState, useEffect } from "react";

export default function DataPage() {
  const [students, setStudents] = useState([]);
  const [hostels, setHostels] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [tab, setTab] = useState("students");

  useEffect(() => {
    fetch("/api/students").then(r => r.json()).then(setStudents);
    fetch("/api/data/hostels").then(r => r.json()).then(setHostels);
    fetch("/api/data/cameras").then(r => r.json()).then(setCameras);
  }, []);

  const deleteStudent = async (id: number) => {
    if (!confirm("Delete this student?")) return;
    await fetch(`/api/students/${id}`, { method: "DELETE" });
    setStudents(s => s.filter((st: any) => st.id !== id));
  };

  const clearOldLogs = async () => {
    if (!confirm("Clear logs older than 90 days?")) return;
    const res = await fetch("/api/data/clear-logs?days=90", { method: "DELETE" });
    const data = await res.json();
    alert(`Deleted ${data.deleted} old log records`);
  };

  const exportData = async () => {
    const res = await fetch("/api/data/export");
    const data = await res.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "students_export.json";
    a.click();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Data Management</h1>

      <div className="flex gap-3">
        {["students", "hostels", "cameras"].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 rounded text-sm font-medium transition ${tab === t ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"}`}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === "students" && (
        <div className="space-y-4">
          <div className="flex gap-3">
            <button onClick={exportData} className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm transition">
              Export JSON
            </button>
            <button onClick={clearOldLogs} className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded text-sm transition">
              Clear Old Logs (90d)
            </button>
          </div>
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
                {students.map((s: any) => (
                  <tr key={s.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-3 px-4 text-white">{s.name}</td>
                    <td className="py-3 px-4 text-gray-400">{s.roll_number}</td>
                    <td className="py-3 px-4 text-gray-400">{s.department || "-"}</td>
                    <td className="py-3 px-4 text-gray-400">{s.hostel_name || "-"}</td>
                    <td className="py-3 px-4 text-gray-400">{s.room_number || "-"}</td>
                    <td className="py-3 px-4">
                      <button onClick={() => deleteStudent(s.id)} className="text-red-400 hover:text-red-300 text-sm">Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "hostels" && (
        <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-3 px-4">Name</th>
                <th className="text-left py-3 px-4">Address</th>
              </tr>
            </thead>
            <tbody>
              {hostels.map((h: any) => (
                <tr key={h.id} className="border-b border-gray-800/50">
                  <td className="py-3 px-4 text-white">{h.name}</td>
                  <td className="py-3 px-4 text-gray-400">{h.address || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "cameras" && (
        <div className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-3 px-4">Name</th>
                <th className="text-left py-3 px-4">Location</th>
                <th className="text-left py-3 px-4">Hostel</th>
                <th className="text-left py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {cameras.map((c: any) => (
                <tr key={c.id} className="border-b border-gray-800/50">
                  <td className="py-3 px-4 text-white">{c.name}</td>
                  <td className="py-3 px-4 text-gray-400">{c.location}</td>
                  <td className="py-3 px-4 text-gray-400">{c.hostel_name || "-"}</td>
                  <td className="py-3 px-4">
                    <span className={`text-xs ${c.is_active ? "text-green-400" : "text-red-400"}`}>
                      {c.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
