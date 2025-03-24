import React, { useState } from "react";
import NavBar from "../components/NavBar.jsx";
import CoffeeCard from "../components/CoffeeCard.jsx";
import col from "../assets/col.jpeg";
import eth from "../assets/eth.webp";
import arm from "../assets/amer.jpeg";
import ken from "../assets/ken.webp";
import bra from "../assets/bra.webp";
import sam from "../assets/sam.webp";

const featuredCoffees = [
  {
    id: 1,
    name: "Colombian Roast",
    image: col,
    description: "Rich and bold",
  },
  {
    id: 2,
    name: "Ethiopian Espresso",
    image: eth,
    description: "Fruity and aromatic",
  },
  {
    id: 3,
    name: "Americano Blend",
    image: arm,
    description: "Smooth and balanced",
  },
  {
    id: 4,
    name: "Kenyan AA",
    image: ken,
    description: "Bright acidity",
  },
  {
    id: 5,
    name: "Sumatra Mandheling",
    image: sam,
    description: "Earthy and intense",
  },
  {
    id: 6,
    name: "Brazilian Santos",
    image: bra,
    description: "Nutty and sweet",
  },
];

const Home = () => {
  // Sliders
  const [bitterness, setBitterness] = useState(5);
  const [acidity, setAcidity] = useState(5);
  const [sweetness, setSweetness] = useState(5);
  const [strength, setStrength] = useState(5);
  const [fruitiness, setFruitiness] = useState(5);

  const handleBrew = async () => {
    try {
      const response = await fetch('http://localhost:8000/brew', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          desired_flavor: {
            acidity: Number(acidity),
            strength: Number(strength),
            sweetness: Number(sweetness),
            fruitiness: Number(fruitiness),
            maltiness: Number(bitterness)  // Using bitterness for maltiness
          }
        })
      });
      
      const data = await response.json();
      
      // Update to match the actual response structure
      alert(`Brew Settings:
        Temperature: ${data.parameters.temperature}°C
        Water: ${data.parameters.dose_size * 2.5}ml
        Pressure: ${data.parameters.extraction_pressure} bars
        Beans: ${data.parameters.bean_type}`);
    } catch (error) {
      console.error('Error:', error);
      alert('Error calculating brew settings');
    }
  };
  
  return (
    <div 
      className="min-h-screen w-full"
      style={{ backgroundColor: "var(--color-mint)" }}
    >
      <NavBar />

      <div className="pt-20">
        {/* Featured Section */}
        <section className="px-4 md:px-8 py-6">
          <h2 
            className="text-2xl font-bold mb-4" 
            style={{ color: "var(--color-roast)" }}
          >
            Featured Coffees
          </h2>
          <div 
            className="overflow-x-auto flex flex-nowrap space-x-4 w-full"
            style={{ scrollBehavior: "smooth" }}
          >
            {featuredCoffees.map((coffee) => (
              <CoffeeCard 
                key={coffee.id}
                id={coffee.id}
                name={coffee.name}
                image={coffee.image}
                description={coffee.description}
              />
            ))}
          </div>
        </section>

        {/* Craft Your Perfect Cup */}
        <section className="px-16 md:px-32 py-6  pt-10">
          <h2 
            className="text-2xl font-bold mb-4" 
            style={{ color: "var(--color-roast)" }}
          >
            Craft Your Perfect Cup
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {/* Bitterness */}
            <div className="flex flex-col">
              <label 
                className="font-semibold mb-1"
                style={{ color: "var(--color-roast)" }}
              >
                Bitterness: {bitterness}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={bitterness}
                onChange={(e) => setBitterness(e.target.value)}
                className="w-full cursor-pointer accent-[var(--color-hgreen)]"
              />
            </div>

            {/* Acidity */}
            <div className="flex flex-col">
              <label 
                className="font-semibold mb-1"
                style={{ color: "var(--color-roast)" }}
              >
                Acidity: {acidity}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={acidity}
                onChange={(e) => setAcidity(e.target.value)}
                className="w-full cursor-pointer accent-[var(--color-hgreen)]"
              />
            </div>

            {/* Sweetness */}
            <div className="flex flex-col">
              <label 
                className="font-semibold mb-1"
                style={{ color: "var(--color-roast)" }}
              >
                Sweetness: {sweetness}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={sweetness}
                onChange={(e) => setSweetness(e.target.value)}
                className="w-full cursor-pointer accent-[var(--color-hgreen)]"
              />
            </div>

            {/* Strength */}
            <div className="flex flex-col">
              <label 
                className="font-semibold mb-1"
                style={{ color: "var(--color-roast)" }}
              >
                Strength: {strength}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={strength}
                onChange={(e) => setStrength(e.target.value)}
                className="w-full cursor-pointer accent-[var(--color-hgreen)]"
              />
            </div>

            {/* Fruitiness */}
            <div className="flex flex-col">
              <label 
                className="font-semibold mb-1"
                style={{ color: "var(--color-roast)" }}
              >
                Fruitiness: {fruitiness}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                value={fruitiness}
                onChange={(e) => setFruitiness(e.target.value)}
                className="w-full cursor-pointer accent-[var(--color-hgreen)]"
              />
            </div>
          </div>

          <button
            onClick={handleBrew}
            className="mt-6 px-6 py-2 rounded shadow-sm hover:shadow-md"
            style={{ 
              backgroundColor: "var(--color-hgreen)", 
              color: "white" 
            }}
          >
            Brew
          </button>
        </section>
      </div>
    </div>
  );
};

export default Home;
