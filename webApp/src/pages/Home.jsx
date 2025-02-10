import React from 'react';
import { useNavigate } from 'react-router-dom';
import { signOut } from '../tools/auth';
import Button from '../components/Button.jsx';

const Home = () => {
  const navigate = useNavigate();

  const handleLogout = async () => {
    await signOut();
    navigate('/login');
  };

  return (
    <div 
      className="flex flex-col items-center justify-center h-screen" 
      style={{ backgroundColor: '#CAF7E2' }}
    >
      <h1 className="text-3xl font-bold mb-8" style={{ color: '#4A442D' }}>
        Home Page
      </h1>
      <Button 
        text="Logout"
        onClick={handleLogout}
        color="#386150"
        transparent={false}
      />
    </div>
  );
};

export default Home;

