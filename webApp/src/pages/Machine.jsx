import React, { useState, useEffect, useRef } from "react";
import NavBar from "../components/NavBar.jsx";
import Button from "../components/Button.jsx";

const Machine = () => {
  const [deviceConnected, setDeviceConnected] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Not connected");
  const [settings, setSettings] = useState({
    temperature: 92,
    pressure: 9,
    grindSize: 5,
  });
  const [log, setLog] = useState([]);
  const socketRef = useRef(null);

  const handleConnect = () => {
    if (socketRef.current) return;

    const ws = new WebSocket("ws://192.168.4.1:81"); // Use your ESP32 WebSocket IP and port

    ws.onopen = () => {
      setDeviceConnected(true);
      setStatusMessage("Connected to AI Coffee Machine");
      setLog((prev) => [...prev, "Connected to ESP32 via WebSocket"]);
    };

    ws.onmessage = (event) => {
      setLog((prev) => [...prev.slice(-19), `📡 ${event.data}`]);
    };

    ws.onerror = (err) => {
      console.error("WebSocket Error:", err);
      setStatusMessage("Connection error");
    };

    ws.onclose = () => {
      setDeviceConnected(false);
      setStatusMessage("Disconnected");
      socketRef.current = null;
      setLog((prev) => [...prev, "Connection closed"]);
    };

    socketRef.current = ws;
  };

  const updateSetting = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleManualBrew = () => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      alert("Please connect to the machine first.");
      return;
    }

    const payload = {
      type: "brew",
      temperature: settings.temperature,
      pressure: settings.pressure,
      grindSize: settings.grindSize,
    };

    socketRef.current.send(JSON.stringify(payload));
    setLog((prev) => [
      ...prev,
      `▶️ Sent brew command: Temp=${settings.temperature}°C, Pressure=${settings.pressure} bar, Grind=${settings.grindSize}`,
    ]);
    alert("☕ Manual brew started!");
  };

  useEffect(() => {
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  return (
    <div className="min-h-screen bg-[var(--color-mint)]">
      <NavBar />
      <div className="pt-24 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-extrabold text-[var(--color-roast)] mb-6">
          Machine Control Center
        </h1>

        <section className="mb-8 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-lg font-medium text-[var(--color-espresso)]">
              Status: {statusMessage}
            </p>
            <Button
              text={deviceConnected ? "Connected" : "Connect"}
              onClick={handleConnect}
              disabled={deviceConnected}
              color="#386150"
            />
          </div>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-semibold text-[var(--color-roast)] mb-4">
            Manual Brew Settings
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div>
              <label className="block text-sm font-medium text-[var(--color-roast)] mb-1">
                Temperature (°C): {settings.temperature}
              </label>
              <input
                type="range"
                min="85"
                max="96"
                value={settings.temperature}
                onChange={(e) => updateSetting("temperature", Number(e.target.value))}
                className="w-full accent-[var(--color-hgreen)]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-roast)] mb-1">
                Pressure (bar): {settings.pressure}
              </label>
              <input
                type="range"
                min="6"
                max="12"
                value={settings.pressure}
                onChange={(e) => updateSetting("pressure", Number(e.target.value))}
                className="w-full accent-[var(--color-hgreen)]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-roast)] mb-1">
                Grind Size: {settings.grindSize}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={settings.grindSize}
                onChange={(e) => updateSetting("grindSize", Number(e.target.value))}
                className="w-full accent-[var(--color-hgreen)]"
              />
            </div>
          </div>
          <div className="mt-6">
            <Button
              text="Start Manual Brew"
              onClick={handleManualBrew}
              color="#386150"
            />
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-[var(--color-roast)] mb-2">
            Live Log
          </h2>
          <div className="bg-white border border-[var(--color-espresso)] rounded p-4 max-h-64 overflow-y-auto text-sm text-[var(--color-espresso)] shadow-sm">
            {log.length === 0 ? (
              <p className="text-gray-500 italic">No activity yet.</p>
            ) : (
              log.map((entry, idx) => <p key={idx}>• {entry}</p>)
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

export default Machine;
