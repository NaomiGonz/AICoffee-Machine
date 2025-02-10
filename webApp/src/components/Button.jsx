import React from 'react';

const Button = ({ 
  color = '#386150', 
  transparent = false, 
  image = null, 
  text, 
  onClick, 
  disabled = false, 
  type = 'button', 
  className = '' 
}) => {
  // Filled vs not Filled style
  const style = transparent 
    ? { 
        border: `2px solid ${color}`, 
        color: color, 
        backgroundColor: 'transparent',
        cursor: disabled ? 'not-allowed' : 'pointer'
      }
    : { 
        backgroundColor: color, 
        color: '#fff', 
        border: 'none',
        cursor: disabled ? 'not-allowed' : 'pointer'
      };

  const baseClasses = `flex items-center justify-center gap-2 px-4 py-2 rounded-md font-medium transition duration-300 ${disabled ? 'opacity-50' : ''} ${className}`;

  return (
    <button 
      type={type}
      onClick={onClick} 
      disabled={disabled}
      style={style}
      className={baseClasses}
    >
      {image && (
        <img src={image} alt="icon" className="w-5 h-5" />
      )}
      {text}
    </button>
  );
};

export default Button;
