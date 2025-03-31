import React from 'react';
import { Link } from 'react-router-dom';
import Button from '../components/Button.jsx';
import Logo from '../assets/logo.svg';

const Welcome = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen w-screen bg-[var(--color-mint)] px-6 text-center">
      <img src={Logo} alt="AI Coffee Logo" className="w-32 h-32 mb-6" />
      <h1 className="text-3xl sm:text-4xl font-extrabold mb-6 text-[var(--color-espresso)] tracking-tight">
        Welcome to AI Coffee
      </h1>
      <p className="text-[var(--color-espresso)] text-sm mb-8 max-w-md">
        Your personalized brewing assistant — craft your perfect cup, learn your flavor profile, and enjoy coffee like never before.
      </p>
      <Link to="/login" className="w-full max-w-xs">
        <Button 
          text="Get Started"
          onClick={() => {}}
          color="var(--color-hgreen)"
          transparent={false}
          className="w-full"
        />
      </Link>
    </div>
  );
};

export default Welcome;