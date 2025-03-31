import React from 'react';
import Button from './Button';

const BrewHistoryCard = ({ brew, onBrewAgain }) => {
  const { desired_flavor, parameters, timestamp } = brew;

  return (
    <div className="rounded-2xl bg-white shadow-md hover:shadow-lg transition p-4 space-y-4 border border-gray-100">
      <div className="text-[var(--color-roast)] font-semibold text-lg">
        Brewed on: {timestamp instanceof Date ? timestamp.toLocaleDateString() : 'Unknown'}
      </div>

      <div className="text-sm text-gray-700">
        <div className="mb-2 font-medium">Flavor Profile:</div>
        <ul className="ml-4 list-disc">
          <li>Bitterness: {desired_flavor?.maltiness}</li>
          <li>Acidity: {desired_flavor?.acidity}</li>
          <li>Sweetness: {desired_flavor?.sweetness}</li>
          <li>Strength: {desired_flavor?.strength}</li>
          <li>Fruitiness: {desired_flavor?.fruitiness}</li>
        </ul>
      </div>

      <div className="text-sm text-gray-700">
        <div className="mb-2 font-medium">Brew Settings:</div>
        <ul className="ml-4 list-disc">
          <li>Temperature: {parameters?.temperature}°C</li>
          <li>Pressure: {parameters?.extraction_pressure} bars</li>
          <li>Water: {parameters?.dose_size * 2.5}ml</li>
          <li>Beans: {parameters?.bean_type}</li>
        </ul>
      </div>

      <Button 
        text="Brew Again"
        onClick={onBrewAgain}
        color="var(--color-hgreen)"
        className="mt-2 w-full"
      />
    </div>
  );
};

export default BrewHistoryCard;
