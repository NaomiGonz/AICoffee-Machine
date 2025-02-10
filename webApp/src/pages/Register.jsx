import React, { useState } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../tools/AuthProvider.jsx';
import { signUp } from '../tools/auth';
import Button from '../components/Button.jsx';

const Register = () => {
  const { userLoggedIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setErrorMessage("Passwords do not match");
      return;
    }
    if (!isRegistering) {
      setIsRegistering(true);
      const user = await signUp(email, password);
      if (!user) {
        setErrorMessage('Registration failed');
        setIsRegistering(false);
      }
      // On success, the AuthProvider updates currentUser and redirection occurs.
    }
  };

  if (userLoggedIn) {
    return <Navigate to="/home" replace />;
  }

  return (
    <main 
      className="w-full h-screen flex items-center justify-center" 
      style={{ backgroundColor: '#CAF7E2' }}
    >
      <div 
        className="w-96 space-y-5 p-6 shadow-xl border rounded-xl" 
        style={{ borderColor: '#3D3522', backgroundColor: '#FFF', color: '#4A442D' }}
      >
        <div className="text-center mb-6">
          <h3 className="text-xl font-semibold">Create a New Account</h3>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-bold">Email</label>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full mt-2 px-3 py-2 bg-transparent outline-none border focus:border-[#58B09C] shadow-sm rounded-lg transition duration-300"
              style={{ borderColor: '#3D3522' }}
            />
          </div>
          <div>
            <label className="text-sm font-bold">Password</label>
            <input
              type="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isRegistering}
              className="w-full mt-2 px-3 py-2 bg-transparent outline-none border focus:border-[#58B09C] shadow-sm rounded-lg transition duration-300"
              style={{ borderColor: '#3D3522' }}
            />
          </div>
          <div>
            <label className="text-sm font-bold">Confirm Password</label>
            <input
              type="password"
              autoComplete="off"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={isRegistering}
              className="w-full mt-2 px-3 py-2 bg-transparent outline-none border focus:border-[#58B09C] shadow-sm rounded-lg transition duration-300"
              style={{ borderColor: '#3D3522' }}
            />
          </div>
          {errorMessage && (
            <span className="text-red-600 font-bold">{errorMessage}</span>
          )}
          <Button 
            type="submit"
            text={isRegistering ? 'Signing Up...' : 'Sign Up'}
            onClick={handleSubmit}
            disabled={isRegistering}
            color="#386150"
            transparent={false}
            className="w-full"
          />
          <div className="text-center text-sm" style={{ color: '#4A442D' }}>
            Already have an account?{' '}
            <Link to="/login" className="hover:underline font-bold" style={{ color: '#386150' }}>
              Continue
            </Link>
          </div>
        </form>
      </div>
    </main>
  );
};

export default Register;
