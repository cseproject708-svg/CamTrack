"use client";

import { useState } from "react";

export default function AdminPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loggedIn, setLoggedIn] = useState(false);
  const [message, setMessage] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage("");
    try {
      const res = await fetch("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (data.success) {
        setLoggedIn(true);
        setMessage(`Welcome, ${data.user.full_name}!`);
      } else {
        setMessage("Invalid credentials");
      }
    } catch {
      setMessage("Connection error");
    }
  };

  if (loggedIn) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-white">Admin Panel</h1>
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-6">
          <p className="text-green-400 mb-6">{message}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <a href="/register" className="block bg-gray-800 hover:bg-gray-750 border border-gray-700 rounded-lg p-4 transition">
              <h3 className="text-white font-medium">Student Registration</h3>
              <p className="text-gray-400 text-sm mt-1">Register new students and capture face data</p>
            </a>
            <a href="/data" className="block bg-gray-800 hover:bg-gray-750 border border-gray-700 rounded-lg p-4 transition">
              <h3 className="text-white font-medium">Data Management</h3>
              <p className="text-gray-400 text-sm mt-1">Import, export, and manage system data</p>
            </a>
            <a href="/reports" className="block bg-gray-800 hover:bg-gray-750 border border-gray-700 rounded-lg p-4 transition">
              <h3 className="text-white font-medium">Reports</h3>
              <p className="text-gray-400 text-sm mt-1">View analytics and generate reports</p>
            </a>
            <a href="/logs" className="block bg-gray-800 hover:bg-gray-750 border border-gray-700 rounded-lg p-4 transition">
              <h3 className="text-white font-medium">Gate Logs</h3>
              <p className="text-gray-400 text-sm mt-1">Review all entry and exit records</p>
            </a>
          </div>
          <button onClick={() => { setLoggedIn(false); setUsername(""); setPassword(""); }}
            className="mt-6 text-gray-500 hover:text-white text-sm transition">
            Logout
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto space-y-6">
      <h1 className="text-3xl font-bold text-white text-center">Admin Login</h1>
      <form onSubmit={handleLogin} className="bg-gray-900 rounded-lg border border-gray-800 p-6 space-y-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Username</label>
          <input value={username} onChange={e => setUsername(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500" />
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Password</label>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500" />
        </div>
        <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded font-medium transition">
          Login
        </button>
        {message && <p className="text-red-400 text-sm text-center">{message}</p>}
        <p className="text-gray-600 text-xs text-center">Default: admin / admin123</p>
      </form>
    </div>
  );
}
