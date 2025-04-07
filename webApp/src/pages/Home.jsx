import React, { useState, useEffect } from "react";
import { getAuth } from "firebase/auth";
import NavBar from "../components/NavBar.jsx";
import CoffeeCard from "../components/CoffeeCard.jsx";

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
  const [servingSize, setServingSize] = useState(7.0);  // Default to 7 oz

  const auth = getAuth();
  const user = auth.currentUser;

  const ServingSizeSelector = () => {
    const sizes = [
      { label: '3 oz', value: 3.0 },
      { label: '7 oz', value: 7.0 },
      { label: '10 oz', value: 10.0 }
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

  const handleNaturalLanguageQuery = async (query = queryInput) => {
    if (!query.trim()) {
      alert("Please enter a coffee request");
      return;
    }

    try {
      setIsLoading(true);
      
      // Get token if user is logged in
      let token = null;
      if (user) {
        token = await user.getIdToken();
      }

      const response = await fetch("http://localhost:8000/brew", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify({ 
          query, 
          serving_size: servingSize 
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      console.log("API Response:", data); // Debug log
      
      // Transform the API response to match our UI expectations
      const transformedData = transformBrewingData(data);
      setBrewResult(transformedData);
    } catch (error) {
      console.error("Error:", error);
      alert("Error calculating brew settings");
    } finally {
      setIsLoading(false);
    }
  };

  // Function to transform backend data to match frontend expectations
  const transformBrewingData = (apiResponse) => {
    // Extract brewing parameters
    const brewingParams = apiResponse.brewing_parameters || {};
    
    // Extract bean information
    const beans = apiResponse.recommended_beans || [];
    
    // Transform beans to the expected format
    const transformedBeans = beans.map((bean) => ({
      name: bean.name || "Custom Blend",
      roast: bean.roast_level || "Medium",
      amount_g: bean.amount_g || apiResponse.serving_details?.coffee_g || 0,
      notes: bean.flavor_notes?.join(", ") || bean.description || "Balanced flavor"
    }));
    
    // Create additional notes from brewing instructions
    const additionalNotes = [];
    
    if (apiResponse.brewing_instructions) {
      additionalNotes.push(apiResponse.brewing_instructions);
    }
    
    if (brewingParams.grind_instructions) {
      additionalNotes.push(`Grind: ${brewingParams.grind_instructions}`);
    }
    
    if (brewingParams.extraction_time) {
      additionalNotes.push(`Extraction time: ${brewingParams.extraction_time} seconds`);
    }
    
    // Return the transformed data
    return {
      coffee_type: apiResponse.coffee_type || "Espresso",
      recommended_temperature: brewingParams.recommended_temp_c || brewingParams.temperature || 93,
      flavor_profile: apiResponse.flavor_profile || brewingParams.flavor_profile || "Balanced",
      beans: transformedBeans.length > 0 ? transformedBeans : [
        {
          name: "House Blend", 
          roast: "Medium", 
          amount_g: apiResponse.serving_details?.coffee_g || 21, 
          notes: "Balanced flavor profile"
        }
      ],
      additional_notes: additionalNotes
    };
  };

  const handleUseExample = (example) => {
    setQueryInput(example);
    setShowExamples(false);
  };

  return (
    <div className="min-h-screen w-full bg-[var(--color-mint)]">
      <NavBar />
      <main className="pt-16 md:pt-24 max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 space-y-6 md:space-y-12">
        {/* Natural Language Query Section */}
        <section className="bg-white rounded-lg shadow-md p-4 md:p-6">
          <h2 className="text-2xl md:text-3xl font-extrabold text-[var(--color-roast)] mb-4 md:mb-6 tracking-tight">
            Craft Your Perfect Cup
          </h2>
          
          <div className="mb-4">
            {/* Serving Size Selector */}
            <ServingSizeSelector />

            <label htmlFor="coffee-query" className="block text-sm font-medium text-gray-700 mb-2">
              Tell us what kind of coffee you want
            </label>
            
            {/* Mobile-optimized input with button below */}
            <div className="flex flex-col gap-2">
              <input
                id="coffee-query"
                type="text"
                className="w-full px-3 py-2 md:px-4 md:py-3 rounded-md border border-gray-300 focus:ring-[var(--color-hgreen)] focus:border-[var(--color-hgreen)] text-base"
                placeholder="How would you like your coffee?"
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
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
                  className="px-3 py-2 md:py-3 border border-gray-300 text-sm md:text-base font-medium rounded-md shadow-sm bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[var(--color-hgreen)]"
                >
                  Examples
                </button>
              </div>
            </div>
          </div>
          
          {/* Collapsible examples section */}
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
        </section>

        {/* Brew Results Section (Appears when there's a result) */}
        {brewResult && (
          <section className="bg-white rounded-lg shadow-md p-4 md:p-6">
            <h2 className="text-xl md:text-2xl font-bold text-[var(--color-roast)] mb-3 md:mb-4">Your Brew Results</h2>
            
            {/* Mobile-friendly grid layout */}
            <div className="space-y-4 md:space-y-0 md:grid md:grid-cols-2 md:gap-6">
              <div className="bg-gray-50 rounded-md p-3">
                <h3 className="text-md md:text-lg font-medium mb-2">Coffee Details</h3>
                <p className="text-sm md:text-base text-gray-700 mb-1">
                  <span className="font-semibold">Type:</span> {brewResult.coffee_type}
                </p>
                <p className="text-sm md:text-base text-gray-700 mb-1">
                  <span className="font-semibold">Temperature:</span> {brewResult.recommended_temperature}°C
                </p>
                <p className="text-sm md:text-base text-gray-700">
                  <span className="font-semibold">Serving Size:</span> {servingSize} oz
                </p>
                <p className="text-sm md:text-base text-gray-700">
                  <span className="font-semibold">Flavor Profile:</span> {brewResult.flavor_profile}
                </p>
              </div>
              
              <div>
                <h3 className="text-md md:text-lg font-medium mb-2">Beans</h3>
                <ul className="space-y-2">
                  {brewResult.beans && brewResult.beans.map((bean, idx) => (
                    <li key={idx} className="p-2 bg-gray-50 rounded text-sm md:text-base">
                      <p className="font-semibold truncate">{bean.name} ({bean.roast})</p>
                      <p className="text-xs md:text-sm text-gray-600">Amount: {bean.amount_g}g</p>
                      <p className="text-xs md:text-sm text-gray-600">Notes: {bean.notes}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            
            {brewResult.additional_notes && brewResult.additional_notes.length > 0 && (
              <div className="mt-4">
                <h3 className="text-md md:text-lg font-medium mb-2">Brewing Notes</h3>
                <ul className="list-disc pl-5 space-y-1 text-sm md:text-base">
                  {brewResult.additional_notes.map((note, idx) => (
                    <li key={idx} className="text-gray-700">{note}</li>
                  ))}
                </ul>
              </div>
            )}
            
            <div className="mt-4 md:mt-6 flex justify-end">
              <button
                onClick={() => setBrewResult(null)}
                className="text-sm md:text-base px-3 py-1.5 md:px-4 md:py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </section>
        )}

        {/* Featured Coffees */}
        <section>
          <h2 className="text-2xl md:text-3xl font-extrabold text-[var(--color-roast)] mb-4 md:mb-6 tracking-tight">Featured Coffees</h2>
          <div className="overflow-x-auto -mx-3 px-3 pb-2">
            <div className="flex flex-nowrap gap-3 md:gap-4">
              {featuredCoffees.map((coffee) => (
                <CoffeeCard key={coffee.id} {...coffee} />
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

export default Home;