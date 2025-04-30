import React, { useState, useEffect, useRef } from "react";
import NavBar from "../components/NavBar.jsx";
import Button from "../components/Button.jsx";
import BeanScanner from "../components/BeanScanner.jsx";
import { db } from "../tools/firebase.js";
import { collection, doc, setDoc, getDoc, onSnapshot } from "firebase/firestore";
import { useAuth } from "../tools/AuthProvider.jsx";

const Machine = () => {
  const { currentUser, userLoggedIn } = useAuth();
  const [statusMessage, setStatusMessage] = useState("Connected to AI Coffee Machine");
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
  const [activeScanSlot, setActiveScanSlot] = useState(null);
  const [savingStatus, setSavingStatus] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [showCleanConfirmation, setShowCleanConfirmation] = useState(false);
  const [cleaningInProgress, setCleaningInProgress] = useState(false);
  const [cleaningProgress, setCleaningProgress] = useState(0);
  const [cleaningStepNumber, setCleaningStepNumber] = useState(0);
  const [cleaningTotalSteps, setCleaningTotalSteps] = useState(0);
  
  // Drum cleaning state variables
  const [drumCleaningInProgress, setDrumCleaningInProgress] = useState(false);
  const [drumCleaningProgress, setDrumCleaningProgress] = useState(0);
  const [showDrumCleanConfirmation, setShowDrumCleanConfirmation] = useState(false);

  // Assume we're always connected to the machine
  const deviceConnected = true;

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

  // Prevent page navigation during cleaning
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (cleaningInProgress || drumCleaningInProgress) {
        // Standard way to show a confirmation dialog when leaving a page
        e.preventDefault();
        e.returnValue = "Cleaning is in progress. Are you sure you want to leave?";
        return e.returnValue;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [cleaningInProgress, drumCleaningInProgress]);

  // Simulate cleaning progress updates
  useEffect(() => {
    let progressTimer;
    
    if (cleaningInProgress) {
      // Calculate total steps (increase + decrease + 1 for stop)
      const stepsIncrease = (8000 - 1250) / 250 + 1;
      const stepsDecrease = (8000 - 1250) / 250 + 1;
      const totalSteps = stepsIncrease + stepsDecrease + 1;
      setCleaningTotalSteps(totalSteps);
      
      let currentStep = 0;
      
      progressTimer = setInterval(() => {
        currentStep += 1;
        setCleaningStepNumber(currentStep);
        const progressPercent = Math.round((currentStep / totalSteps) * 100);
        setCleaningProgress(progressPercent);
        
        setLog((prev) => [...prev.slice(-19), `🧹 Cleaning step ${currentStep}/${totalSteps}: ${progressPercent}%`]);
        
        if (currentStep >= totalSteps) {
          clearInterval(progressTimer);
          setCleaningInProgress(false);
          setLog((prev) => [...prev.slice(-19), "🧹 Grinder cleaning completed"]);
        }
      }, 10000); // Update every 10 seconds
    }
    
    return () => {
      if (progressTimer) clearInterval(progressTimer);
    };
  }, [cleaningInProgress]);

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

  const handleManualBrew = () => {
    const payload = {
      type: "brew",
      temperature: settings.temperature,
      pressure: settings.pressure,
      grindSize: settings.grindSize,
      beanSlots,
    };

    console.log("Sending brew command:", payload);
    setLog((prev) => [
      ...prev,
      `▶️ Sent brew command: Temp=${settings.temperature}°C, Pressure=${settings.pressure} bar, Grind=${settings.grindSize}`,
    ]);
    alert("☕ Manual brew started!");
  };

  const startGrinderCleaning = () => {
    // Make API call to start grinder cleaning
    fetch('http://localhost:8000/grinder-clean', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ machine_ip: "128.197.180.251" }),
    })
      .then(response => response.json())
      .then(data => {
        console.log('Grinder cleaning started:', data);
        setLog((prev) => [...prev.slice(-19), "🧹 Grinder cleaning cycle started"]);
        setCleaningInProgress(true);
        setCleaningProgress(0);
        setCleaningStepNumber(0);
        setShowCleanConfirmation(false);
      })
      .catch(error => {
        console.error('Error starting grinder cleaning:', error);
        setLog((prev) => [...prev.slice(-19), `❌ Error starting grinder cleaning: ${error.message}`]);
        alert("Failed to start grinder cleaning. Please try again.");
        setShowCleanConfirmation(false);
      });
  };

  const startDrumCleaning = () => {
    // Make API call to start drum cleaning
    fetch('http://localhost:8000/drum-clean', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ machine_ip: "128.197.180.251" }),
    })
      .then(response => response.json())
      .then(data => {
        console.log('Drum cleaning started:', data);
        setLog((prev) => [...prev.slice(-19), "🧹 Drum cleaning cycle started"]);
        setDrumCleaningInProgress(true);
        setDrumCleaningProgress(0);
        setShowDrumCleanConfirmation(false);
        
        // Simulate progress for the 4-step cleaning process
        const totalTime = 20000; // Estimate total time in ms
        const steps = 4; // P-400-5, R-15000, D-60000, R-0
        let currentStep = 0;
        
        const progressTimer = setInterval(() => {
          currentStep += 1;
          const progressPercent = Math.round((currentStep / steps) * 100);
          setDrumCleaningProgress(progressPercent);
          
          setLog((prev) => [...prev.slice(-19), `🧹 Drum cleaning step ${currentStep}/${steps}: ${progressPercent}%`]);
          
          if (currentStep >= steps) {
            clearInterval(progressTimer);
            setDrumCleaningInProgress(false);
            setLog((prev) => [...prev.slice(-19), "🧹 Drum cleaning completed"]);
          }
        }, totalTime / steps); // Update based on estimated time per step
      })
      .catch(error => {
        console.error('Error starting drum cleaning:', error);
        setLog((prev) => [...prev.slice(-19), `❌ Error starting drum cleaning: ${error.message}`]);
        alert("Failed to start drum cleaning. Please try again.");
        setShowDrumCleanConfirmation(false);
      });
  };

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

        {/* Grinder Cleaning Section */}
        <section className="mb-8 bg-white p-6 rounded-lg border border-[var(--color-espresso)] shadow-sm">
          <h2 className="text-xl font-semibold text-[var(--color-roast)] mb-4">
            Grinder Maintenance
          </h2>
          
          <div className="mb-4">
            <p className="text-gray-700 mb-2">
              Run the grinder cleaning cycle to remove residual coffee particles and oils. 
              This process will gradually increase the grinder speed from 1250 to 8000 RPM and then decrease 
              back to 1250 RPM in 250 RPM increments.
            </p>
          </div>

          {!cleaningInProgress ? (
            <Button
              text="Run Grinder Cleaning Cycle"
              onClick={() => setShowCleanConfirmation(true)}
              color="#CF4137"
              className="w-full"
            />
          ) : (
            <div>
              <div className="mb-2 flex justify-between">
                <span className="text-sm font-medium">Cleaning Progress</span>
                <span className="text-sm font-medium">{cleaningProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-4 mb-4">
                <div 
                  className="bg-[var(--color-roast)] h-4 rounded-full" 
                  style={{ width: `${cleaningProgress}%` }}
                ></div>
              </div>
              <p className="text-center text-amber-600 font-semibold">
                Cleaning in progress - Please do not leave this page until completion
              </p>
            </div>
          )}

          {/* Confirmation Dialog */}
          {showCleanConfirmation && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg p-6 max-w-md w-full">
                <h3 className="text-lg font-semibold mb-4">Confirm Grinder Cleaning</h3>
                <p className="mb-4">
                  This will start a full grinder cleaning cycle that takes approximately 5 minutes to complete.
                  During this time:
                </p>
                <ul className="list-disc pl-5 mb-4 text-sm">
                  <li>The grinder will run at various speeds (1250-8000 RPM)</li>
                  <li>You will not be able to leave this page</li>
                  <li>No beans should be in the hopper</li>
                  <li><strong>This process cannot be canceled once started</strong></li>
                </ul>
                <p className="mb-6 font-semibold">Are you sure you want to proceed?</p>
                <div className="flex justify-end space-x-3">
                  <button 
                    className="px-4 py-2 rounded bg-gray-200 hover:bg-gray-300"
                    onClick={() => setShowCleanConfirmation(false)}
                  >
                    Cancel
                  </button>
                  <button 
                    className="px-4 py-2 rounded bg-[var(--color-roast)] text-white hover:bg-opacity-90"
                    onClick={startGrinderCleaning}
                  >
                    Start Cleaning
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Drum Cleaning Section */}
        <section className="mb-8 bg-white p-6 rounded-lg border border-[var(--color-espresso)] shadow-sm">
          <h2 className="text-xl font-semibold text-[var(--color-roast)] mb-4">
            Drum Maintenance
          </h2>
          
          <div className="mb-4">
            <p className="text-gray-700 mb-2">
              Run the drum cleaning cycle to remove residual coffee oils and particles from the roasting drum.
              This process will execute a specialized cleaning sequence to ensure proper maintenance of your roaster.
            </p>
          </div>

          {!drumCleaningInProgress ? (
            <Button
              text="Run Drum Cleaning Cycle"
              onClick={() => setShowDrumCleanConfirmation(true)}
              color="#8e7cc3"
              className="w-full"
            />
          ) : (
            <div>
              <div className="mb-2 flex justify-between">
                <span className="text-sm font-medium">Cleaning Progress</span>
                <span className="text-sm font-medium">{drumCleaningProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-4 mb-4">
                <div 
                  className="bg-[var(--color-roast)] h-4 rounded-full" 
                  style={{ width: `${drumCleaningProgress}%` }}
                ></div>
              </div>
              <p className="text-center text-amber-600 font-semibold">
                Drum cleaning in progress - Please do not leave this page until completion
              </p>
            </div>
          )}

          {/* Confirmation Dialog */}
          {showDrumCleanConfirmation && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg p-6 max-w-md w-full">
                <h3 className="text-lg font-semibold mb-4">Confirm Drum Cleaning</h3>
                <p className="mb-4">
                  This will start a full drum cleaning cycle that takes approximately 5 minutes to complete.
                  During this time:
                </p>
                <ul className="list-disc pl-5 mb-4 text-sm">
                  <li>The drum will execute a preset cleaning sequence</li>
                  <li>You will not be able to leave this page</li>
                  <li>Ensure the drum is empty before starting</li>
                  <li><strong>This process cannot be canceled once started</strong></li>
                </ul>
                <p className="mb-6 font-semibold">Are you sure you want to proceed?</p>
                <div className="flex justify-end space-x-3">
                  <button 
                    className="px-4 py-2 rounded bg-gray-200 hover:bg-gray-300"
                    onClick={() => setShowDrumCleanConfirmation(false)}
                  >
                    Cancel
                  </button>
                  <button 
                    className="px-4 py-2 rounded bg-[var(--color-roast)] text-white hover:bg-opacity-90"
                    onClick={startDrumCleaning}
                  >
                    Start Cleaning
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default Machine;