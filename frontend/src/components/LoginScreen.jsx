import React, { useState } from 'react';
import './LoginScreen.css';
import { useNavigate } from 'react-router-dom';

// Validation helpers
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const passwordRegex = /^(?=.*[0-9])(?=.*[!@#$%^&*])/; // at least one digit and one special char

export default function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  // Validate a single field and return an error string (or empty)
  const validateField = (name, value) => {
    if (name === 'email') {
      if (!value) return 'Email is required.';
      if (!emailRegex.test(value)) return 'Enter a valid email address.';
    }
    if (name === 'password') {
      if (!value) return 'Password is required.';
      if (value.length < 8) return 'Password must be at least 8 characters.';
      if (!passwordRegex.test(value))
        return 'Include at least one number and one special character.';
    }
    return '';
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    const errorMsg = validateField(name, value);
    setErrors((prev) => ({ ...prev, [name]: errorMsg }));
    setTouched((prev) => ({ ...prev, [name]: true }));
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name === 'email') setEmail(value);
    if (name === 'password') setPassword(value);
    // If already touched, re‑validate on change for real‑time feedback
    if (touched[name]) {
      const errorMsg = validateField(name, value);
      setErrors((prev) => ({ ...prev, [name]: errorMsg }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Validate all fields before submitting
    const emailError = validateField('email', email);
    const passwordError = validateField('password', password);
    const newErrors = { email: emailError, password: passwordError };
    setErrors(newErrors);
    setTouched({ email: true, password: true });
    if (emailError || passwordError) return; // block submit

    setIsSubmitting(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: email, password }),
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('jwt', data.access_token);
        const payload = JSON.parse(atob(data.access_token.split('.')[1]));
        localStorage.setItem('role', payload.role);
        navigate('/dashboard');
      } else {
        setErrors((prev) => ({ ...prev, form: data.detail || 'Login failed' }));
      }
    } catch (err) {
      setErrors((prev) => ({ ...prev, form: 'Network error' }));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-container">
      <form className="login-form" onSubmit={handleSubmit} noValidate>
        <h2 className="login-title">Welcome to MediAssist</h2>
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            type="email"
            id="email"
            name="email"
            value={email}
            onChange={handleChange}
            onBlur={handleBlur}
            className={errors.email ? 'input-error' : ''}
            placeholder="Enter your email address"
            disabled={isSubmitting}
          />
          {errors.email && <p className="error-msg">{errors.email}</p>}
        </div>
        <div className="form-group">
          <label htmlFor="password">Password</label>
          <div className="password-wrapper">
            <input
              type={showPassword ? 'text' : 'password'}
              id="password"
              name="password"
              value={password}
              onChange={handleChange}
              onBlur={handleBlur}
              className={errors.password ? 'input-error' : ''}
              placeholder="••••••••"
              disabled={isSubmitting}
            />
            <button
              type="button"
              className="toggle-visibility"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? '🙈' : '👁'}
            </button>
          </div>
          {errors.password && <p className="error-msg">{errors.password}</p>}
        </div>
        <button type="submit" className="submit-btn" disabled={isSubmitting}>
          {isSubmitting ? <span className="spinner" /> : 'Login'}
        </button>
      </form>
    </div>
  );
}
