import React, { useState } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../tools/AuthProvider.jsx';
import { signIn, signInWithGoogle } from '../tools/auth';
import { auth } from "../tools/firebase";
import Button from '../components/Button.jsx';
import googleIcon from '../assets/google-3.png';

const Login = () => {
  const { userLoggedIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSigningIn, setIsSigningIn] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isSigningIn) {
      setIsSigningIn(true);
      const user = await signIn(email, password);
      if (!user) {
        setErrorMessage('Invalid email or password');
        setIsSigningIn(false);
      }
      // On successful login, the AuthProvider will update and redirect.
    }
  };

  const handleGoogleSignIn = async (e) => {
    e.preventDefault();
    if (!isSigningIn) {
      setIsSigningIn(true);
      const result = await signInWithGoogle();
      if (!result) {
        setErrorMessage('Google sign-in failed');
        setIsSigningIn(false);
      }
      // On success, the AuthProvider will update and redirect.
    }
  };

  const logToken = async () => {
    const user = auth.currentUser;
    if (user) {
      const token = await user.getIdToken();
      console.log("Firebase ID Token:", token);
    } else {
      console.log("No user is signed in.");
    }
  };

  if (userLoggedIn) {
    logToken();
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
        <div className="text-center">
          <h3 className="text-xl font-semibold">Welcome Back</h3>
        </div>
        <form onSubmit={handleSubmit} className="space-y-5">
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
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full mt-2 px-3 py-2 bg-transparent outline-none border focus:border-[#58B09C] shadow-sm rounded-lg transition duration-300"
              style={{ borderColor: '#3D3522' }}
            />
          </div>
          {errorMessage && (
            <span className="text-red-600 font-bold">{errorMessage}</span>
          )}
          <Button 
            type="submit"
            text={isSigningIn ? 'Signing In...' : 'Sign In'}
            onClick={handleSubmit}
            disabled={isSigningIn}
            color="#386150" // Deep Brew (primary button color)
            transparent={false}
            className="w-full"
          />
        </form>
        <p className="text-center text-sm">
          Don't have an account?{' '}
          <Link to="/register" className="hover:underline font-bold" style={{ color: '#386150' }}>
            Sign up
          </Link>
        </p>
        <div className="flex items-center my-2">
          <div className="flex-grow border-t" style={{ borderColor: '#3D3522' }}></div>
          <span className="mx-2 font-bold" style={{ color: '#3D3522' }}>OR</span>
          <div className="flex-grow border-t" style={{ borderColor: '#3D3522' }}></div>
        </div>
        <Button 
          text={isSigningIn ? 'Signing In...' : 'Continue with Google'}
          onClick={handleGoogleSignIn}
          disabled={isSigningIn}
          color="#58B09C" // Latte (secondary button color)
          transparent={false}
          className="w-full"
          image={googleIcon}
        />
      </div>
    </main>
  );
};

export default Login;


