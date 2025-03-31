import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import logo from '../assets/logo.svg';
import Button from './Button.jsx';
import { signOut } from '../tools/auth';

function Navbar() {
  const [navbarOpen, setNavbarOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await signOut();
    navigate('/login');
  };

  return (
    <>
      <nav className="fixed w-full z-20 shadow-sm bg-[var(--color-teal)]">
        <div className="max-w-7xl mx-auto px-4 flex justify-between items-center h-16">
          <div className="flex items-center">
            <Link to="/home" className="flex items-center space-x-2">
              <img src={logo} alt="Logo" className="h-9 w-9" />
              <span className="text-lg font-semibold text-white tracking-tight font-mono hidden sm:block">
                AI Coffee
              </span>
            </Link>
          </div>

          <div className="hidden md:flex items-center space-x-6">
            <Link to="/home" className="text-white font-mono hover:underline">Home</Link>
            <Link to="/machine" className="text-white font-mono hover:underline">Machine</Link>
            <Link to="/account" className="text-white font-mono hover:underline">Account</Link>
            <Button 
              text="Logout"
              onClick={handleLogout}
              color="white"
              transparent={true}
              className="border-white"
            />
          </div>

          <div className="md:hidden">
            <button
              onClick={() => setNavbarOpen(!navbarOpen)}
              className="focus:outline-none text-white"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {navbarOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>
      </nav>

      {navbarOpen && (
        <div className="md:hidden fixed top-16 left-0 w-full z-10 bg-[var(--color-mint)] shadow-md">
          <div className="flex flex-col px-4 py-4 space-y-4 text-[var(--color-espresso)] font-mono">
            <Link to="/home" onClick={() => setNavbarOpen(false)}>Home</Link>
            <Link to="/machine" onClick={() => setNavbarOpen(false)}>Machine</Link>
            <Link to="/account" onClick={() => setNavbarOpen(false)}>Account</Link>
            <Button
              text="Logout"
              onClick={() => {
                setNavbarOpen(false);
                handleLogout();
              }}
              color="var(--color-hgreen)"
              transparent={false}
            />
          </div>
        </div>
      )}
    </>
  );
}

export default Navbar;
