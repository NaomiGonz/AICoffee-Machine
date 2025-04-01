import React from "react";
import Button from "./Button";

const BrewHistoryCard = ({ brew, onBrewAgain, onSave, onDelete, hideSave = false, showName = false, isSaved = false }) => {
  const { desired_flavor, parameters, timestamp, name } = brew;

  return (
    <div className="bg-white rounded-lg shadow-md p-4 flex flex-col justify-between">
      <div>
        {showName && name && (
          <h3 className="text-xl font-semibold text-[var(--color-espresso)] mb-2">{name}</h3>
        )}
        <p className="text-sm text-gray-500 mb-2">
          Brewed on: {timestamp instanceof Date ? timestamp.toLocaleString() : "Unknown"}
        </p>

        <div className="text-sm text-gray-700 mb-2">
          <strong>Flavor:</strong>
          <ul className="list-disc list-inside">
            <li>Acidity: {desired_flavor.acidity}</li>
            <li>Sweetness: {desired_flavor.sweetness}</li>
            <li>Strength: {desired_flavor.strength}</li>
            <li>Fruitiness: {desired_flavor.fruitiness}</li>
            <li>Maltiness: {desired_flavor.maltiness}</li>
          </ul>
        </div>

        <div className="text-sm text-gray-700 mb-4">
          <strong>Settings:</strong>
          <ul className="list-disc list-inside">
            <li>Temp: {parameters.temperature}°C</li>
            <li>Pressure: {parameters.extraction_pressure} bars</li>
            <li>Dose: {parameters.dose_size}g</li>
            <li>Bean: {parameters.bean_type}</li>
          </ul>
        </div>
      </div>

      <div className="flex gap-2 flex-wrap mt-auto">
        {onBrewAgain && (
          <Button 
            text="Brew Again" 
            onClick={onBrewAgain} 
            color="var(--color-hgreen)" 
            transparent={false} 
            className="flex-1" 
          />
        )}
        {!hideSave && onSave && !isSaved && (
          <Button 
            text="Save" 
            onClick={() => onSave(brew)} 
            color="var(--color-hgreen)" 
            transparent={true} 
            className="flex-1" 
          />
        )}
        {!hideSave && isSaved && (
          <Button 
            text="Saved" 
            onClick={() => {}} 
            color="gray" 
            transparent={true} 
            className="flex-1 cursor-default" 
            disabled
          />
        )}
        {onDelete && (
          <Button 
            text="Remove from Saved" 
            onClick={onDelete} 
            color="#E74C3C" 
            transparent={true} 
            className="flex-1" 
          />
        )}
      </div>
    </div>
  );
};

export default BrewHistoryCard;