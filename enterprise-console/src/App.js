import React, { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import { useSelector } from 'react-redux';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard/Dashboard';
import FleetManagement from './pages/FleetManagement/FleetManagement';
import SystemMonitoring from './pages/SystemMonitoring/SystemMonitoring';
import Security from './pages/Security/Security';
import Compliance from './pages/Compliance/Compliance';
import Deployment from './pages/Deployment/Deployment';
import Settings from './pages/Settings/Settings';
import Login from './pages/Auth/Login';
import { selectIsAuthenticated } from './store/slices/authSlice';

// Lazy load components for better performance
const FleetManagement = React.lazy(() => import('./pages/FleetManagement/FleetManagement'));
const SystemMonitoring = React.lazy(() => import('./pages/SystemMonitoring/SystemMonitoring'));
const Security = React.lazy(() => import('./pages/Security/Security'));
const Compliance = React.lazy(() => import('./pages/Compliance/Compliance'));
const Deployment = React.lazy(() => import('./pages/Deployment/Deployment'));
const Settings = React.lazy(() => import('./pages/Settings/Settings'));

// Loading component for lazy loading
const LoadingFallback = () => (
  <Box
    display="flex"
    justifyContent="center"
    alignItems="center"
    minHeight="100vh"
  >
    <CircularProgress size={60} thickness={4} />
  </Box>
);

// Protected Route component
const ProtectedRoute = ({ children }) => {
  const isAuthenticated = useSelector(selectIsAuthenticated);
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

function App() {
  return (
    <div className="App">
      <Routes>
        {/* Authentication Routes */}
        <Route path="/login" element={<Login />} />
        
        {/* Protected Routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout>
                <Suspense fallback={<LoadingFallback />}>
                  <Routes>
                    <Route index element={<Dashboard />} />
                    <Route path="dashboard" element={<Dashboard />} />
                    <Route path="fleet" element={<FleetManagement />} />
                    <Route path="monitoring" element={<SystemMonitoring />} />
                    <Route path="security" element={<Security />} />
                    <Route path="compliance" element={<Compliance />} />
                    <Route path="deployment" element={<Deployment />} />
                    <Route path="settings" element={<Settings />} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </Suspense>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  );
}

export default App;