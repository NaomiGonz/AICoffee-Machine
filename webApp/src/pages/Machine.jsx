import React, { useState, useEffect, useRef } from "react";
import NavBar from "../components/NavBar.jsx";
import Button from "../components/Button.jsx";
import { db } from "../tools/firebase.js";
import { collection, doc, setDoc, getDoc, onSnapshot } from "firebase/firestore";
import { useAuth } from "../tools/AuthProvider.jsx"; // Using your AuthProvider

const Machine = () => {
  const { currentUser, userLoggedIn } = useAuth();
  const [deviceConnected, setDeviceConnected] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Not connected");
  const [settings, setSettings] = useState({
    temperature: 92,
    pressure: 9,
    grindSize: 5,
  });
  // Default bean configuration
  const defaultBeanConfig = [
    { name: "", type: "arabica", roast: "medium", notes: "" },
    { name: "", type: "arabica", roast: "medium", notes: "" },
    { name: "", type: "arabica", roast: "medium", notes: "" },
  ];
  
  const [beanSlots, setBeanSlots] = useState(defaultBeanConfig);
  const [log, setLog] = useState([]);
  const socketRef = useRef(null);

  // Load beans data from Firestore on component mount
  useEffect(() => {
    if (!currentUser || !userLoggedIn) return;

    const beansDocRef = doc(db, "users", currentUser.uid, "beans", "configuration");
    
    // First, try to get existing data
    getDoc(beansDocRef)
      .then((docSnap) => {
        if (docSnap.exists()) {
          const data = docSnap.data();
          if (data.slots) {
            setBeanSlots(data.slots);
            setLog((prev) => [...prev, "Loaded saved bean configuration"]);
          }
        } else {
          // Document doesn't exist, create it with default configuration
          setDoc(beansDocRef, {
            slots: defaultBeanConfig,
            createdAt: new Date(),
            updatedAt: new Date()
          })
            .then(() => {
              setLog((prev) => [...prev, "Created new bean configuration"]);
            })
            .catch((error) => {
              console.error("Error creating default bean configuration:", error);
              setLog((prev) => [...prev, `Error creating bean configuration: ${error.message}`]);
            });
        }
      })
      .catch((error) => {
        console.error("Error loading bean data:", error);
        setLog((prev) => [...prev, `Error loading bean data: ${error.message}`]);
      });
      
    // Set up real-time listener for future updates
    const unsubscribe = onSnapshot(
      beansDocRef,
      (doc) => {
        if (doc.exists()) {
          const data = doc.data();
          if (data.slots) {
            setBeanSlots(data.slots);
            setLog((prev) => [...prev.slice(-19), "Bean configuration updated"]);
          }
        }
      },
      (error) => {
        console.error("Error in beans snapshot listener:", error);
      }
    );

    return () => unsubscribe();
  }, [currentUser, userLoggedIn]);

  const handleConnect = () => {
    if (socketRef.current) return;

    const ws = new WebSocket("ws://128.197.180.251"); // Use your ESP32 WebSocket IP and port

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

  const updateBeanSlot = (index, field, value) => {
    const updated = [...beanSlots];
    updated[index][field] = value;
    setBeanSlots(updated);
    
    // Save updated beans to Firestore
    saveBeanConfiguration(updated);
  };
  
  const saveBeanConfiguration = async (updatedSlots) => {
    if (!currentUser || !userLoggedIn) {
      setLog((prev) => [...prev, "Cannot save: User not logged in"]);
      return;
    }
    
    try {
      await setDoc(doc(db, "users", currentUser.uid, "beans", "configuration"), {
        slots: updatedSlots,
        updatedAt: new Date()
      });
      setLog((prev) => [...prev.slice(-19), "Bean configuration saved to cloud"]);
    } catch (error) {
      console.error("Error saving bean configuration:", error);
      setLog((prev) => [...prev, `Error saving bean data: ${error.message}`]);
    }
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
      beanSlots,
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

        <section className="mb-12">
          <h2 className="text-xl font-semibold text-[var(--color-roast)] mb-4">
            Bean Slots Configuration
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {beanSlots.map((slot, idx) => (
              <div
                key={idx}
                className="border border-[var(--color-espresso)] rounded p-4 bg-white shadow-sm"
              >
                <h3 className="font-semibold text-[var(--color-roast)] mb-2">
                  Slot {idx + 1}
                </h3>
                <input
                  className="w-full mb-2 p-2 border rounded"
                  placeholder="Bean Name (optional)"
                  value={slot.name}
                  onChange={(e) => updateBeanSlot(idx, "name", e.target.value)}
                />
                <select
                  className="w-full mb-2 p-2 border rounded"
                  value={slot.type}
                  onChange={(e) => updateBeanSlot(idx, "type", e.target.value)}
                >
                  <option value="arabica">Arabica</option>
                  <option value="robusta">Robusta</option>
                  <option value="blend">Blend</option>
                </select>
                <select
                  className="w-full mb-2 p-2 border rounded"
                  value={slot.roast}
                  onChange={(e) => updateBeanSlot(idx, "roast", e.target.value)}
                >
                  <option value="light">Light Roast</option>
                  <option value="medium">Medium Roast</option>
                  <option value="dark">Dark Roast</option>
                </select>
                <textarea
                  className="w-full p-2 border rounded"
                  rows="2"
                  placeholder="Flavor notes (optional)"
                  value={slot.notes}
                  onChange={(e) => updateBeanSlot(idx, "notes", e.target.value)}
                />
              </div>
            ))}
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