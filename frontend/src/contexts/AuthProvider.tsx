import React, { useMemo, useState } from 'react';
import type { User } from '../lib/api';
import { AuthContext } from './auth-core';

function readStoredAuth(): { token: string | null; user: User | null } {
  const token = localStorage.getItem('token');
  const storedUser = localStorage.getItem('user');
  return { token, user: storedUser ? (JSON.parse(storedUser) as User) : null };
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [auth, setAuth] = useState(readStoredAuth);

  const login = (token: string, user: User) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
    setAuth({ token, user });
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setAuth({ token: null, user: null });
  };

  const value = useMemo(
    () => ({
      user: auth.user,
      token: auth.token,
      isAuthenticated: Boolean(auth.token),
      login,
      logout,
    }),
    [auth],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
