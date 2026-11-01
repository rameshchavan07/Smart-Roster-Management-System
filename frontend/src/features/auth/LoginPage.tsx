import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { DEMO_ACCOUNTS } from '../../config/demoAccounts';
import { getDemoAccountsApi } from '../../api/auth';
import type { DemoAccountInfo } from '../../types/auth';
import { ChevronDown, ChevronUp, Lock, ShieldCheck, UserCheck } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDemoDisclosure, setShowDemoDisclosure] = useState(false);
  const [remoteDemoAccounts, setRemoteDemoAccounts] = useState<DemoAccountInfo[] | null>(null);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  useEffect(() => {
    // Optionally fetch dynamic demo accounts from backend
    getDemoAccountsApi()
      .then((data) => setRemoteDemoAccounts(data))
      .catch(() => {
        // Fallback to local config if backend unreachable
      });
  }, []);

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

  const handleSelectDemoAccount = (demoEmail: string, demoPassword?: string | null) => {
    setEmail(demoEmail);
    setPassword(demoPassword || 'DemoPass123!');
    setError(null);
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

          {/* Evaluator Demo Access Disclosure */}
          <div className="mt-5 border-t border-border pt-4">
            <button
              type="button"
              onClick={() => setShowDemoDisclosure((prev) => !prev)}
              className="flex w-full items-center justify-between text-left text-xs font-medium text-ink-2 hover:text-ink focus:outline-none"
            >
              <span className="flex items-center gap-1.5 text-accent-700">
                <ShieldCheck className="h-3.5 w-3.5" />
                Demo Access (for Evaluators)
              </span>
              {showDemoDisclosure ? (
                <ChevronUp className="h-3.5 w-3.5 text-ink-3" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5 text-ink-3" />
              )}
            </button>

            {showDemoDisclosure && (
              <div className="mt-3 space-y-2 text-xs">
                <p className="text-[11px] text-ink-3 leading-relaxed">
                  Click any demo role to auto-populate credentials for evaluation:
                </p>

                <div className="space-y-1.5">
                  {(remoteDemoAccounts || DEMO_ACCOUNTS).map((account) => {
                    const pwd = ('default_password' in account ? account.default_password : null) || 'DemoPass123!';
                    return (
                      <button
                        key={account.email}
                        type="button"
                        onClick={() => handleSelectDemoAccount(account.email, pwd)}
                        className="w-full text-left rounded-ctl border border-border bg-surface-2 p-2 hover:border-accent-600 hover:bg-accent-50/50 transition-colors group"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-ink group-hover:text-accent-700">
                            {'roleLabel' in account ? account.roleLabel : account.role}
                          </span>
                          <span className="text-[10px] font-mono text-ink-3 bg-surface px-1.5 py-0.5 rounded border border-border">
                            {account.role}
                          </span>
                        </div>
                        <p className="mt-0.5 font-mono text-[11px] text-ink-2 truncate">{account.email}</p>
                        <p className="mt-0.5 text-[10px] text-ink-3 truncate">
                          {'description' in account ? account.description : account.scope}
                        </p>
                      </button>
                    );
                  })}
                </div>

                <div className="flex items-center gap-1.5 pt-1 text-[11px] text-ink-3">
                  <Lock className="h-3 w-3 shrink-0" />
                  <span>Default password: <code className="font-mono bg-surface px-1 py-0.5 rounded border border-border">DemoPass123!</code></span>
                </div>
              </div>
            )}
          </div>
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

