import React from 'react';

const Button = ({ 
  color = 'var(--color-hgreen)', 
  transparent = false, 
  image = null, 
  text, 
  onClick, 
  disabled = false, 
  type = 'button', 
  className = '',
  icon = null,
  loading = false
}) => {
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

  const baseClasses = `
    inline-flex items-center justify-center gap-2
    px-4 py-2 rounded-lg font-medium
    transition duration-300 ease-in-out
    ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md'}
    ${className}
  `;

  return (
    <button 
      type={type}
      onClick={onClick} 
      disabled={disabled || loading}
      style={style}
      className={baseClasses}
    >
      {loading && (
        <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
      )}
      {icon && !loading && <span className="text-white">{icon}</span>}
      {image && !loading && <img src={image} alt="icon" className="w-5 h-5" />}
      {!loading && text}
    </button>
  );
};

export default Button;