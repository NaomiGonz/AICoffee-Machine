import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import logo from '../assets/logo.svg'; // Adjust path to your logo
import Button from './Button.jsx';     // <-- Import your custom Button
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
      {/* Fixed Navbar */}
      <nav 
        className="fixed w-full z-20 shadow-lg"
        style={{ backgroundColor: 'var(--color-teal)' }}
      >
        <div className="max-w-7xl mx-auto px-4 flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link to="/home" className="text-2xl font-bold">
              <img 
                src={logo} 
                alt="Logo" 
                className="h-10 w-10 mr-2"
              />
            </Link>
            <span 
              className="hidden sm:block text-xl font-semibold font-mono" 
              style={{ color: 'var(--color-black)' }}
            >
              AI Coffee
            </span>
          </div>

          {/* Desktop Menu */}
          <div className="hidden md:flex space-x-6">
            <div className="pt-3 md:flex space-x-6">
            <Link 
              to="/home" 
              className="font-mono hover:opacity-80"
              style={{ color: 'var(--color-black)' }}
            >
              Home
            </Link>
            <Link 
              to="/machine" 
              className="font-mono hover:opacity-80"
              style={{ color: 'var(--color-black)' }}
            >
              Machine
            </Link>
            <Link 
              to="/account" 
              className="font-mono hover:opacity-80"
              style={{ color: 'var(--color-black)' }}
            >
              Account
            </Link>
            </div>
            {/* Logout using custom Button */}
            <Button 
              text="Logout"
              onClick={handleLogout}
              color="var(--color-hgreen)"
              transparent={false}
            />
          </div>

          {/* Mobile Hamburger Icon */}
          <div className="md:hidden">
            <button
              onClick={() => setNavbarOpen(!navbarOpen)}
              className="focus:outline-none"
              style={{ color: 'var(--color-espresso)' }}
            >
              <svg
                className="h-6 w-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                {navbarOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile Menu */}
      {navbarOpen && (
        <div 
          className="md:hidden fixed top-16 left-0 w-full shadow-lg z-10"
          style={{ backgroundColor: 'var(--color-mint)' }}
        >
          <div className="px-4 pt-2 pb-3 space-y-3">
            <Link
              to="/home"
              onClick={() => setNavbarOpen(false)}
              className="block font-mono hover:opacity-80"
              style={{ color: 'var(--color-espresso)' }}
            >
              Home
            </Link>
            <Link
              to="/machine"
              onClick={() => setNavbarOpen(false)}
              className="block font-mono hover:opacity-80"
              style={{ color: 'var(--color-espresso)' }}
            >
              Machine
            </Link>
            <Link
              to="/account"
              onClick={() => setNavbarOpen(false)}
              className="block font-mono hover:opacity-80"
              style={{ color: 'var(--color-espresso)' }}
            >
              Account
            </Link>
            {/* Logout Button */}
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
