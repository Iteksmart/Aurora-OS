import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
  Alert,
} from '@mui/material';
import {
  Computer,
  Security,
  CloudUpload,
  TrendingUp,
  Warning,
  CheckCircle,
} from '@mui/icons-material';
import { useQuery } from 'react-query';
import { motion } from 'framer-motion';
import {
  SystemOverviewChart,
  FleetHealthChart,
  PerformanceMetrics,
  RecentActivity,
  AlertsPanel,
  QuickActions,
} from '../../components/Dashboard';
import { dashboardService } from '../../services/dashboardService';
import { formatNumber, formatBytes } from '../../utils/formatters';

const Dashboard = () => {
  const [timeRange, setTimeRange] = useState('24h');

  // Fetch dashboard data
  const {
    data: dashboardData,
    isLoading,
    error,
    refetch,
  } = useQuery(
    ['dashboard', timeRange],
    () => dashboardService.getDashboardData(timeRange),
    {
      refetchInterval: 30000, // Refresh every 30 seconds
      select: (data) => ({
        ...data,
        systemHealth: data.systemHealth || {
          cpu: 0,
          memory: 0,
          storage: 0,
          network: 0,
        },
        fleetMetrics: data.fleetMetrics || {
          totalDevices: 0,
          onlineDevices: 0,
          offlineDevices: 0,
          maintenanceDevices: 0,
        },
        alerts: data.alerts || [],
        recentActivity: data.recentActivity || [],
        performanceData: data.performanceData || [],
      }),
    }
  );

  useEffect(() => {
    const interval = setInterval(() => {
      refetch();
    }, 30000);

    return () => clearInterval(interval);
  }, [refetch]);

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <LinearProgress sx={{ width: '50%' }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        Failed to load dashboard data: {error.message}
      </Alert>
    );
  }

  const { systemHealth, fleetMetrics, alerts, recentActivity, performanceData } = dashboardData;

  const calculateSystemHealth = () => {
    const health = (
      systemHealth.cpu +
      systemHealth.memory +
      systemHealth.storage +
      systemHealth.network
    ) / 4;
    return Math.round(health);
  };

  const systemHealthPercentage = calculateSystemHealth();

  const StatCard = ({ title, value, icon, color, subtitle, trend }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <Card
        sx={{
          height: '100%',
          background: 'linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255,255,255,0.1)',
          '&:hover': {
            transform: 'translateY(-5px)',
            boxShadow: '0 10px 30px rgba(0,212,255,0.3)',
          },
          transition: 'all 0.3s ease',
        }}
      >
        <CardContent>
          <Box display="flex" alignItems="center" mb={2}>
            <Box
              sx={{
                backgroundColor: color,
                borderRadius: '12px',
                p: 1,
                mr: 2,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {icon}
            </Box>
            <Box flex={1}>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                {title}
              </Typography>
              <Typography variant="h4" fontWeight="bold" color="text.primary">
                {value}
              </Typography>
              {subtitle && (
                <Typography variant="body2" color="text.secondary">
                  {subtitle}
                </Typography>
              )}
            </Box>
          </Box>
          {trend && (
            <Box display="flex" alignItems="center">
              <TrendingUp
                sx={{
                  color: trend > 0 ? 'success.main' : 'error.main',
                  fontSize: 16,
                  mr: 0.5,
                }}
              />
              <Typography
                variant="body2"
                color={trend > 0 ? 'success.main' : 'error.main'}
              >
                {Math.abs(trend)}%
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Box mb={4}>
        <Typography variant="h3" fontWeight="300" gutterBottom>
          Aurora-OS Enterprise Console
        </Typography>
        <Typography variant="h6" color="text.secondary">
          Real-time fleet management and monitoring dashboard
        </Typography>
      </Box>

      {/* Critical Alerts */}
      {alerts.filter(alert => alert.severity === 'critical').length > 0 && (
        <Box mb={3}>
          <AlertsPanel alerts={alerts.filter(alert => alert.severity === 'critical')} />
        </Box>
      )}

      {/* Key Metrics */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Fleet Devices"
            value={formatNumber(fleetMetrics.totalDevices)}
            icon={<Computer />}
            color="primary.main"
            subtitle={`${fleetMetrics.onlineDevices} online`}
            trend={5.2}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="System Health"
            value={`${systemHealthPercentage}%`}
            icon={<CheckCircle />}
            color={systemHealthPercentage > 80 ? 'success.main' : 'warning.main'}
            subtitle="Overall system status"
            trend={2.1}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Security Score"
            value="98%"
            icon={<Security />}
            color="success.main"
            subtitle="FIPS 140-2 compliant"
            trend={0.5}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Deployments"
            value="127"
            icon={<CloudUpload />}
            color="secondary.main"
            subtitle="This month"
            trend={12.3}
          />
        </Grid>
      </Grid>

      {/* System Health Overview */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={8}>
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <Card
              sx={{
                background: 'rgba(20, 25, 35, 0.8)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  System Performance
                </Typography>
                <SystemOverviewChart data={performanceData} />
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
        <Grid item xs={12} md={4}>
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <Card
              sx={{
                background: 'rgba(20, 25, 35, 0.8)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                height: '100%',
              }}
            >
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  Resource Usage
                </Typography>
                <PerformanceMetrics
                  metrics={[
                    {
                      label: 'CPU',
                      value: systemHealth.cpu,
                      color: 'primary.main',
                    },
                    {
                      label: 'Memory',
                      value: systemHealth.memory,
                      color: 'secondary.main',
                    },
                    {
                      label: 'Storage',
                      value: systemHealth.storage,
                      color: 'warning.main',
                    },
                    {
                      label: 'Network',
                      value: systemHealth.network,
                      color: 'info.main',
                    },
                  ]}
                />
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>

      {/* Fleet Status and Recent Activity */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <Card
              sx={{
                background: 'rgba(20, 25, 35, 0.8)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  Fleet Health Distribution
                </Typography>
                <FleetHealthChart data={fleetMetrics} />
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
        <Grid item xs={12} md={4}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
          >
            <Card
              sx={{
                background: 'rgba(20, 25, 35, 0.8)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                height: '100%',
              }}
            >
              <CardContent>
                <Typography variant="h5" gutterBottom>
                  Recent Activity
                </Typography>
                <RecentActivity activities={recentActivity} />
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>

      {/* Quick Actions */}
      <Box mt={4}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          <QuickActions />
        </motion.div>
      </Box>
    </Box>
  );
};

export default Dashboard;