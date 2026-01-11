/**
 * PermissionGate component for conditional rendering based on user permissions.
 * 
 * This component wraps children and only renders them if the user has the required permission(s).
 * 
 * @example
 * ```tsx
 * <PermissionGate permission={PERMISSION_DOCUMENT_CREATE}>
 *   <Button>Create Document</Button>
 * </PermissionGate>
 * 
 * <PermissionGate permissions={[PERMISSION_DEAL_VIEW, PERMISSION_DEAL_VIEW_OWN]} requireAll={false}>
 *   <DealList />
 * </PermissionGate>
 * ```
 */

import { ReactNode } from 'react';
import { usePermissions } from '@/hooks/usePermissions';

interface PermissionGateProps {
  /** Single permission to check */
  permission?: string;
  /** Multiple permissions to check */
  permissions?: string[];
  /** If true, user must have ALL permissions. If false, user needs ANY permission. Default: false */
  requireAll?: boolean;
  /** Children to render if permission check passes */
  children: ReactNode;
  /** Optional fallback to render if permission check fails */
  fallback?: ReactNode;
}

/**
 * PermissionGate component that conditionally renders children based on user permissions.
 * 
 * @param props - PermissionGate props
 * @returns Rendered children if permission check passes, or fallback/null if it fails
 */
export function PermissionGate({
  permission,
  permissions,
  requireAll = false,
  children,
  fallback = null,
}: PermissionGateProps): ReactNode {
  const { hasPermission, hasAnyPermission, hasAllPermissions } = usePermissions();

  // Validate props
  if (!permission && !permissions) {
    console.warn('PermissionGate: Either "permission" or "permissions" prop must be provided');
    return fallback;
  }

  if (permission && permissions) {
    console.warn('PermissionGate: Both "permission" and "permissions" provided. Using "permissions" array.');
  }

  // Determine which permissions to check
  const permsToCheck = permissions || (permission ? [permission] : []);

  // Check permissions
  let hasAccess = false;
  if (requireAll) {
    hasAccess = hasAllPermissions(permsToCheck);
  } else {
    hasAccess = hasAnyPermission(permsToCheck);
  }

  // Render children if access granted, otherwise render fallback
  return hasAccess ? <>{children}</> : <>{fallback}</>;
}
