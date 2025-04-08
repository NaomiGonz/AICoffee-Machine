import React, { useState } from "react";

const FeedbackModal = ({ isOpen, onClose, onSubmit }) => {
  const [rating, setRating] = useState(null);
  const [notes, setNotes] = useState("");

  const handleSubmit = () => {
    if (!rating) return alert("Please select a rating.");
    onSubmit(rating, notes);
    setRating(null);
    setNotes("");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-lg p-6 w-[90%] max-w-md space-y-4">
        <h2 className="text-lg font-semibold">Leave Feedback</h2>
        <div className="flex space-x-2">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              onClick={() => setRating(star)}
              className={`px-3 py-1 rounded ${
                rating === star ? "bg-yellow-400 text-white" : "bg-gray-200"
              }`}
            >
              {star} ⭐
            </button>
          ))}
        </div>
        <textarea
          className="w-full border border-gray-300 rounded-md p-2 text-sm"
          rows={3}
          placeholder="Optional notes..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        <div className="flex justify-end space-x-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm border rounded-md text-gray-600 hover:bg-gray-100"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 text-sm bg-[var(--color-hgreen)] text-white rounded-md hover:bg-[var(--color-roast)]"
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
};

export default FeedbackModal;
