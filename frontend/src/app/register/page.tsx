"use client";

import { useState, useRef, useEffect, useCallback } from "react";

type Phase = "form" | "camera" | "capturing" | "uploading" | "retraining" | "done";

export default function RegisterPage() {
  const [form, setForm] = useState({
    roll_number: "", name: "", email: "", phone: "",
    department: "", year_of_study: "", hostel_id: "", room_id: "",
  });
  const [hostels, setHostels] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [phase, setPhase] = useState<Phase>("form");
  const [captured, setCaptured] = useState(0);
  const [faceDetected, setFaceDetected] = useState(false);
  const [faceBox, setFaceBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const [message, setMessage] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const captureIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const framesRef = useRef<Blob[]>([]);
  const animFrameRef = useRef<number>(0);

  useEffect(() => {
    fetch("/api/data/hostels").then(r => r.json()).then(setHostels).catch(() => {});
    fetch("/api/data/rooms").then(r => r.json()).then(setRooms).catch(() => {});
  }, []);

  useEffect(() => {
    return () => {
      stopCamera();
      if (captureIntervalRef.current) clearInterval(captureIntervalRef.current);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = 0;
    }
  }, []);

  const detectFace = useCallback((video: HTMLVideoElement, overlay: HTMLCanvasElement) => {
    const ctx = overlay.getContext("2d");
    if (!ctx) return;

    const draw = () => {
      if (!video.videoWidth || video.paused || video.ended) {
        animFrameRef.current = 0;
        return;
      }

      overlay.width = video.videoWidth;
      overlay.height = video.videoHeight;
      ctx.clearRect(0, 0, overlay.width, overlay.height);

      const tempCanvas = document.createElement("canvas");
      tempCanvas.width = video.videoWidth;
      tempCanvas.height = video.videoHeight;
      const tempCtx = tempCanvas.getContext("2d");
      if (!tempCtx) return;

      tempCtx.drawImage(video, 0, 0);
      const imageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
      const data = imageData.data;

      let sumX = 0, sumY = 0, count = 0;
      const w = tempCanvas.width;
      const h = tempCanvas.height;

      for (let y = 0; y < h; y += 4) {
        for (let x = 0; x < w; x += 4) {
          const i = (y * w + x) * 4;
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];

          const isSkin = r > 95 && g > 40 && b > 20 &&
            r > g && r > b &&
            Math.abs(r - g) > 15 &&
            r - Math.min(g, b) > 15;

          if (isSkin) {
            sumX += x;
            sumY += y;
            count++;
          }
        }
      }

      if (count > 150) {
        const cx = sumX / count;
        const cy = sumY / count;
        const spread = Math.sqrt(count) * 2.5;
        const boxW = Math.min(spread * 2, w * 0.7);
        const boxH = Math.min(spread * 2.5, h * 0.8);
        const boxX = Math.max(0, cx - boxW / 2);
        const boxY = Math.max(0, cy - boxH / 2);

        setFaceDetected(true);
        setFaceBox({ x: boxX, y: boxY, w: boxW, h: boxH });

        ctx.strokeStyle = "#22c55e";
        ctx.lineWidth = 3;
        ctx.strokeRect(boxX, boxY, boxW, boxH);

        ctx.fillStyle = "rgba(34, 197, 94, 0.15)";
        ctx.fillRect(boxX, boxY, boxW, boxH);

        const cornerLen = 20;
        ctx.strokeStyle = "#22c55e";
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(boxX, boxY + cornerLen); ctx.lineTo(boxX, boxY); ctx.lineTo(boxX + cornerLen, boxY);
        ctx.moveTo(boxX + boxW - cornerLen, boxY); ctx.lineTo(boxX + boxW, boxY); ctx.lineTo(boxX + boxW, boxY + cornerLen);
        ctx.moveTo(boxX + boxW, boxY + boxH - cornerLen); ctx.lineTo(boxX + boxW, boxY + boxH); ctx.lineTo(boxX + boxW - cornerLen, boxY + boxH);
        ctx.moveTo(boxX + cornerLen, boxY + boxH); ctx.lineTo(boxX, boxY + boxH); ctx.lineTo(boxX, boxY + boxH - cornerLen);
        ctx.stroke();

        ctx.font = "bold 16px sans-serif";
        ctx.fillStyle = "#22c55e";
        ctx.fillText("Face Detected", boxX, boxY - 10);
      } else {
        setFaceDetected(false);
        setFaceBox(null);

        const centerX = w / 2;
        const centerY = h / 2;
        const radius = Math.min(w, h) * 0.25;

        ctx.strokeStyle = "rgba(251, 191, 36, 0.6)";
        ctx.lineWidth = 2;
        ctx.setLineDash([10, 5]);
        ctx.beginPath();
        ctx.ellipse(centerX, centerY, radius, radius * 1.3, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.font = "14px sans-serif";
        ctx.fillStyle = "rgba(251, 191, 36, 0.8)";
        ctx.textAlign = "center";
        ctx.fillText("Position your face here", centerX, centerY + radius * 1.3 + 25);
        ctx.textAlign = "start";
      }

      animFrameRef.current = requestAnimationFrame(draw);
    };

    animFrameRef.current = requestAnimationFrame(draw);
  }, []);

  const captureSingleFrame = useCallback((rollNumber: string, index: number): Promise<boolean> => {
    return new Promise((resolve) => {
      if (!videoRef.current || !canvasRef.current) {
        resolve(false);
        return;
      }

      const video = videoRef.current;
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      if (!ctx) { resolve(false); return; }

      canvas.width = 128;
      canvas.height = 128;
      ctx.drawImage(video, 0, 0, 128, 128);

      canvas.toBlob((blob) => {
        if (blob) {
          framesRef.current.push(blob);
          resolve(true);
        } else {
          resolve(false);
        }
      }, "image/jpeg", 0.9);
    });
  }, []);

  const startAutoCapture = useCallback(async (rollNumber: string) => {
    setPhase("capturing");
    setCaptured(0);
    framesRef.current = [];

    const totalFrames = 100;
    const intervalMs = 100;

    let count = 0;
    captureIntervalRef.current = setInterval(async () => {
      if (count >= totalFrames) {
        if (captureIntervalRef.current) clearInterval(captureIntervalRef.current);
        captureIntervalRef.current = null;
        await uploadAndFinish(rollNumber);
        return;
      }

      const ok = await captureSingleFrame(rollNumber, count);
      if (ok) {
        count++;
        setCaptured(count);
      }
    }, intervalMs);
  }, [captureSingleFrame]);

  const uploadAndFinish = useCallback(async (rollNumber: string) => {
    setPhase("uploading");
    setMessage("Uploading photos...");
    stopCamera();

    const fd = new FormData();
    fd.append("roll_number", rollNumber);
    fd.append("name", form.name);
    if (form.email) fd.append("email", form.email);
    if (form.phone) fd.append("phone", form.phone);
    if (form.department) fd.append("department", form.department);
    if (form.year_of_study) fd.append("year_of_study", form.year_of_study);
    if (form.hostel_id) fd.append("hostel_id", form.hostel_id);
    if (form.room_id) fd.append("room_id", form.room_id);

    framesRef.current.forEach((blob, i) => {
      fd.append("photos", blob, `${rollNumber}_${i}.jpg`);
    });

    try {
      const res = await fetch("/api/data/register-student", { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json();
        setErrorMsg(err.detail || "Upload failed");
        setPhase("form");
        return;
      }

      setMessage("Retraining model...");
      setPhase("retraining");

      const retrainRes = await fetch("/api/data/retrain", { method: "POST" });
      if (!retrainRes.ok) {
        setMessage("Photos saved, but retraining failed. Run retrain manually.");
      } else {
        setMessage("Registration complete! Model updated.");
      }

      setPhase("done");
      setForm({ roll_number: "", name: "", email: "", phone: "", department: "", year_of_study: "", hostel_id: "", room_id: "" });
    } catch {
      setErrorMsg("Connection error during upload");
      setPhase("form");
    }
  }, [form, stopCamera]);

  const handleFormSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setMessage("");

    if (!form.roll_number || !form.name) {
      setErrorMsg("Roll Number and Name are required");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" }
      });
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setPhase("camera");
      setMessage("Camera ready. Capturing face photos...");

      setTimeout(() => {
        if (overlayRef.current && videoRef.current) {
          detectFace(videoRef.current, overlayRef.current);
        }
        startAutoCapture(form.roll_number);
      }, 800);
    } catch {
      setErrorMsg("Camera access denied. Please allow camera and try again.");
    }
  }, [form, detectFace, startAutoCapture]);

  const resetAll = useCallback(() => {
    stopCamera();
    setPhase("form");
    setCaptured(0);
    setFaceDetected(false);
    setFaceBox(null);
    setMessage("");
    setErrorMsg("");
    framesRef.current = [];
  }, [stopCamera]);

  const progressPercent = phase === "capturing" ? Math.round((captured / 100) * 100) : 0;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold text-white">Student Registration</h1>

      {phase === "done" ? (
        <div className="bg-gray-900 rounded-lg border border-green-700 p-8 text-center space-y-4">
          <div className="text-5xl">&#10003;</div>
          <h2 className="text-2xl font-bold text-green-400">Registration Complete</h2>
          <p className="text-gray-400">{message}</p>
          <button onClick={resetAll} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded font-medium transition mt-4">
            Register Another Student
          </button>
        </div>
      ) : phase === "form" ? (
        <form onSubmit={handleFormSubmit} className="bg-gray-900 rounded-lg border border-gray-800 p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="Roll Number *" value={form.roll_number} onChange={v => setForm(f => ({ ...f, roll_number: v }))} />
            <Input label="Full Name *" value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} />
            <Input label="Email" value={form.email} onChange={v => setForm(f => ({ ...f, email: v }))} />
            <Input label="Phone" value={form.phone} onChange={v => setForm(f => ({ ...f, phone: v }))} />
            <Input label="Department" value={form.department} onChange={v => setForm(f => ({ ...f, department: v }))} />
            <Input label="Year" value={form.year_of_study} onChange={v => setForm(f => ({ ...f, year_of_study: v }))} type="number" />
            <Select label="Hostel" value={form.hostel_id} onChange={v => setForm(f => ({ ...f, hostel_id: v }))} options={hostels.map((h: any) => ({ value: h.id, label: h.name }))} />
            <Select label="Room" value={form.room_id} onChange={v => setForm(f => ({ ...f, room_id: v }))} options={rooms.map((r: any) => ({ value: r.id, label: r.room_number }))} />
          </div>
          <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded font-medium transition">
            Register & Capture Photos
          </button>
        </form>
      ) : (
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">
              {phase === "camera" && "Initializing Camera..."}
              {phase === "capturing" && "Capturing Face Photos"}
              {phase === "uploading" && "Uploading..."}
              {phase === "retraining" && "Retraining Model..."}
            </h2>
            {(phase === "camera" || phase === "capturing") && (
              <button onClick={resetAll} className="text-gray-400 hover:text-white text-sm transition">
                Cancel
              </button>
            )}
          </div>

          <div className="relative inline-block">
            <video
              ref={videoRef}
              className="rounded border border-gray-700 bg-black"
              style={{ width: 480, height: 360 }}
              autoPlay
              muted
              playsInline
            />
            <canvas
              ref={overlayRef}
              className="absolute top-0 left-0 rounded"
              style={{ width: 480, height: 360, pointerEvents: "none" }}
            />
            <canvas ref={canvasRef} className="hidden" />
          </div>

          {phase === "capturing" && (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-gray-800 rounded-full h-3 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-200"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <span className="text-white font-mono text-sm w-16 text-right">{captured}/100</span>
              </div>

              <div className="flex gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${faceDetected ? "bg-green-500" : "bg-yellow-500 animate-pulse"}`} />
                  <span className={faceDetected ? "text-green-400" : "text-yellow-400"}>
                    {faceDetected ? "Face detected" : "Searching for face..."}
                  </span>
                </div>
                <span className="text-gray-500">|</span>
                <span className="text-gray-400">{Math.round(progressPercent)}% complete</span>
              </div>

              {!faceDetected && (
                <p className="text-yellow-400 text-sm">
                  Please position your face in the center of the frame. Look straight at the camera.
                </p>
              )}
            </div>
          )}

          {(phase === "uploading" || phase === "retraining") && (
            <div className="flex items-center gap-3">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500" />
              <span className="text-gray-300">{message}</span>
            </div>
          )}
        </div>
      )}

      {errorMsg && (
        <div className="bg-red-900/30 border border-red-700 rounded p-3 text-red-400 text-sm">
          {errorMsg}
        </div>
      )}
      {message && phase === "form" && (
        <div className="bg-blue-900/30 border border-blue-700 rounded p-3 text-blue-400 text-sm">
          {message}
        </div>
      )}
    </div>
  );
}

function Input({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <div>
      <label className="block text-sm text-gray-400 mb-1">{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)}
        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
    </div>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: { value: number; label: string }[] }) {
  return (
    <div>
      <label className="block text-sm text-gray-400 mb-1">{label}</label>
      <select value={value} onChange={e => onChange(e.target.value)}
        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500">
        <option value="">Select...</option>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}
