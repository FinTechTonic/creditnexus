/**
 * React hook for checking user permissions.
 * 
 * This hook provides permission checking functionality based on the current user's role
 * and explicit permissions (if any).
 */

import { useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import {
  getRolePermissions,
  roleHasPermission,
  roleHasAnyPermission,
  roleHasAllPermissions,
} from '@/utils/permissions';

interface UsePermissionsReturn {
  /** Check if user has a specific permission */
  hasPermission: (permission: string) => boolean;
  /** Check if user has any of the specified permissions */
  hasAnyPermission: (permissions: string[]) => boolean;
  /** Check if user has all of the specified permissions */
  hasAllPermissions: (permissions: string[]) => boolean;
  /** Get all permissions for the current user */
  getUserPermissions: () => string[];
  /** Current user role */
  userRole: string | null;
  /** Whether user is authenticated */
  isAuthenticated: boolean;
}

/**
 * Hook to check user permissions based on role and explicit permissions.
 * 
 * @returns Permission checking functions and user information
 * 
 * @example
 * ```tsx
 * const { hasPermission, hasAnyPermission } = usePermissions();
 * 
 * if (hasPermission(PERMISSION_DOCUMENT_CREATE)) {
 *   // Show create document button
 * }
 * 
 * if (hasAnyPermission([PERMISSION_DEAL_VIEW, PERMISSION_DEAL_VIEW_OWN])) {
 *   // Show deal list
 * }
 * ```
 */
export function usePermissions(): UsePermissionsReturn {
  const { user, isAuthenticated } = useAuth();

  // Get user's explicit permissions from profile_data or permissions field
  // Note: Backend may store explicit permissions in user.permissions (JSONB) or user.profile_data
  const explicitPermissions = useMemo(() => {
    if (!user) return [];
    
    // Check if user has explicit permissions stored
    // This would come from the backend user object if it includes a permissions field
    // For now, we'll rely on role-based permissions
    // TODO: Add support for explicit user permissions when backend provides them
    return [];
  }, [user]);

  // Get role-based permissions
  const rolePermissions = useMemo(() => {
    if (!user?.role) return [];
    return getRolePermissions(user.role);
  }, [user?.role]);

  // Combine role permissions with explicit permissions
  const allPermissions = useMemo(() => {
    const perms = new Set(rolePermissions);
    explicitPermissions.forEach(perm => perms.add(perm));
    return Array.from(perms);
  }, [rolePermissions, explicitPermissions]);

  /**
   * Check if user has a specific permission.
   */
  const hasPermission = (permission: string): boolean => {
    if (!user?.role) return false;
    
    // Check explicit permissions first (override role permissions)
    if (explicitPermissions.includes(permission)) {
      return true;
    }
    
    // Check role permissions
    return roleHasPermission(user.role, permission);
  };

  /**
   * Check if user has any of the specified permissions.
   */
  const hasAnyPermission = (permissions: string[]): boolean => {
    if (!user?.role) return false;
    
    // Check explicit permissions first
    if (permissions.some(perm => explicitPermissions.includes(perm))) {
      return true;
    }
    
    // Check role permissions
    return roleHasAnyPermission(user.role, permissions);
  };

  /**
   * Check if user has all of the specified permissions.
   */
  const hasAllPermissions = (permissions: string[]): boolean => {
    if (!user?.role) return false;
    
    // Combine explicit and role permissions
    return permissions.every(perm => allPermissions.includes(perm));
  };

  /**
   * Get all permissions for the current user.
   */
  const getUserPermissions = (): string[] => {
    return allPermissions;
  };

  return {
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    getUserPermissions,
    userRole: user?.role || null,
    isAuthenticated,
  };
}
