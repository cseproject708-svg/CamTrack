"use client";

import { useState, useEffect } from "react";

export default function ReportsPage() {
  const [summary, setSummary] = useState<any>(null);
  const [daily, setDaily] = useState([]);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    fetch("/api/reports/summary").then(r => r.json()).then(setSummary);
    fetch("/api/logs/stats").then(r => r.json()).then(setStats);
    fetch("/api/reports/daily?days=14").then(r => r.json()).then(setDaily);
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Reports & Analytics</h1>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <ReportCard label="Total Entries" value={summary.total_entries} />
          <ReportCard label="Total Exits" value={summary.total_exits} />
          <ReportCard label="Unique Students" value={summary.unique_students} />
          <ReportCard label="Peak Hour" value={`${summary.peak_hour}:00`} />
          <ReportCard label="Avg Confidence" value={`${(summary.avg_confidence * 100).toFixed(1)}%`} />
          <ReportCard label="Spoof Attempts" value={summary.spoof_attempts} danger />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-lg font-semibold text-white mb-4">Daily Activity (14 days)</h2>
          {daily.length === 0 ? (
            <p className="text-gray-500">No data</p>
          ) : (
            <div className="space-y-2">
              {daily.reduce((acc: any, item: any) => {
                if (!acc[item.day]) acc[item.day] = { day: item.day, entry: 0, exit: 0 };
                acc[item.day][item.direction] = item.count;
                return acc;
              }, {}) && Object.values(
                daily.reduce((acc: any, item: any) => {
                  if (!acc[item.day]) acc[item.day] = { day: item.day, entry: 0, exit: 0 };
                  acc[item.day][item.direction] = item.count;
                  return acc;
                }, {})
              ).map((d: any) => (
                <div key={d.day} className="flex items-center gap-3 text-sm">
                  <span className="text-gray-400 w-24">{d.day}</span>
                  <div className="flex-1 flex gap-1">
                    <div className="bg-green-800 h-4 rounded" style={{ width: `${d.entry * 20}px` }} />
                    <span className="text-green-400 text-xs">{d.entry}</span>
                  </div>
                  <div className="flex-1 flex gap-1">
                    <div className="bg-red-800 h-4 rounded" style={{ width: `${d.exit * 20}px` }} />
                    <span className="text-red-400 text-xs">{d.exit}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-lg font-semibold text-white mb-4">Hourly Distribution (Today)</h2>
          {stats?.hourly?.length === 0 ? (
            <p className="text-gray-500">No data</p>
          ) : (
            <div className="space-y-1">
              {Array.from({ length: 24 }, (_, i) => {
                const hourData = stats?.hourly?.filter((h: any) => h.hour === i) || [];
                const entry = hourData.find((h: any) => h.direction === "entry")?.count || 0;
                const exit = hourData.find((h: any) => h.direction === "exit")?.count || 0;
                const total = entry + exit;
                return (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className="text-gray-500 w-10 text-right">{i}:00</span>
                    <div className="flex-1 bg-gray-800 rounded h-3 overflow-hidden">
                      <div className="bg-blue-600 h-full rounded" style={{ width: `${total * 15}%` }} />
                    </div>
                    <span className="text-gray-500 w-8 text-right">{total}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {stats?.top_students?.length > 0 && (
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-lg font-semibold text-white mb-4">Most Active Students (7 days)</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-2">#</th>
                <th className="text-left py-2">Student</th>
                <th className="text-left py-2">Roll No</th>
                <th className="text-left py-2">Visits</th>
              </tr>
            </thead>
            <tbody>
              {stats.top_students.map((s: any, i: number) => (
                <tr key={i} className="border-b border-gray-800/50">
                  <td className="py-2 text-gray-500">{i + 1}</td>
                  <td className="py-2 text-white">{s.name}</td>
                  <td className="py-2 text-gray-400">{s.roll_number}</td>
                  <td className="py-2 text-blue-400 font-medium">{s.visits}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ReportCard({ label, value, danger }: { label: string; value: any; danger?: boolean }) {
  return (
    <div className={`rounded-lg border p-4 ${danger ? "border-red-800 bg-red-900/20" : "border-gray-800 bg-gray-900"}`}>
      <p className="text-gray-400 text-sm">{label}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
    </div>
  );
}
