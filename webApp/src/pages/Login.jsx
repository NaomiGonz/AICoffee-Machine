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
    <main className="w-full h-screen flex items-center justify-center bg-[var(--color-mint)]">
      <div className="w-full max-w-md px-6 py-8 bg-white border border-[var(--color-roast)] shadow-lg rounded-xl space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-extrabold text-[var(--color-espresso)] tracking-tight">Welcome Back</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="text-sm font-semibold text-[var(--color-espresso)]">Email</label>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full mt-1 px-3 py-2 border rounded-md outline-none focus:border-[var(--color-teal)] transition"
            />
          </div>

          <div>
            <label className="text-sm font-semibold text-[var(--color-espresso)]">Password</label>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full mt-1 px-3 py-2 border rounded-md outline-none focus:border-[var(--color-teal)] transition"
            />
          </div>

          {errorMessage && (
            <div className="text-red-600 text-sm font-semibold">{errorMessage}</div>
          )}

          <Button
            type="submit"
            text={isSigningIn ? 'Signing In...' : 'Sign In'}
            onClick={handleSubmit}
            disabled={isSigningIn}
            color="var(--color-hgreen)"
            className="w-full"
          />
        </form>

        <p className="text-center text-sm text-[var(--color-espresso)]">
          Don't have an account?{' '}
          <Link to="/register" className="font-semibold hover:underline text-[var(--color-hgreen)]">
            Sign up
          </Link>
        </p>

        <div className="flex items-center gap-4">
          <hr className="flex-grow border-t border-[var(--color-roast)]" />
          <span className="text-xs font-semibold text-[var(--color-roast)]">OR</span>
          <hr className="flex-grow border-t border-[var(--color-roast)]" />
        </div>

        <Button
          text={isSigningIn ? 'Signing In...' : 'Continue with Google'}
          onClick={handleGoogleSignIn}
          disabled={isSigningIn}
          color="var(--color-teal)"
          className="w-full"
          image={googleIcon}
        />
      </div>
    </main>
  );
};

export default Login;
