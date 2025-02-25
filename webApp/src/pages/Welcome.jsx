import React from 'react';
import { Link } from 'react-router-dom';
import Button from '../components/Button.jsx';
import Logo from '../assets/logo.svg';

const Welcome = () => {
  return (
    <div 
      className="flex flex-col items-center justify-center h-screen w-screen" 
    >
      <img src={Logo} alt="AI Coffee Logo" className="w-40 h-40 mb-8" />
      <h1 className="text-4xl font-bold mb-8" style={{ color: '#4A442D' }}>
        Welcome to AI Coffee
      </h1>
      <Link to="/login">
        <Button 
          text="Login"
          onClick={() => {}}
          color="#386150"
          transparent={false}
        />
      </Link>
    </div>
  );

  
};

export default Welcome;




