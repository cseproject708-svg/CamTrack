import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Campus Gate Access Control",
  description: "Face recognition-based hostel gate management system",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen">
          <aside className="w-64 bg-gray-900 border-r border-gray-800 p-4 flex flex-col">
            <h1 className="text-xl font-bold text-white mb-8">
              Campus Gate
            </h1>
            <nav className="flex flex-col gap-1 flex-1">
              <a href="/" className="px-3 py-2 rounded hover:bg-gray-800 text-gray-300 hover:text-white transition">Dashboard</a>
              <a href="/register" className="px-3 py-2 rounded hover:bg-gray-800 text-gray-300 hover:text-white transition">Student Register</a>
              <a href="/recognition" className="px-3 py-2 rounded hover:bg-gray-800 text-gray-300 hover:text-white transition">Face Recognition</a>
              <a href="/logs" className="px-3 py-2 rounded hover:bg-gray-800 text-gray-300 hover:text-white transition">Gate Logs</a>
              <a href="/search" className="px-3 py-2 rounded hover:bg-gray-800 text-gray-300 hover:text-white transition">Search</a>
              <a href="/reports" className="px-3 py-2 rounded hover:bg-gray-800 text-gray-300 hover:text-white transition">Reports</a>
              <a href="/data" className="px-3 py-2 rounded hover:bg-gray-800 text-gray-300 hover:text-white transition">Data Management</a>
              <a href="/admin" className="px-3 py-2 rounded hover:bg-gray-800 text-gray-300 hover:text-white transition mt-auto">Admin</a>
            </nav>
          </aside>
          <main className="flex-1 p-6 overflow-auto">{children}</main>
        </div>
      </body>
    </html>
  );
}
