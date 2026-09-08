'use client';

import React, { useState } from 'react';
import { Lock } from 'lucide-react';
import { Modal } from './ui/Modal';
import { useAuthStore } from '@/store/authStore';

interface LoginModalProps {
  open: boolean;
  onClose: () => void;
}

export function LoginModal({ open, onClose }: LoginModalProps) {
  const login = useAuthStore((s) => s.login);
  const error = useAuthStore((s) => s.error);
  const clearError = useAuthStore((s) => s.clearError);
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!employeeId || !password) return;
    setSubmitting(true);
    try {
      await login(employeeId, password);
      setEmployeeId('');
      setPassword('');
      onClose();
    } catch {
      // error is already surfaced via the store's `error` field
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={() => {
        clearError();
        onClose();
      }}
      title="Sign in"
      description="Authenticate with a real RailOS account instead of the demo role selector."
      maxWidthClassName="max-w-sm"
    >
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
          <Lock className="h-3.5 w-3.5" aria-hidden="true" />
          <span>Argon2 + JWT — verified server-side, not a role you choose.</span>
        </div>

        <div>
          <label htmlFor="login-employee-id" className="block text-xs font-mono font-bold uppercase tracking-wide text-[var(--text-muted)] mb-1">
            Employee ID
          </label>
          <input
            id="login-employee-id"
            type="text"
            autoComplete="username"
            required
            placeholder="e.g. EMP901"
            value={employeeId}
            onChange={(e) => setEmployeeId(e.target.value)}
            className="w-full min-h-11 px-3 rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] text-sm text-[var(--text-primary)] font-mono focus:outline-none focus:border-[var(--accent)]"
          />
        </div>

        <div>
          <label htmlFor="login-password" className="block text-xs font-mono font-bold uppercase tracking-wide text-[var(--text-muted)] mb-1">
            Password
          </label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            required
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full min-h-11 px-3 rounded border border-[var(--border-strong)] bg-[var(--bg-surface)] text-sm text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)]"
          />
        </div>

        {error && (
          <div role="alert" className="rounded border border-[var(--status-critical-border)] bg-[var(--status-critical-bg)] px-3 py-2 text-xs text-[var(--status-critical-text)]">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => {
              clearError();
              onClose();
            }}
            className="min-h-11 px-3 rounded border border-[var(--border-default)] text-xs font-semibold text-[var(--text-secondary)] hover:border-[var(--border-strong)]"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !employeeId || !password}
            className="min-h-11 px-4 rounded bg-[var(--accent)] text-xs font-bold text-white disabled:opacity-50"
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
