import React from "react";
import NavBar from "../components/NavBar.jsx";

const Machine = () => {
  return (
    <div className="min-h-screen bg-[var(--color-mint)]">
      <NavBar />
      <div className="max-w-4xl mx-auto px-6 pt-28 pb-16">
        <h1 className="text-3xl font-extrabold text-[var(--color-espresso)] mb-4">
          Machine Interface (Coming Soon)
        </h1>
        <p className="text-gray-700 max-w-lg">
          This page will allow you to directly control your AI Coffee Machine — from starting brews to adjusting grind size, temperature, and pressure in real time. Stay tuned for a beautifully interactive experience.
        </p>

        <div className="mt-8 text-sm text-gray-500">
          Planned features:
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>Live brewing stats and logs</li>
            <li>Manual override of brew settings</li>
            <li>Hardware status indicators</li>
            <li>Connected device management</li>
            <li>Remote brew start</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Machine;