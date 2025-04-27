import React, { useState, useEffect, useRef } from "react";
import NavBar from "../components/NavBar.jsx";
import Button from "../components/Button.jsx";
import BeanScanner from "../components/BeanScanner.jsx";
import { db } from "../tools/firebase.js";
import { collection, doc, setDoc, getDoc, onSnapshot } from "firebase/firestore";
import { useAuth } from "../tools/AuthProvider.jsx";

const Machine = () => {
  const { currentUser, userLoggedIn } = useAuth();
  const [deviceConnected, setDeviceConnected] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Not connected");
  const [settings, setSettings] = useState({
    temperature: 92,
    pressure: 9,
    grindSize: 5,
  });
  const defaultBeanConfig = [
    { name: "", type: "arabica", roast: "medium", notes: "" },
    { name: "", type: "arabica", roast: "medium", notes: "" },
    { name: "", type: "arabica", roast: "medium", notes: "" },
  ];
  
  const [beanSlots, setBeanSlots] = useState(defaultBeanConfig);
  const [log, setLog] = useState([]);
  const socketRef = useRef(null);
  const [activeScanSlot, setActiveScanSlot] = useState(null);
  const [savingStatus, setSavingStatus] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    if (!currentUser || !userLoggedIn) return;

    const beansDocRef = doc(db, "users", currentUser.uid, "beans", "configuration");

    getDoc(beansDocRef)
      .then((docSnap) => {
        if (docSnap.exists()) {
          const data = docSnap.data();
          if (data.slots) {
            setBeanSlots(data.slots);
            if (data.updatedAt) {
              setLastUpdated(data.updatedAt.toDate());
            }
            console.log("Loaded saved bean configuration from Firebase");
            setLog((prev) => [...prev, "Loaded saved bean configuration"]);
          }
        } else {
          setDoc(beansDocRef, {
            slots: defaultBeanConfig,
            createdAt: new Date(),
            updatedAt: new Date()
          })
            .then(() => {
              console.log("Created new bean configuration in Firebase");
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

    const unsubscribe = onSnapshot(
      beansDocRef,
      (doc) => {
        if (doc.exists()) {
          const data = doc.data();
          if (data.slots) {
            setBeanSlots(data.slots);
            if (data.updatedAt) {
              setLastUpdated(data.updatedAt.toDate());
            }
            console.log("Real-time update: Bean configuration changed in Firebase");
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

  const saveBeanConfiguration = async (updatedSlots) => {
    if (!currentUser || !userLoggedIn) {
      console.log("Cannot save: User not logged in");
      setLog((prev) => [...prev, "Cannot save: User not logged in"]);
      setSavingStatus("Error: Not logged in");
      return;
    }
    
    try {
      setSavingStatus("Saving...");
      console.log("Saving bean configuration to Firebase...");
      
      await setDoc(doc(db, "users", currentUser.uid, "beans", "configuration"), {
        slots: updatedSlots,
        updatedAt: new Date()
      });

      setLastUpdated(new Date());
      
      console.log("Bean configuration saved successfully");
      setLog((prev) => [...prev.slice(-19), "Bean configuration saved to cloud"]);
      setSavingStatus("Saved!");
      
      setTimeout(() => {
        setSavingStatus("");
      }, 2000);
    } catch (error) {
      console.error("Error saving bean configuration:", error);
      setLog((prev) => [...prev, `Error saving bean data: ${error.message}`]);
      setSavingStatus(`Error: ${error.message}`);
    }
  };

  const updateBeanSlot = (index, field, value) => {
    console.log(`Updating bean slot ${index}, field: ${field}, value: ${value}`);
    const updated = [...beanSlots];
    updated[index][field] = value;
    setBeanSlots(updated);
    saveBeanConfiguration(updated);
  };
  
  const handleScanComplete = (slotIndex, beanInfo) => {
    console.log(`Scan completed for slot ${slotIndex}:`, beanInfo);
    const slotArrayIndex = slotIndex - 1;
    const updated = [...beanSlots];
    updated[slotArrayIndex] = {
      ...updated[slotArrayIndex],
      ...beanInfo
    };
    setBeanSlots(updated);
    saveBeanConfiguration(updated);
    setActiveScanSlot(null);
    setLog((prev) => [...prev.slice(-19), `📷 Scanned bean info for slot ${slotIndex}: ${beanInfo.name}`]);
  };

  const handleConnect = () => {
    if (socketRef.current) return;

    const ws = new WebSocket("ws://128.197.180.251");

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

  // Helper function for nicer time format
  const formatDateTime = (date) => {
    return date.toLocaleString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  return (
    <div className="min-h-screen bg-[var(--color-mint)]">
      <NavBar />
      <div className="pt-24 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-extrabold text-[var(--color-roast)] mb-6">
          Machine Control Center
        </h1>

        <section className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-[var(--color-roast)]">
              Bean Slots Configuration
            </h2>
            {savingStatus && (
              <div className="text-sm font-medium px-3 py-1 rounded bg-white">
                {savingStatus}
              </div>
            )}
          </div>

          {activeScanSlot !== null && (
            <BeanScanner 
              onScanComplete={handleScanComplete} 
              slotIndex={activeScanSlot} 
              onCancel={() => setActiveScanSlot(null)}
            />
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {beanSlots.map((slot, idx) => (
              <div
                key={idx}
                className="border border-[var(--color-espresso)] rounded p-4 bg-white shadow-sm"
              >
                <div className="flex justify-between items-center mb-3">
                <h3 className="font-semibold text-[var(--color-roast)]">
                  Slot {String.fromCharCode(65 + idx)}
                </h3>
                  <Button
                    text="Scan Bag"
                    onClick={() => setActiveScanSlot(idx + 1)}
                    color="#386150"
                    className="text-xs py-1 px-2"
                  />
                </div>
                <input
                  className="w-full mb-2 p-2 border rounded"
                  placeholder="Bean Name (scan bag or enter manually)"
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
                  placeholder="Flavor notes (scan bag or enter manually)"
                  value={slot.notes}
                  onChange={(e) => updateBeanSlot(idx, "notes", e.target.value)}
                />
              </div>
            ))}
          </div>

          <div className="mt-4 text-center text-sm text-gray-600">
            {lastUpdated ? (
              <p>Last updated: {formatDateTime(lastUpdated)}</p>
            ) : (
              <p>Loading last updated time...</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

export default Machine;
