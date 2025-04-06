import React, { useState, useEffect } from "react";
import { doc, collection, getDocs, addDoc, deleteDoc } from "firebase/firestore";
import { getAuth } from "firebase/auth";
import { db } from "../tools/firebase";
import NavBar from "../components/NavBar.jsx";
import CoffeeCard from "../components/CoffeeCard.jsx";
import BrewHistoryCard from "../components/BrewHistoryCard.jsx";

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
  "I want a fruity espresso with bright notes",
  "Make me a large cappuccino with chocolatey flavor",
  "Can I have a pour-over with nutty profile?",
  "Brew me a strong dark roast for the morning",
  "I need something smooth and balanced today",
  "Can you make an Ethiopian coffee with floral notes?"
];

const Home = () => {
  const [queryInput, setQueryInput] = useState("");
  const [brewHistory, setBrewHistory] = useState([]);
  const [savedBrews, setSavedBrews] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [brewResult, setBrewResult] = useState(null);

  const auth = getAuth();
  const uid = auth.currentUser?.uid;

  const handleNaturalLanguageQuery = async (query = queryInput) => {
    if (!query.trim()) {
      alert("Please enter a coffee request");
      return;
    }

    try {
      setIsLoading(true);
      const user = auth.currentUser;
      if (!user) {
        alert("You must be logged in to brew coffee.");
        setIsLoading(false);
        return;
      }
      const token = await user.getIdToken();

      const response = await fetch("http://localhost:8000/brew-natural", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query }),
      });

      const data = await response.json();
      setBrewResult(data);
      
      const formattedMessage = `
☕ Brew Recommendation:
Coffee Type: ${data.coffee_type}
Beans: ${data.beans.map(b => `${b.name} (${b.roast}) - ${b.amount_g}g`).join(", ")}
Temperature: ${data.recommended_temperature}°C
${data.additional_notes.length > 0 ? `\nNotes: ${data.additional_notes.join("\n")}` : ""}
      `;
      
      alert(formattedMessage);
      fetchBrews();
    } catch (error) {
      console.error("Error:", error);
      alert("Error calculating brew settings");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchBrews = async () => {
    if (!uid) {
      console.warn("No user logged in, skipping Firestore fetch.");
      return;
    }

    try {
      const userDocRef = doc(db, "users", uid);
      const brewsRef = collection(userDocRef, "brews");

      const snapshot = await getDocs(brewsRef);

      const brews = snapshot.docs.map((doc) => {
        const data = doc.data();
        const timestamp = data.timestamp?.toDate?.() || new Date();

        return {
          id: doc.id,
          ...data,
          timestamp,
        };
      });

      setBrewHistory(
        brews
          .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
          .slice(0, 10)
      );
    } catch (error) {
      console.error("[Firestore] Error fetching brews:", error);
    }
  };

  const fetchSavedBrews = async () => {
    if (!uid) return;

    try {
      const savedRef = collection(doc(db, "users", uid), "saved_brews");
      const snapshot = await getDocs(savedRef);
      const saved = snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
      setSavedBrews(saved);
    } catch (error) {
      console.error("Error fetching saved brews:", error);
    }
  };

  const handleSaveBrew = async (brew) => {
    if (!uid) return;

    const name = prompt("Enter a name for this saved brew:", "My Custom Brew");
    if (!name) return;

    try {
      const savedRef = collection(doc(db, "users", uid), "saved_brews");
      const existing = savedBrews.find(
        (saved) => JSON.stringify(saved.query) === JSON.stringify(brew.query)
      );

      if (existing) {
        await deleteDoc(doc(savedRef, existing.id));
        alert("Removed from saved brews.");
      } else {
        await addDoc(savedRef, {
          name,
          query: brew.query,
          result: brew.result,
          timestamp: new Date(),
        });
        alert("Saved brew successfully.");
      }

      fetchSavedBrews();
    } catch (error) {
      console.error("Error toggling saved brew:", error);
    }
  };

  const handleUseExample = (example) => {
    setQueryInput(example);
  };

  useEffect(() => {
    fetchBrews();
    fetchSavedBrews();
  }, [uid]);

  return (
    <div className="min-h-screen w-full bg-[var(--color-mint)]">
      <NavBar />
      <main className="pt-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        {/* Natural Language Query Section */}
        <section className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-3xl font-extrabold text-[var(--color-roast)] mb-6 tracking-tight">
            Craft Your Perfect Cup
          </h2>
          
          <div className="mb-4">
            <label htmlFor="coffee-query" className="block text-sm font-medium text-gray-700 mb-2">
              Tell us what kind of coffee you want
            </label>
            <div className="flex gap-2">
              <input
                id="coffee-query"
                type="text"
                className="flex-1 min-w-0 block w-full px-4 py-3 rounded-md border border-gray-300 focus:ring-[var(--color-hgreen)] focus:border-[var(--color-hgreen)]"
                placeholder="I want a fruity espresso with bright notes..."
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
              />
              <button
                onClick={() => handleNaturalLanguageQuery()}
                disabled={isLoading}
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-[var(--color-hgreen)] hover:bg-[var(--color-roast)] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[var(--color-hgreen)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? "Brewing..." : "Brew"}
              </button>
            </div>
          </div>
          
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Try one of these examples:</h3>
            <div className="flex flex-wrap gap-2">
              {exampleQueries.map((example, idx) => (
                <button
                  key={idx}
                  onClick={() => handleUseExample(example)}
                  className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-medium rounded-full text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[var(--color-hgreen)]"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Brew Results Section (Appears when there's a result) */}
        {brewResult && (
          <section className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-2xl font-bold text-[var(--color-roast)] mb-4">Your Brew Results</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-lg font-medium mb-2">Coffee Details</h3>
                <p className="text-gray-700 mb-1"><span className="font-semibold">Type:</span> {brewResult.coffee_type}</p>
                <p className="text-gray-700 mb-1"><span className="font-semibold">Temperature:</span> {brewResult.recommended_temperature}°C</p>
                <p className="text-gray-700"><span className="font-semibold">Flavor Profile:</span> {brewResult.flavor_profile}</p>
              </div>
              <div>
                <h3 className="text-lg font-medium mb-2">Beans</h3>
                <ul className="space-y-2">
                  {brewResult.beans.map((bean, idx) => (
                    <li key={idx} className="p-2 bg-gray-50 rounded">
                      <p className="font-semibold">{bean.name} ({bean.roast})</p>
                      <p className="text-sm text-gray-600">Amount: {bean.amount_g}g</p>
                      <p className="text-sm text-gray-600">Notes: {bean.notes}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            
            {brewResult.additional_notes && brewResult.additional_notes.length > 0 && (
              <div className="mt-4">
                <h3 className="text-lg font-medium mb-2">Brewing Notes</h3>
                <ul className="list-disc pl-5 space-y-1">
                  {brewResult.additional_notes.map((note, idx) => (
                    <li key={idx} className="text-gray-700">{note}</li>
                  ))}
                </ul>
              </div>
            )}
            
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => handleSaveBrew({ query: queryInput, result: brewResult })}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-[var(--color-hgreen)] bg-gray-50 hover:bg-gray-100"
              >
                Save This Brew
              </button>
            </div>
          </section>
        )}

        {/* Featured Coffees */}
        <section>
          <h2 className="text-3xl font-extrabold text-[var(--color-roast)] mb-6 tracking-tight">Featured Coffees</h2>
          <div className="overflow-x-auto flex flex-nowrap gap-4 pb-2">
            {featuredCoffees.map((coffee) => (
              <CoffeeCard key={coffee.id} {...coffee} />
            ))}
          </div>
        </section>

        {/* Brew History */}
        <section>
          <h2 className="text-3xl font-extrabold text-[var(--color-roast)] mb-6 tracking-tight">Brew History</h2>
          {brewHistory.length === 0 ? (
            <p className="text-gray-600">No brews found.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {brewHistory.map((brew) => {
                const isAlreadySaved = savedBrews.some(
                  (saved) =>
                    JSON.stringify(saved.query) === JSON.stringify(brew.query)
                );

                return (
                  <BrewHistoryCard
                    key={brew.id}
                    brew={brew}
                    onBrewAgain={() => handleNaturalLanguageQuery(brew.query)}
                    onSave={() => handleSaveBrew(brew)}
                    isSaved={isAlreadySaved}
                  />
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default Home;