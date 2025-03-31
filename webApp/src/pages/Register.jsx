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
    }
  };

  if (userLoggedIn) {
    return <Navigate to="/home" replace />;
  }

  return (
    <main className="flex items-center justify-center min-h-screen bg-[var(--color-mint)]">
      <div className="w-full max-w-md px-6 py-8 bg-white border border-[var(--color-roast)] shadow-lg rounded-xl space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-extrabold text-[var(--color-espresso)] tracking-tight">Create a New Account</h1>
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
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isRegistering}
              className="w-full mt-1 px-3 py-2 border rounded-md outline-none focus:border-[var(--color-teal)] transition"
            />
          </div>

          <div>
            <label className="text-sm font-semibold text-[var(--color-espresso)]">Confirm Password</label>
            <input
              type="password"
              autoComplete="off"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={isRegistering}
              className="w-full mt-1 px-3 py-2 border rounded-md outline-none focus:border-[var(--color-teal)] transition"
            />
          </div>

          {errorMessage && (
            <div className="text-red-600 text-sm font-semibold">{errorMessage}</div>
          )}

          <Button 
            type="submit"
            text={isRegistering ? 'Signing Up...' : 'Sign Up'}
            onClick={handleSubmit}
            disabled={isRegistering}
            color="var(--color-hgreen)"
            className="w-full"
          />

          <p className="text-center text-sm text-[var(--color-espresso)]">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold hover:underline text-[var(--color-hgreen)]">
              Continue
            </Link>
          </p>
        </form>
      </div>
    </main>
  );
};

export default Register;
