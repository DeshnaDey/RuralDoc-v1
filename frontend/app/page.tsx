"use client";

import { useEffect, useState } from 'react';
import { Users, AlertTriangle, Activity } from 'lucide-react';
import StatCard from '@/components/StatCard';
import AppointmentList from '@/components/AppointmentList';
import { fetchDashboardStats, fetchAppointments, DashboardStats, Patient } from '@/lib/api';
import { useWebSocket } from '@/hooks/useWebSocket';

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [appointments, setAppointments] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);

  const { isConnected } = useWebSocket();

  useEffect(() => {
    async function loadDashboardData() {
      try {
        const [statsData, appointmentsData] = await Promise.all([
          fetchDashboardStats(),
          fetchAppointments()
        ]);
        setStats(statsData);
        setAppointments(appointmentsData);
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      } finally {
        setLoading(false);
      }
    }

    loadDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-4 text-[#7bbfba]">
          <Activity className="w-8 h-8 animate-spin" style={{ color: '#5aada8' }} />
          <p className="text-[#3d7a76]">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[#0f2b2a] tracking-tight">Good morning, Dr. Sharma</h1>
          <p className="text-[#7bbfba] mt-1">Here is what's happening at the clinic today.</p>
        </div>

        {/* Connection Status */}
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium"
          style={{ backgroundColor: 'rgba(90,173,168,0.15)', border: '1px solid rgba(90,173,168,0.28)' }}
        >
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-red-400'}`} />
          <span className="text-[#3d7a76]">{isConnected ? 'System Connected' : 'System Offline'}</span>
        </div>
      </div>

      {/* Stats Grid — 3 cards (no Budget) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Total Patients Today"
          value={stats?.totalPatientsToday || 0}
          icon={Users}
          trend={{ value: '12%', positive: true }}
        />
        <StatCard
          title="Critical Cases"
          value={stats?.criticalCases || 0}
          icon={AlertTriangle}
          trend={{ value: '2', positive: false }}
        />
        <StatCard
          title="Active Scenarios"
          value={stats?.activeScenarios || 0}
          icon={Activity}
        />
      </div>

      {/* Appointments — full width */}
      <AppointmentList appointments={appointments} />
    </div>
  );
}
