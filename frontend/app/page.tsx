"use client";

import { useEffect, useState } from 'react';
import { Users, AlertTriangle, Wallet, Activity } from 'lucide-react';
import StatCard from '@/components/StatCard';
import AppointmentList from '@/components/AppointmentList';
import { fetchDashboardStats, fetchAppointments, DashboardStats, Patient } from '@/lib/api';
import { useWebSocket } from '@/hooks/useWebSocket';

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [appointments, setAppointments] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);

  // Initialize WebSocket connection for real-time simulation/LLM data later
  const { isConnected, lastMessage } = useWebSocket();

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
        <div className="flex flex-col items-center gap-4 text-slate-400">
          <Activity className="w-8 h-8 animate-spin text-primary" />
          <p>Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Good morning, Dr. Sharma</h1>
          <p className="text-slate-500 mt-1">Here is what's happening at the clinic today.</p>
        </div>
        
        {/* Connection Status Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 rounded-full text-sm font-medium">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
          <span className="text-slate-600">{isConnected ? 'System Connected' : 'System Offline'}</span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
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
        <StatCard 
          title="Budget Remaining" 
          value={`$${stats?.budgetRemaining || 0}`} 
          icon={Wallet} 
        />
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <AppointmentList appointments={appointments} />
        </div>
        <div className="space-y-6">
          {/* Quick Actions or Real-time Feed could go here */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-900 mb-4">Latest System Logs</h3>
            <div className="space-y-4 text-sm">
              {lastMessage ? (
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100 text-slate-600 font-mono text-xs overflow-hidden break-words">
                  {JSON.stringify(lastMessage, null, 2)}
                </div>
              ) : (
                <p className="text-slate-500 italic">Waiting for simulation data...</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
