import React, { useState, useEffect } from "react";
import { getAuth } from "firebase/auth";
import NavBar from "../components/NavBar.jsx";
import CoffeeCard from "../components/CoffeeCard.jsx";
import FeedbackModal from "../components/FeedbackModal.jsx";
import MachineCodeVisualization from "../components/MachineCodeVisualization";

import col from "../assets/col.jpeg";
import eth from "../assets/eth.webp";
import arm from "../assets/amer.jpeg";
import ken from "../assets/ken.webp";
import bra from "../assets/bra.webp";
import sam from "../assets/sam.webp";

const featuredCoffees = [
  { id: 1, name: "Colombian Roast", image: col, description: "Rich and bold" },
  { id: 2, name: "Ethiopian Espresso", image: eth, description: "Fruity and aromatic" },
  { id: 3, name: "Americano Blend", image: arm, description: "Smooth and balanced" },
  { id: 4, name: "Kenyan AA", image: ken, description: "Bright acidity" },
  { id: 5, name: "Sumatra Mandheling", image: sam, description: "Earthy and intense" },
  { id: 6, name: "Brazilian Santos", image: bra, description: "Nutty and sweet" },
];

const exampleQueries = [
  "Fruity espresso",
  "Large cappuccino",
  "Nutty pour-over",
  "Strong dark roast",
  "Smooth coffee",
  "Ethiopian light roast"
];

const Home = () => {
  const [queryInput, setQueryInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [brewResult, setBrewResult] = useState(null);
  const [showExamples, setShowExamples] = useState(false);
  const [servingSize, setServingSize] = useState(7);
  const [brewHistory, setBrewHistory] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");
  const [selectedBrewId, setSelectedBrewId] = useState(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [showRawCommands, setShowRawCommands] = useState(false);
  const [brewProgress, setBrewProgress] = useState(0);
  const [brewProgressSource, setBrewProgressSource] = useState(null);
  const [isSendingToMachine, setIsSendingToMachine] = useState(false);

  const auth = getAuth();
  const user = auth.currentUser;

  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      console.error("Timestamp parsing error:", error);
      return "Unknown Date";
    }
  };

  useEffect(() => {
    const fetchBrewHistory = async () => {
      if (!user) return;

      try {
        const token = await user.getIdToken();
        const response = await fetch(`http://localhost:8000/history/${user.uid}`, {
          method: "GET",
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
          }
        });

        if (!response.ok) throw new Error(`API error: ${response.status}`);

        const data = await response.json();
        setBrewHistory(data.history || []);
      } catch (error) {
        console.error("Error fetching brew history:", error);
        setErrorMessage("Could not fetch brew history");
      }
    };

    fetchBrewHistory();
  }, [user]);

  const ServingSizeSelector = () => {
    const sizes = [
      { label: '3 oz', value: 3 },
      { label: '7 oz', value: 7 },
      { label: '10 oz', value: 10 }
    ];

    return (
      <div className="flex space-x-2 mb-4">
        <p className="text-sm font-medium text-gray-700 mr-2">Serving Size:</p>
        {sizes.map((size) => (
          <button
            key={size.value}
            onClick={() => setServingSize(size.value)}
            className={`px-3 py-1.5 text-xs rounded-md border ${
              servingSize === size.value 
                ? 'bg-[var(--color-hgreen)] text-white' 
                : 'bg-white text-gray-700 border-gray-300'
            }`}
          >
            {size.label}
          </button>
        ))}
      </div>
    );
  };

  const getBrewStageLabelSmart = (commands, progress) => {
    if (!commands || commands.length === 0) return "Preparing...";
  
    // Figure out which command index we are approximately at
    const index = Math.floor((progress / 100) * commands.length);
    const command = commands[Math.min(index, commands.length - 1)]; // Safety to not go out of bounds
  
    if (!command) return "Processing...";
  
    if (command.startsWith("G-")) return "Grinding Beans...";
    if (command.startsWith("H-")) return "Heating Water...";
    if (command.startsWith("P-")) return "Brewing Coffee...";
    if (command.startsWith("R-")) return "Mixing and Rotating...";
    
    return "Finalizing Brew...";
  };  

  const handleSaveFeedback = async (brewId, rating, notes = "") => {
    if (!user) {
      alert("User not authenticated. Please log in.");
      return;
    }

    const brew = brewHistory.find(b => b.brew_id === brewId);
    if (brew && brew.feedback) {
      alert("You've already rated this brew.");
      return;
    }

    try {
      const token = await user.getIdToken();
      const response = await fetch("http://localhost:8000/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: user.uid,
          brew_id: brewId,
          rating,
          notes
        })
      });

      if (!response.ok) throw new Error(`Feedback submission error: ${response.status}`);

      const historyResponse = await fetch(`http://localhost:8000/history/${user.uid}`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      });

      if (historyResponse.ok) {
        const historyData = await historyResponse.json();
        setBrewHistory(historyData.history || []);
      }

      alert("Feedback saved successfully!");
    } catch (error) {
      console.error("Feedback submission error:", error);
      alert("Could not save feedback");
    }
  };

  const handleExecuteHistoricalBrew = async (brewId) => {
    if (!user) {
      alert("User not authenticated. Please log in.");
      return;
    }

    try {
      setIsLoading(true);
      const token = await user.getIdToken();
      const response = await fetch(`http://localhost:8000/execute-brew/${user.uid}/${brewId}`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      });

      if (!response.ok) throw new Error(`Execute brew error: ${response.status}`);

      const data = await response.json();
      alert("Brew executed successfully!");
      console.log("Brew execution result:", data);
    } catch (error) {
      console.error("Brew execution error:", error);
      alert("Could not execute brew");
    } finally {
      setIsLoading(false);
    }
  };

  const handleNaturalLanguageQuery = async (query = queryInput) => {
    if (!query.trim()) {
      alert("Please enter a coffee request");
      return;
    }
  
    if (!user) {
      alert("User not authenticated. Please log in.");
      return;
    }
  
    try {
      setIsLoading(true);
      setIsSendingToMachine(true);
      setErrorMessage("");
      const token = await user.getIdToken();
  
      const response = await fetch("http://localhost:8000/brew", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          query,
          serving_size: servingSize,
          user_id: user.uid,
        }),
      });
  
      if (!response.ok) throw new Error(`API error: ${response.status}`);
  
      const data = await response.json();
      setBrewResult(data);
  
      if (data.brew_id) {
        const source = new EventSource(`http://localhost:8000/brew-progress/${data.brew_id}`);
        setBrewProgressSource(source);
  
        source.onmessage = (event) => {
          const parsedData = JSON.parse(event.data);
          setBrewProgress(parsedData.progress);
  
          // ✅ Clear "Sending..." first
          if (parsedData.progress > 0 && isSendingToMachine) {
            setIsSendingToMachine(false);
          }
  
          // ✅ Then if 100%, close the EventSource
          if (parsedData.progress >= 100) {
            source.close();
            setBrewProgressSource(null);
          }
        };
  
        source.onerror = (err) => {
          console.error("Brew progress stream error:", err);
          source.close();
          setBrewProgressSource(null);
        };
      }
  
      const historyResponse = await fetch(`http://localhost:8000/history/${user.uid}`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
  
      if (historyResponse.ok) {
        const historyData = await historyResponse.json();
        setBrewHistory(historyData.history || []);
      }
    } catch (error) {
      console.error("Error:", error);
      setErrorMessage("Error calculating brew settings. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };  

  const handleUseExample = (example) => {
    setQueryInput(example);
    setShowExamples(false);
  };

  return (
    <div className="min-h-screen w-full bg-[var(--color-mint)]">
      <NavBar />
      <main className="pt-16 md:pt-24 max-w-7xl mx-auto px-1 sm:px-2 space-y-6 md:space-y-8">
        {/* Two-column layout for main content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-3 lg:gap-4">
          {/* Left column for brew sections - takes 3/4 of the space */}
          <div className="lg:col-span-3 space-y-4">
            {/* Brew Request Section */}
            <section className="bg-white rounded-lg shadow-md p-3 md:p-4">
              <h2 className="text-xl md:text-2xl font-bold text-[var(--color-roast)] mb-3 md:mb-4 tracking-tight">
                Craft Your Perfect Cup
              </h2>
              <div className="mb-4">
                <ServingSizeSelector />
                <label htmlFor="coffee-query" className="block text-sm font-medium text-gray-700 mb-2">
                  Tell us what kind of coffee you want
                </label>
                <div className="flex flex-col gap-2">
                  <input
                    id="coffee-query"
                    type="text"
                    autoComplete="off"
                    className="w-full px-3 py-2 md:px-4 md:py-3 rounded-md border border-gray-300 focus:ring-[var(--color-hgreen)] focus:border-[var(--color-hgreen)] text-base"
                    placeholder="How would you like your coffee?"
                    value={queryInput}
                    onChange={(e) => setQueryInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault(); // prevent accidental form submits
                        handleNaturalLanguageQuery();
                      }
                    }}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleNaturalLanguageQuery()}
                      disabled={isLoading}
                      className="flex-1 px-4 py-2 md:py-3 border border-transparent text-sm md:text-base font-medium rounded-md shadow-sm text-white bg-[var(--color-hgreen)] hover:bg-[var(--color-roast)] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[var(--color-hgreen)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isLoading ? "Brewing..." : "Brew Coffee"}
                    </button>
                    <button
                      onClick={() => setShowExamples(!showExamples)}
                      disabled={isLoading || isSendingToMachine}
                      className={`px-3 py-2 md:py-3 border text-sm md:text-base font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[var(--color-hgreen)] ${
                        isLoading || isSendingToMachine
                          ? "bg-gray-200 text-gray-400 cursor-not-allowed border-gray-300"
                          : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                      }`}
                    >
                      Examples
                    </button>
                  </div>
                  {errorMessage && (
                    <p className="text-red-500 text-sm mt-2">{errorMessage}</p>
                  )}
                </div>
                {showExamples && (
                  <div className="mt-2 mb-3 bg-gray-50 p-3 rounded-md">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Try one of these:</h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {exampleQueries.map((example, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleUseExample(example)}
                          className="text-left px-3 py-2 border border-gray-300 text-xs md:text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none truncate"
                        >
                          {example}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </section>

            {/* Send to Machine Status */}

            {isSendingToMachine && (
              <section className="bg-white rounded-lg shadow-md p-3 md:p-4">
                <h2 className="text-lg md:text-xl font-bold text-[var(--color-roast)] mb-3">
                  Preparing Your Coffee
                </h2>
                <p className="text-sm font-medium text-gray-700 mb-2">
                  Sending instructions to the machine...
                </p>
                <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                  <div
                    className="bg-gray-400 h-4 rounded-full animate-pulse"
                    style={{ width: `100%` }}
                  ></div>
                </div>
              </section>
            )}


            {/* Brew Result Section */}
            {brewResult && (
            <section className="bg-white rounded-lg shadow-md p-3 md:p-4">
              <h2 className="text-lg md:text-xl font-bold text-[var(--color-roast)] mb-4">
                Your Brew Results
              </h2>

              {/* Progress Bar */}
              {brewProgress > 0 && brewProgress < 100 && (
                <div className="mb-6">
                  <p className="text-sm font-medium text-gray-700 mb-1">
                    {getBrewStageLabelSmart(brewResult?.machine_code?.commands, brewProgress)}
                  </p>
                  <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                    <div
                      className="bg-[var(--color-hgreen)] h-4 rounded-full transition-all duration-500 ease-out"
                      style={{ width: `${brewProgress}%` }}
                    ></div>
                  </div>
                </div>
              )}

              {/* Beans Used */}
              <div className="bg-gray-50 p-4 rounded-md">
                <h3 className="text-md md:text-lg font-semibold mb-3">Beans Used</h3>
                <ul className="space-y-2">
                  {brewResult?.beans?.map((bean, idx) => (
                    <li key={idx} className="p-2 bg-white rounded-md text-sm shadow-sm">
                      <p className="font-semibold">{bean.name} ({bean.roast})</p>
                      <p className="text-xs text-gray-600">{bean.notes} — {bean.amount_g}g</p>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Brewing Process Visualization */}
              {brewResult.machine_code?.commands && (
                <div className="mt-6">
                  <MachineCodeVisualization machineCode={brewResult.machine_code} />
                </div>
              )}

              {/* Machine Commands Toggle */}
              <div className="mt-6">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="text-md md:text-lg font-semibold">Technical Details</h3>
                  <button
                    onClick={() => setShowRawCommands(!showRawCommands)}
                    className="text-xs px-3 py-1 bg-gray-100 rounded-md hover:bg-gray-200"
                  >
                    {showRawCommands ? "Hide Commands" : "Show Commands"}
                  </button>
                </div>

                {showRawCommands && (
                  <div className="bg-gray-50 rounded-md p-3 text-sm font-mono whitespace-pre-wrap">
                    {brewResult.machine_code?.commands?.join("\n") || "No commands returned."}
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="mt-6 flex flex-col md:flex-row justify-end gap-3">
                <button
                  onClick={() => {
                    setSelectedBrewId(brewResult.brew_id);
                    setShowFeedbackModal(true);
                  }}
                  className="px-4 py-2 text-sm bg-[var(--color-hgreen)] text-white rounded-md hover:bg-[var(--color-roast)]"
                >
                  Leave Feedback
                </button>
                <button
                  onClick={() => {
                    if (brewProgressSource) {
                      brewProgressSource.close();
                      setBrewProgressSource(null);
                    }
                    setBrewProgress(0);
                    setBrewResult(null);
                  }}
                  className="text-sm px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                >
                  Close
                </button>
              </div>
            </section>
          )}


            {/* Brew History Section */}
            {brewHistory.length > 0 && (
              <section>
                <h2 className="text-xl md:text-2xl font-bold text-[var(--color-roast)] mb-3 md:mb-4 tracking-tight">
                  Recent Brews
                </h2>
                <div className="space-y-4">
                  {brewHistory.slice(0, 5).map((brew, index) => (
                    <div 
                      key={brew.brew_id || index} 
                      className="bg-white rounded-lg shadow-md p-4 flex justify-between items-center"
                    >
                      <div className="flex-grow">
                        <div className="flex justify-between items-center">
                          <p className="text-sm font-medium text-gray-700">
                            {brew.query || "Custom Brew"}
                          </p>
                          <p className="text-xs text-gray-500 ml-2">
                            {formatTimestamp(brew.timestamp)}
                          </p>
                        </div>
                        {brew.brew_result && (
                          <div className="text-xs text-gray-600 mt-1 flex items-center">
                            <span>{brew.brew_result.beans?.[0]?.name || 'Unknown Beans'}</span>
                            {' • '}
                            <span>{brew.serving_size} oz</span>
                          </div>
                        )}
                      </div>
                      <div className="flex space-x-2 ml-4 items-center">
                        <button
                          onClick={() => handleExecuteHistoricalBrew(brew.brew_id)}
                          disabled={isLoading}
                          className="px-3 py-1.5 text-xs bg-[var(--color-hgreen)] text-white rounded-md hover:bg-[var(--color-roast)] disabled:opacity-50"
                        >
                          Brew Again
                        </button>
                        {brew.feedback?.rating ? (
                          <div className="flex items-center space-x-1 text-xs text-gray-500">
                            <span>{brew.feedback.rating} ⭐</span>
                            {brew.feedback.notes && (
                              <span 
                                title={brew.feedback.notes}
                                className="cursor-help truncate max-w-[100px]"
                              >
                                (Notes)
                              </span>
                            )}
                          </div>
                        ) : (
                          <div> 
                            <button
                              onClick={() => {
                                setSelectedBrewId(brew.brew_id);
                                setShowFeedbackModal(true);
                              }}
                              className="px-3 py-1.5 text-xs bg-[var(--color-hgreen)] text-white rounded-md hover:bg-[var(--color-roast)]" 
                            > 
                              Leave Feedback
                            </button> 
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>

          {/* Right column for featured coffees - takes 1/4 of the space */}
          <div className="lg:col-span-1">
            <section className="bg-white rounded-lg shadow-md p-4 sticky top-24">
              <h2 className="text-xl font-bold text-[var(--color-roast)] mb-4 tracking-tight">
                Featured Coffees
              </h2>
              {/* Desktop view - compact vertical list */}
              <div className="hidden lg:block space-y-3">
                {featuredCoffees.map((coffee) => (
                  <button 
                    key={coffee.id} 
                    className="w-full flex items-center p-2 bg-gray-50 rounded-md hover:bg-gray-100 transition-colors text-left"
                    onClick={() => handleUseExample(`${coffee.name} coffee`)}
                  >
                    <img 
                      src={coffee.image} 
                      alt={coffee.name}
                      className="w-12 h-12 object-cover rounded-md mr-3" 
                    />
                    <div>
                      <h3 className="font-medium text-sm">{coffee.name}</h3>
                      <p className="text-xs text-gray-600">{coffee.description}</p>
                    </div>
                  </button>
                ))}
              </div>
              
              {/* Mobile view - horizontal scrolling cards */}
              <div className="lg:hidden overflow-x-auto -mx-2 px-2">
                <div className="flex flex-nowrap gap-3 pb-2">
                  {featuredCoffees.map((coffee) => (
                    <div key={coffee.id} onClick={() => handleUseExample(`${coffee.name} coffee`)} className="cursor-pointer">
                      <CoffeeCard {...coffee} />
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </div>
        </div>
      </main>

      <FeedbackModal
        isOpen={showFeedbackModal}
        onClose={() => setShowFeedbackModal(false)}
        onSubmit={(rating, notes) => handleSaveFeedback(selectedBrewId, rating, notes)}
      />
    </div>
  );
};

export default Home;