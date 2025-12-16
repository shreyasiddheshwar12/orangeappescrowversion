import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider, useAuth } from './lib/auth';

// Pages
import Landing from './pages/Landing';
import Login from './pages/Login';
import Signup from './pages/Signup';
import CreatorOnboarding from './pages/onboarding/CreatorOnboarding';
import BusinessOnboarding from './pages/onboarding/BusinessOnboarding';
import CreatorDashboard from './pages/dashboard/CreatorDashboard';
import BusinessDashboard from './pages/dashboard/BusinessDashboard';
import CreatorProfile from './pages/profile/CreatorProfile';
import BusinessProfile from './pages/profile/BusinessProfile';
import Chat from './pages/Chat';

import './App.css';

// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen gradient-hero flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-primary rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse">
            <span className="text-3xl">🍊</span>
          </div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={user.role === 'creator' ? '/dashboard/creator' : '/dashboard/business'} replace />;
  }

  return children;
};

// Public Route (redirects if already logged in)
const PublicRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen gradient-hero flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-primary rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse">
            <span className="text-3xl">🍊</span>
          </div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (user) {
    if (!user.hasCompletedOnboarding) {
      return <Navigate to={user.role === 'creator' ? '/onboarding/creator' : '/onboarding/business'} replace />;
    }
    return <Navigate to={user.role === 'creator' ? '/dashboard/creator' : '/dashboard/business'} replace />;
  }

  return children;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/signup" element={<PublicRoute><Signup /></PublicRoute>} />
      
      {/* Onboarding Routes */}
      <Route 
        path="/onboarding/creator" 
        element={
          <ProtectedRoute allowedRoles={['creator']}>
            <CreatorOnboarding />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/onboarding/business" 
        element={
          <ProtectedRoute allowedRoles={['business']}>
            <BusinessOnboarding />
          </ProtectedRoute>
        } 
      />
      
      {/* Dashboard Routes */}
      <Route 
        path="/dashboard/creator" 
        element={
          <ProtectedRoute allowedRoles={['creator']}>
            <CreatorDashboard />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/dashboard/business" 
        element={
          <ProtectedRoute allowedRoles={['business']}>
            <BusinessDashboard />
          </ProtectedRoute>
        } 
      />
      
      {/* Public Profile Routes */}
      <Route path="/profile/creator/:id" element={<CreatorProfile />} />
      <Route path="/profile/business/:id" element={<BusinessProfile />} />
      
      {/* Chat Route */}
      <Route 
        path="/chat/:requestId" 
        element={
          <ProtectedRoute>
            <Chat />
          </ProtectedRoute>
        } 
      />
      
      {/* Catch all - redirect to landing */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster 
          position="top-center" 
          toastOptions={{
            style: {
              background: '#fff',
              border: '1px solid #FFD8C2',
              borderRadius: '1rem',
            },
          }}
        />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
