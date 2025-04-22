import React, { useState } from "react";

const FeedbackModal = ({ isOpen, onClose, onSubmit }) => {
  const [rating, setRating] = useState(null);
  const [notes, setNotes] = useState("");

  const handleRatingClick = (star) => {
    setRating(star);
  };

  const handleSubmit = () => {
    if (!rating) return alert("Please select a rating.");
    onSubmit(rating, notes);
    setRating(null);
    setNotes("");
    onClose();
  };

  if (!isOpen) return null;

  // Base styles for all buttons
  const baseButtonStyle = {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "0.5rem 1rem",
    borderRadius: "0.375rem",
    borderWidth: "1px",
    fontSize: "1.125rem",
    fontWeight: "600",
    transition: "all 200ms",
    margin: "0 0.25rem"
  };

  return (
    <div style={{
      position: "fixed",
      inset: "0",
      backgroundColor: "rgba(0, 0, 0, 0.4)",
      zIndex: "50",
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }}>
      <div style={{
        backgroundColor: "white",
        borderRadius: "0.5rem",
        boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
        padding: "1.5rem",
        width: "90%",
        maxWidth: "500px"
      }}>
        <h2 style={{ fontSize: "1.125rem", fontWeight: "600", marginBottom: "1rem" }}>
          Leave Feedback
        </h2>
        
        <div style={{ display: "flex", marginBottom: "1rem" }}>
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              onClick={() => handleRatingClick(star)}
              style={{
                ...baseButtonStyle,
                backgroundColor: rating === star ? "#fef9c3" : "white", // yellow-200 equivalent
                borderColor: rating === star ? "#eab308" : "black", // yellow-500 equivalent
                ':hover': {
                  backgroundColor: rating === star ? "#fef9c3" : "#f3f4f6"
                }
              }}
            >
              <span>{star}</span>
              <span style={{ marginLeft: "0.25rem" }}>⭐</span>
            </button>
          ))}
        </div>
        
        <textarea
          style={{
            width: "100%",
            borderWidth: "1px",
            borderColor: "#d1d5db",
            borderRadius: "0.375rem",
            padding: "0.5rem",
            fontSize: "0.875rem",
            marginBottom: "1rem"
          }}
          rows={3}
          placeholder="Optional notes..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
          <button
            onClick={onClose}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "0.875rem",
              borderWidth: "1px",
              borderRadius: "0.375rem",
              color: "#4b5563",
              backgroundColor: "white"
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "0.875rem",
              backgroundColor: "#16a34a", // green-600 equivalent
              color: "white",
              borderRadius: "0.375rem"
            }}
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
};

export default FeedbackModal;