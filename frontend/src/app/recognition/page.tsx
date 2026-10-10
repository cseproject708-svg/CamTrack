"use client";

import { useState, useRef, useEffect, useCallback } from "react";

interface FaceResult {
  bbox: number[];
  name: string;
  confidence: number;
  is_live: boolean;
  spoof: boolean;
  liveness_warning?: boolean;
}

const QUALITY_LABELS: Record<string, string> = {
  too_dark: "Too dark — move to better light",
  too_bright: "Too bright / backlit",
  low_contrast: "Low contrast",
  strong_color_cast: "Color cast (tube-light?)",
  blurry: "Blurry — hold still",
};

export default function RecognitionPage() {
  const [active, setActive] = useState(false);
  const [results, setResults] = useState<FaceResult[]>([]);
  const [qualityWarnings, setQualityWarnings] = useState<string[]>([]);
  const [recentLogs, setRecentLogs] = useState<any[]>([]);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const drawOverlays = useCallback((faces: FaceResult[]) => {
    const overlay = overlayRef.current;
    const video = videoRef.current;
    if (!overlay || !video || !video.videoWidth) return;

    const ctx = overlay.getContext("2d");
    if (!ctx) return;

    overlay.width = video.videoWidth;
    overlay.height = video.videoHeight;
    ctx.clearRect(0, 0, overlay.width, overlay.height);

    for (const face of faces) {
      const [x1, y1, x2, y2] = face.bbox;
      const w = x2 - x1;
      const h = y2 - y1;

      let color = "#22c55e";
      let bgColor = "rgba(34, 197, 94, 0.12)";
      let label = face.name;
      let sublabel = `${(face.confidence * 100).toFixed(1)}%`;

      if (face.spoof) {
        color = "#ef4444";
        bgColor = "rgba(239, 68, 68, 0.12)";
        label = "SPOOF";
        sublabel = "Non-live face";
      } else if (face.name === "Unknown") {
        color = "#eab308";
        bgColor = "rgba(234, 179, 8, 0.12)";
        label = "Unknown";
        sublabel = `${(face.confidence * 100).toFixed(1)}%`;
      }

      ctx.fillStyle = bgColor;
      ctx.fillRect(x1, y1, w, h);

      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(x1, y1, w, h);

      const cornerLen = Math.min(20, w * 0.25, h * 0.25);
      ctx.strokeStyle = color;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(x1, y1 + cornerLen); ctx.lineTo(x1, y1); ctx.lineTo(x1 + cornerLen, y1);
      ctx.moveTo(x2 - cornerLen, y1); ctx.lineTo(x2, y1); ctx.lineTo(x2, y1 + cornerLen);
      ctx.moveTo(x2, y2 - cornerLen); ctx.lineTo(x2, y2); ctx.lineTo(x2 - cornerLen, y2);
      ctx.moveTo(x1 + cornerLen, y2); ctx.lineTo(x1, y2); ctx.lineTo(x1, y2 - cornerLen);
      ctx.stroke();

      ctx.font = "bold 18px sans-serif";
      const textWidth = ctx.measureText(label).width;
      const labelH = 26;
      const labelY = y1 - labelH - 4;

      ctx.fillStyle = color;
      ctx.fillRect(x1, labelY, textWidth + 12, labelH);
      ctx.fillStyle = "#000";
      ctx.fillText(label, x1 + 6, labelY + 18);

      if (sublabel) {
        ctx.font = "13px sans-serif";
        const subW = ctx.measureText(sublabel).width;
        ctx.fillStyle = "rgba(0,0,0,0.6)";
        ctx.fillRect(x1, y2 + 4, subW + 10, 20);
        ctx.fillStyle = color;
        ctx.fillText(sublabel, x1 + 5, y2 + 18);
      }
    }
  }, []);

  const processFrame = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d")!;
    canvas.width = videoRef.current.videoWidth || 640;
    canvas.height = videoRef.current.videoHeight || 480;
    ctx.drawImage(videoRef.current, 0, 0);

    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const fd = new FormData();
      fd.append("file", blob, "frame.jpg");
      try {
        const res = await fetch("/api/recognition/recognize", { method: "POST", body: fd });
        if (res.ok) {
          const data = await res.json();
          const faces = data.faces || [];
          setResults(faces);
          drawOverlays(faces);
          setQualityWarnings(data.quality?.warnings || []);
          const newLogs = data.logs || [];
          if (newLogs.length > 0) {
            setRecentLogs(prev => [...newLogs, ...prev].slice(0, 50));
          }
        }
      } catch {}
    }, "image/jpeg", 0.92);
  }, [drawOverlays]);

  const startRecognition = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      setActive(true);
      setResults([]);
      intervalRef.current = setInterval(processFrame, 1000);
    } catch {
      alert("Camera access denied");
    }
  };

  const stopRecognition = () => {
    streamRef.current?.getTracks().forEach(t => t.stop());
    if (intervalRef.current) clearInterval(intervalRef.current);
    setActive(false);
    setResults([]);
    const overlay = overlayRef.current;
    if (overlay) {
      const ctx = overlay.getContext("2d");
      if (ctx) ctx.clearRect(0, 0, overlay.width, overlay.height);
    }
  };

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach(t => t.stop());
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">Face Recognition</h1>

      <div className="flex gap-4 items-center">
        {!active ? (
          <button onClick={startRecognition} className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded font-medium transition">
            Start Recognition
          </button>
        ) : (
          <button onClick={stopRecognition} className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded font-medium transition">
            Stop
          </button>
        )}
        <span className={`px-3 py-1 rounded text-sm ${active ? "bg-green-900 text-green-300" : "bg-gray-800 text-gray-500"}`}>
          {active ? "LIVE" : "STOPPED"}
        </span>
      </div>

      {active && qualityWarnings.length > 0 && (
        <div className="bg-yellow-900/30 border border-yellow-700 rounded p-3 text-yellow-300 text-sm">
          Lighting: {qualityWarnings.map(w => QUALITY_LABELS[w] || w).join(" · ")}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-lg font-semibold text-white mb-3">Camera Feed</h2>
          <div className="relative inline-block w-full">
            <video ref={videoRef} className="rounded border border-gray-700 w-full bg-black" autoPlay muted />
            <canvas ref={overlayRef} className="absolute top-0 left-0 w-full h-full rounded pointer-events-none" />
            <canvas ref={canvasRef} className="hidden" />
          </div>
        </div>

        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-lg font-semibold text-white mb-3">Detection Results</h2>
          {results.length === 0 ? (
            <p className="text-gray-500 py-8 text-center">No faces detected</p>
          ) : (
            <div className="space-y-2">
              {results.map((r, i) => (
                <div key={i} className={`p-3 rounded border ${r.spoof ? "border-red-800 bg-red-900/20" : r.name === "Unknown" ? "border-yellow-800 bg-yellow-900/20" : "border-green-800 bg-green-900/20"}`}>
                  <div className="flex justify-between items-center">
                    <span className="text-white font-medium">
                      {r.spoof ? "SPOOF DETECTED" : r.name}
                    </span>
                    <span className="text-sm text-gray-400">
                      {r.spoof ? "" : `${(r.confidence * 100).toFixed(1)}%`}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {r.spoof ? "Non-live face detected" : r.is_live ? "Live face" : "Liveness uncertain — logged with warning"}
                  </div>
                  {r.liveness_warning && (
                    <div className="text-xs text-yellow-400 mt-1">Poor lighting/blur — liveness low confidence, check lighting</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {recentLogs.length > 0 && (
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
          <h2 className="text-lg font-semibold text-white mb-3">Recent Activity</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-2 px-3">Time</th>
                  <th className="text-left py-2 px-3">Student</th>
                  <th className="text-left py-2 px-3">Direction</th>
                  <th className="text-left py-2 px-3">Camera</th>
                </tr>
              </thead>
              <tbody>
                {recentLogs.map((log: any, i: number) => (
                  <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-2 px-3 text-gray-300">{new Date(log.timestamp).toLocaleTimeString()}</td>
                    <td className="py-2 px-3 text-white font-medium">{log.student_name}</td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${log.direction === "entry" ? "bg-green-900 text-green-300" : "bg-red-900 text-red-300"}`}>
                        {log.direction === "entry" ? "ENTRY" : "EXIT"}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-gray-400">{log.camera_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
