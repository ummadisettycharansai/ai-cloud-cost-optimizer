import React, { createContext, useContext, useState } from 'react';

export type Role = 'admin' | 'finance' | 'viewer';

export interface Permissions {
  canSeeFinancials: boolean;
  canSeeAnomalies: boolean;
  canSeeAutopilot: boolean;
  canSeeAlerts: boolean;
  canSeeRecommendations: boolean;
  canSeeBudgets: boolean;
  canSeeForecast: boolean;
  canSeeServiceCost: boolean;
  canSeeKubernetes: boolean;
  canSeeOrganizations: boolean;
  canSeeAIEngine: boolean;
}

export const ROLE_PERMISSIONS: Record<Role, Permissions> = {
  admin: {
    canSeeFinancials: true,
    canSeeAnomalies: true,
    canSeeAutopilot: true,
    canSeeAlerts: true,
    canSeeRecommendations: true,
    canSeeBudgets: true,
    canSeeForecast: true,
    canSeeServiceCost: true,
    canSeeKubernetes: true,
    canSeeOrganizations: true,
    canSeeAIEngine: true,
  },
  finance: {
    canSeeFinancials: true,
    canSeeAnomalies: true,
    canSeeAutopilot: false,
    canSeeAlerts: true,
    canSeeRecommendations: true,
    canSeeBudgets: true,
    canSeeForecast: true,
    canSeeServiceCost: true,
    canSeeKubernetes: true,
    canSeeOrganizations: false,
    canSeeAIEngine: false,
  },
  viewer: {
    canSeeFinancials: false,
    canSeeAnomalies: true,
    canSeeAutopilot: false,
    canSeeAlerts: true,
    canSeeRecommendations: true,
    canSeeBudgets: false,
    canSeeForecast: false,
    canSeeServiceCost: false,
    canSeeKubernetes: false,
    canSeeOrganizations: false,
    canSeeAIEngine: false,
  },
};

interface AuthContextType {
  role: Role;
  setRole: (role: Role) => void;
  permissions: Permissions;
  isAdmin: boolean;
  isFinance: boolean;
  isAdminOrFinance: boolean;
}

const AuthContext = createContext<AuthContextType>({
  role: 'admin',
  setRole: () => { },
  permissions: ROLE_PERMISSIONS.admin,
  isAdmin: true,
  isFinance: false,
  isAdminOrFinance: true,
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [role, setRole] = useState<Role>('admin');

  const isAdmin = role === 'admin';
  const isFinance = role === 'finance';
  const isAdminOrFinance = isAdmin || isFinance;

    const currentPermissions = ROLE_PERMISSIONS[role] || ROLE_PERMISSIONS.viewer;
  
    return (
      <AuthContext.Provider value={{
        role,
        setRole,
        permissions: currentPermissions,
        isAdmin,
        isFinance,
        isAdminOrFinance
      }}>
      {children}
    </AuthContext.Provider>
  );
};
