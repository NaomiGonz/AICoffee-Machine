import React, { useEffect, useState } from "react";
import { getAuth, deleteUser } from "firebase/auth";
import { doc, collection, getDocs, deleteDoc } from "firebase/firestore";
import { db } from "../tools/firebase";
import NavBar from "../components/NavBar.jsx";
import BrewHistoryCard from "../components/BrewHistoryCard.jsx";
import Button from "../components/Button.jsx";

const Account = () => {
  const [savedBrews, setSavedBrews] = useState([]);
  const [userInfo, setUserInfo] = useState(null);
  const auth = getAuth();
  const user = auth.currentUser;
  const uid = user?.uid;

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

  const handleDeleteAccount = async () => {
    if (!window.confirm("Are you sure you want to delete your account? This cannot be undone.")) return;
    try {
      await deleteUser(user);
      alert("Your account has been deleted.");
      window.location.href = "/login";
    } catch (error) {
      console.error("Error deleting account:", error);
      alert("Failed to delete account. Try signing in again and retry.");
    }
  };

  useEffect(() => {
    if (user) {
      setUserInfo({
        name: user.displayName || "N/A",
        email: user.email,
        uid: user.uid,
        created: user.metadata.creationTime,
        lastLogin: user.metadata.lastSignInTime,
      });
    }
    fetchSavedBrews();
  }, [uid]);

  return (
    <div className="min-h-screen bg-[var(--color-mint)]">
      <NavBar />
      <div className="p-4 pt-24 max-w-6xl mx-auto space-y-10">
        <section>
          <h1 className="text-3xl font-bold mb-4 text-[var(--color-espresso)]">
            Your Profile
          </h1>
          {userInfo ? (
            <div className="bg-white shadow-md rounded p-6 space-y-2 text-[var(--color-espresso)]">
              <p><strong>Name:</strong> {userInfo.name}</p>
              <p><strong>Email:</strong> {userInfo.email}</p>
              <p><strong>User ID:</strong> {userInfo.uid}</p>
              <p><strong>Created On:</strong> {userInfo.created}</p>
              <p><strong>Last Login:</strong> {userInfo.lastLogin}</p>
            </div>
          ) : (
            <p className="text-gray-600">No user information found.</p>
          )}
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4 text-[var(--color-espresso)]">
            Your Saved Brews
          </h2>
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
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4 text-[var(--color-espresso)]">Feedback</h2>
          <p className="mb-3 text-[var(--color-espresso)]">
            We'd love to hear your thoughts on how we can improve your coffee experience!
          </p>
          <a
            href="https://forms.gle/your-google-form-url" // Replace with your form
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block px-5 py-2 bg-[var(--color-hgreen)] text-white rounded hover:opacity-90"
          >
            Submit Feedback
          </a>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4 text-red-700">Account Management</h2>
          <Button
            text="Delete My Account"
            onClick={handleDeleteAccount}
            color="#B00020"
            transparent={false}
          />
        </section>
      </div>
    </div>
  );
};

export default Account;