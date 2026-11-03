import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { UserCheck } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter both email and password.');
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      await login({ email, password });
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Invalid email or password.';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen w-screen items-center justify-center bg-bg p-4 font-sans text-ink">
      <div className="w-full max-w-[400px] space-y-6">
        {/* App Wordmark / Header */}
        <div className="text-center space-y-1.5">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-ctl bg-accent-600 text-surface font-semibold text-base shadow-sm">
            R
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-ink">RosterOps</h1>
          <p className="text-xs text-ink-2">Smart Roster Management & Optimization</p>
        </div>

        {/* Login Card */}
        <div className="rounded-ctl border border-border bg-surface p-6 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-ink">Sign in to your account</h2>
              <p className="text-[11px] text-ink-3">Enter your credentials below to access the workspace</p>
            </div>

            {error && (
              <div className="rounded-ctl border border-bad/30 bg-bad/5 p-2.5 text-xs text-bad">
                {error}
              </div>
            )}

            <div className="space-y-3">
              <Input
                label="Work Email"
                type="email"
                required
                autoComplete="email"
                placeholder="name@example.test"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />

              <Input
                label="Password"
                type="password"
                required
                autoComplete="current-password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full h-9 text-xs"
              isLoading={isSubmitting}
            >
              Sign In
            </Button>
          </form>
        </div>

        {/* Security & System Info Footer */}
        <div className="flex items-center justify-center gap-2 text-[11px] text-ink-3">
          <UserCheck className="h-3.5 w-3.5" />
          <span>Role-Based Access Control Active</span>
        </div>
      </div>
    </div>
  );
};

