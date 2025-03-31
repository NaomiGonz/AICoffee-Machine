import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import NavBar from "../components/NavBar.jsx";
import Button from "../components/Button.jsx";
import col from "../assets/col.jpeg";
import eth from "../assets/eth.webp";
import arm from "../assets/amer.jpeg";
import ken from "../assets/ken.webp";
import bra from "../assets/bra.webp";
import sam from "../assets/sam.webp";

const coffeeData = {
  1: {
    name: "Colombian Roast",
    image: col,
    description: "Rich and bold with chocolatey undertones.",
    bitterness: 7,
    acidity: 5,
    sweetness: 4,
    strength: 8,
    fruitiness: 3,
    brewTime: "4-5 minutes",
  },
  2: {
    name: "Ethiopian Espresso",
    image: eth,
    description: "Fruity and aromatic with a light body.",
    bitterness: 4,
    acidity: 6,
    sweetness: 5,
    strength: 5,
    fruitiness: 8,
    brewTime: "3-4 minutes",
  },
  3: {
    name: "Americano Blend",
    image: arm,
    description: "Smooth and balanced, with notes of chocolate and caramel.",
    bitterness: 5,
    acidity: 6,
    sweetness: 5,
    strength: 6,
    fruitiness: 4,
    brewTime: "4 minutes",
  },
};

const CoffeeDetails = () => {
  const { coffeeId } = useParams();
  const navigate = useNavigate();
  const coffee = coffeeData[coffeeId];

  if (!coffee) {
    return (
      <div className="min-h-screen bg-[var(--color-mint)]">
        <NavBar />
        <div className="pt-24 flex flex-col items-center justify-center">
          <h2 className="text-xl text-[var(--color-espresso)] mb-4">
            No coffee found with ID: {coffeeId}
          </h2>
          <Button
            text="Go Back"
            onClick={() => navigate(-1)}
            color="var(--color-hgreen)"
          />
        </div>
      </div>
    );
  }

  const handleBrew = () => {
    alert(`Brewing ${coffee.name}...`);
  };

  return (
    <div className="min-h-screen bg-[var(--color-mint)]">
      <NavBar />

      <div className="pt-24 flex flex-col items-center text-center px-4">
        <h1 className="text-3xl font-extrabold text-[var(--color-roast)] mb-4 tracking-tight">
          {coffee.name}
        </h1>

        <img
          src={coffee.image}
          alt={coffee.name}
          className="w-48 h-auto rounded-xl shadow-md mb-6"
        />

        <p className="mb-4 max-w-md text-gray-700 leading-relaxed">
          {coffee.description}
        </p>

        <ul className="text-left mb-4 max-w-xs text-sm text-gray-700 space-y-1">
          <li><strong>Bitterness:</strong> {coffee.bitterness}/10</li>
          <li><strong>Acidity:</strong> {coffee.acidity}/10</li>
          <li><strong>Sweetness:</strong> {coffee.sweetness}/10</li>
          <li><strong>Strength:</strong> {coffee.strength}/10</li>
          <li><strong>Fruitiness:</strong> {coffee.fruitiness}/10</li>
        </ul>

        <p className="mb-6 text-gray-600 text-sm">Expected brew time: {coffee.brewTime}</p>

        <div className="flex flex-col sm:flex-row gap-4">
          <Button
            text="Brew"
            onClick={handleBrew}
            color="var(--color-hgreen)"
          />

          <Button
            text="Back"
            onClick={() => navigate(-1)}
            color="var(--color-hgreen)"
            transparent={true}
          />
        </div>
      </div>
    </div>
  );
};

export default CoffeeDetails;
