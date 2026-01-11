import { LoginForm } from '@/components/LoginForm';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

export function LoginPage() {
  const [isOpen, setIsOpen] = useState(true);
  const navigate = useNavigate();
  const { user, isLoading } = useAuth();

  // Redirect to dashboard if already logged in
  useEffect(() => {
    if (user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  const handleClose = () => {
    // If user is logged in, navigate to dashboard
    if (user) {
      navigate('/dashboard', { replace: true });
    }
  };
  
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <LoginForm isOpen={isOpen} onClose={handleClose} />
    </div>
  );
}
