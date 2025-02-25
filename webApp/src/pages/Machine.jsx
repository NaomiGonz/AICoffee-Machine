import React from "react";
import NavBar from "../components/NavBar.jsx";

const Machine = () => {
  return (
    <div className="min-h-screen" style={{ backgroundColor: "var(--color-mint)" }}>
      <NavBar />
      <div className="p-4 pt-20">
        <h1 className="text-3xl font-bold mb-4" style={{ color: "var(--color-espresso)" }}>
          Machine Page
        </h1>
        <p>This is a placeholder for the machine control interface.</p>
        {/* Later, we’ll add content for controlling the coffee machine */}
      </div>
    </div>
  );
};

export default Machine;
