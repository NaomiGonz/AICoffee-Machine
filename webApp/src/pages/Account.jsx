import React from "react";
import NavBar from "../components/NavBar.jsx";

const Account = () => {
  return (
    <div className="min-h-screen" style={{ backgroundColor: "var(--color-mint)" }}>
      <NavBar />
      <div className="p-4 pt-20">
        <h1 className="text-3xl font-bold mb-4" style={{ color: "var(--color-espresso)" }}>
          Account Page
        </h1>
        <p>This is a placeholder for the account settings page.</p>
        {/* Later, we’ll add forms and data for user profile, etc. */}
      </div>
    </div>
  );
};

export default Account;
