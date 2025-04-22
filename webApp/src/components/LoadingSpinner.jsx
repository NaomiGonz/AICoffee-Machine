import React from "react";

const LoadingSpinner = ({ size = "md", color = "#386150" }) => {
  // Size classes
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12",
  };
  
  // Get the appropriate size class or default to md
  const sizeClass = sizeClasses[size] || sizeClasses.md;

  return (
    <div className="flex justify-center items-center">
      <div
        className={`${sizeClass} border-4 border-t-transparent rounded-full animate-spin`}
        style={{ borderColor: `${color} transparent transparent transparent` }}
      ></div>
    </div>
  );
};

export default LoadingSpinner;