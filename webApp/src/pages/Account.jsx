import React from "react";
import { getAuth } from "firebase/auth";
import NavBar from "../components/NavBar.jsx";
import Button from "../components/Button.jsx";
import { signOut } from "../tools/auth";
import { useNavigate } from "react-router-dom";

const Account = () => {
  const auth = getAuth();
  const user = auth.currentUser;
  const navigate = useNavigate();

  const handleLogout = async () => {
    await signOut();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-[var(--color-mint)]">
      <NavBar />
      <div className="max-w-xl mx-auto px-6 pt-28 pb-12">
        <h1 className="text-3xl font-extrabold text-[var(--color-espresso)] mb-6">My Account</h1>

        <div className="bg-white shadow-md rounded-xl p-6 space-y-4 border border-gray-100">
          <div>
            <h2 className="text-lg font-semibold text-[var(--color-roast)]">User Info</h2>
            <p className="text-sm text-gray-700">Email: {user?.email}</p>
            <p className="text-sm text-gray-500">UID: {user?.uid}</p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-[var(--color-roast)]">Actions</h2>
            <Button 
              text="Log Out"
              onClick={handleLogout}
              color="var(--color-hgreen)"
              className="mt-2"
            />
          </div>
        </div>

        <div className="mt-8 text-sm text-center text-gray-500">
          More features coming soon — such as managing brew preferences, saved recipes, and connected devices.
        </div>
      </div>
    </div>
  );
};

export default Account;