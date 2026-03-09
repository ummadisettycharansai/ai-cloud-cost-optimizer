import React, { createContext, useContext, useState } from 'react';

type Role = 'admin' | 'finance' | 'viewer';

interface AuthContextType {
  role: Role;
  setRole: (role: Role) => void;
  isAdminOrFinance: boolean;
}

const AuthContext = createContext<AuthContextType>({
  role: 'admin',
  setRole: () => {},
  isAdminOrFinance: true,
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [role, setRole] = useState<Role>('admin');

  // Utility auth checks for RBAC
  const isAdminOrFinance = role === 'admin' || role === 'finance';

  return (
    <AuthContext.Provider value={{ role, setRole, isAdminOrFinance }}>
      {children}
    </AuthContext.Provider>
  );
};
