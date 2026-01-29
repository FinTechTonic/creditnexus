import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { User, Settings, LogOut, ChevronDown, Shield } from 'lucide-react';

export function UserMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!user) {
    return null;
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-800 transition-colors"
      >
        {user.profile_image ? (
          <img
            src={user.profile_image}
            alt={user.display_name}
            className="w-8 h-8 rounded-full object-cover border-2 border-emerald-500"
          />
        ) : (
          <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-white font-semibold border-2 border-emerald-500">
            {user?.display_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
          </div>
        )}
        <div className="hidden md:block text-left">
          <p className="text-sm font-medium text-slate-100">{user?.display_name || user?.email || 'User'}</p>
          <p className="text-xs text-slate-400 capitalize">{user?.role}</p>
        </div>
        <ChevronDown className={`h-4 w-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      
      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-slate-800 border border-slate-700 rounded-lg shadow-lg z-50">
          <div className="p-2">
            <div className="px-3 py-2 border-b border-slate-700">
              <p className="text-sm font-semibold text-slate-100">{user?.display_name || 'User'}</p>
              <p className="text-xs text-slate-400">{user?.email}</p>
              {user?.organization && (
                <p className="text-xs text-slate-400 mt-1">{user.organization.name}</p>
              )}
            </div>
            
            <button
              onClick={() => {
                navigate('/settings');
                setIsOpen(false);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700 rounded mt-2"
            >
              <Settings className="h-4 w-4" />
              User Settings
            </button>
            
            {(user?.role === 'admin' || user?.organization_role === 'admin') && (
              <button
                onClick={() => {
                  navigate('/admin-settings');
                  setIsOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700 rounded"
              >
                <Shield className="h-4 w-4" />
                Admin Settings
              </button>
            )}
            
            <div className="border-t border-slate-700 mt-2 pt-2">
              <button
                onClick={() => {
                  logout();
                  setIsOpen(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-slate-700 rounded"
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
