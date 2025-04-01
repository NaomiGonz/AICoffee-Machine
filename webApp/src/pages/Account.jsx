import React, { useEffect, useState } from "react";
import { getAuth } from "firebase/auth";
import { doc, collection, getDocs, deleteDoc } from "firebase/firestore";
import { db } from "../tools/firebase";
import NavBar from "../components/NavBar.jsx";
import BrewHistoryCard from "../components/BrewHistoryCard.jsx";

const Account = () => {
  const [savedBrews, setSavedBrews] = useState([]);
  const auth = getAuth();
  const uid = auth.currentUser?.uid;

  const fetchSavedBrews = async () => {
    if (!uid) return;
    try {
      const savedRef = collection(doc(db, "users", uid), "saved_brews");
      const snapshot = await getDocs(savedRef);
      const brews = snapshot.docs.map((doc) => {
        const data = doc.data();
        const timestamp = data.timestamp?.toDate?.() || new Date();
        return { id: doc.id, ...data, timestamp };
      });
      const sorted = brews.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
      setSavedBrews(sorted);
    } catch (error) {
      console.error("Error fetching saved brews:", error);
    }
  };

  const handleDelete = async (brewId) => {
    try {
      const brewRef = doc(db, "users", uid, "saved_brews", brewId);
      await deleteDoc(brewRef);
      setSavedBrews((prev) => prev.filter((b) => b.id !== brewId));
      alert("Brew removed successfully.");
    } catch (error) {
      console.error("Error deleting brew:", error);
      alert("Failed to delete brew.");
    }
  };

  useEffect(() => {
    fetchSavedBrews();
  }, [uid]);

  return (
    <div className="min-h-screen bg-[var(--color-mint)]">
      <NavBar />
      <div className="p-4 pt-24 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-6 text-[var(--color-espresso)]">
          Your Saved Brews
        </h1>
        {savedBrews.length === 0 ? (
          <p className="text-gray-600">You haven't saved any brews yet.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {savedBrews.map((brew) => (
              <BrewHistoryCard 
                key={brew.id} 
                brew={brew} 
                hideSave 
                showName 
                onDelete={() => handleDelete(brew.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Account;