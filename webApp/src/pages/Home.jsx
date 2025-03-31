import React, { useState, useEffect } from "react";
import { doc, collection, getDocs } from "firebase/firestore";
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

const Home = () => {
  const [bitterness, setBitterness] = useState(5);
  const [acidity, setAcidity] = useState(5);
  const [sweetness, setSweetness] = useState(5);
  const [strength, setStrength] = useState(5);
  const [fruitiness, setFruitiness] = useState(5);
  const [brewHistory, setBrewHistory] = useState([]);

  const auth = getAuth();
  const uid = auth.currentUser?.uid;

  const handleBrew = async (flavor = null) => {
    try {
      const user = auth.currentUser;
      if (!user) {
        alert("You must be logged in to brew coffee.");
        return;
      }
      const token = await user.getIdToken();

      const flavorProfile = flavor || {
        acidity: Number(acidity),
        strength: Number(strength),
        sweetness: Number(sweetness),
        fruitiness: Number(fruitiness),
        maltiness: Number(bitterness),
      };

      const response = await fetch("http://localhost:8000/brew", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ desired_flavor: flavorProfile }),
      });

      const data = await response.json();
      alert(`Brew Settings:\nTemperature: ${data.parameters.temperature}°C\nWater: ${data.parameters.dose_size * 2.5}ml\nPressure: ${data.parameters.extraction_pressure} bars\nBeans: ${data.parameters.bean_type}`);

      fetchBrews();
    } catch (error) {
      console.error("Error:", error);
      alert("Error calculating brew settings");
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

      console.log("[Firestore] Fetching from: users/", uid, "/brews");

      const snapshot = await getDocs(brewsRef);
      console.log("[Firestore] Documents fetched:", snapshot.docs.length);

      if (snapshot.empty) {
        console.warn("[Firestore] No brew documents found.");
      }

      const brews = snapshot.docs.map((doc) => {
        const data = doc.data();
        const timestamp = data.timestamp?.toDate?.() || new Date();

        return {
          id: doc.id,
          ...data,
          timestamp,
        };
      });

      const sortedBrews = brews.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
      setBrewHistory(sortedBrews.slice(0, 10));
    } catch (error) {
      console.error("[Firestore] Error fetching brews:", error);
    }
  };

  useEffect(() => {
    fetchBrews();
  }, [uid]);

  const sliders = [
    { label: "Bitterness", value: bitterness, setter: setBitterness },
    { label: "Acidity", value: acidity, setter: setAcidity },
    { label: "Sweetness", value: sweetness, setter: setSweetness },
    { label: "Strength", value: strength, setter: setStrength },
    { label: "Fruitiness", value: fruitiness, setter: setFruitiness },
  ];

  return (
    <div className="min-h-screen w-full bg-[var(--color-mint)]">
      <NavBar />
      <div className="pt-20">
        <section className="px-6 md:px-12 py-6">
          <h2 className="text-2xl font-bold mb-4 text-[var(--color-roast)]">Featured Coffees</h2>
          <div className="overflow-x-auto flex flex-nowrap gap-4 pb-2">
            {featuredCoffees.map((coffee) => (
              <CoffeeCard key={coffee.id} {...coffee} />
            ))}
          </div>
        </section>

        <section className="px-6 md:px-12 py-6">
          <h2 className="text-2xl font-bold mb-4 text-[var(--color-roast)]">Craft Your Perfect Cup</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
            {sliders.map(({ label, value, setter }, idx) => (
              <div key={idx} className="flex flex-col">
                <label className="font-semibold text-[var(--color-roast)]">{label}: {value}</label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={value}
                  onChange={(e) => setter(Number(e.target.value))}
                  className="accent-[var(--color-hgreen)] cursor-pointer"
                />
              </div>
            ))}
          </div>
          <button
            onClick={() => handleBrew()}
            className="mt-6 px-6 py-2 bg-[var(--color-hgreen)] text-white rounded hover:shadow-md"
          >
            Brew
          </button>
        </section>

        <section className="px-6 md:px-12 py-6">
          <h2 className="text-2xl font-bold mb-4 text-[var(--color-roast)]">Brew History</h2>
          {brewHistory.length === 0 ? (
            <p className="text-gray-600">No brews found.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
              {brewHistory.map((brew) => (
                <BrewHistoryCard key={brew.id} brew={brew} onBrewAgain={() => handleBrew(brew.desired_flavor)} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default Home;