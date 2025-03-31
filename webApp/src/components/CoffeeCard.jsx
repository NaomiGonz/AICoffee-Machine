import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * CoffeeCard Component
 * @param {number} id - Coffee ID
 * @param {string} name - Name of the coffee
 * @param {string} image - Image URL of the coffee
 * @param {string} description - Short description of the coffee
 */
const CoffeeCard = ({ id, name, image, description }) => {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/coffee/${id}`);
  };

  return (
    <div
      onClick={handleClick}
      className="w-48 md:w-56 flex-shrink-0 rounded-2xl overflow-hidden bg-white shadow-md hover:shadow-lg transition duration-300 ease-in-out cursor-pointer border border-gray-100"
    >
      {/* Coffee Image */}
      <img
        className="w-full h-36 object-cover object-center"
        src={image}
        alt={name}
      />

      {/* Bottom Section */}
      <div className="px-4 py-3">
        <div className="text-lg font-semibold text-[var(--color-roast)] mb-1 truncate">
          {name}
        </div>
        <p className="text-sm text-gray-600 leading-snug">
          {description}
        </p>
      </div>
    </div>
  );
};

export default CoffeeCard;