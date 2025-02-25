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
      // Fixed width on small screens, larger on md+, prevent shrink
      className="w-48 md:w-56 flex-shrink-0 rounded-lg overflow-hidden shadow-lg opacity-90 cursor-pointer  bg-hgreen"
    >
      {/* Coffee Image */}
      <img className="w-full h-auto rounded-t-lg" src={image} alt={name} />

      {/* Bottom Section */}
      <div className="px-6 py-4 rounded-b-lg">
        <div className="font-bold text-xl mb-2 text-white">{name}</div>
        <p className="text-sm text-white">
          {description}
        </p>
      </div>
    </div>
  );
};

export default CoffeeCard;


