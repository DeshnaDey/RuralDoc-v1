"use client";

import { useEffect, useState } from 'react';
import { Users, AlertTriangle, Activity, X, FileText, Thermometer, FlaskConical } from 'lucide-react';
import StatCard from '@/components/StatCard';
import AppointmentList from '@/components/AppointmentList';
import { fetchDashboardStats, fetchAppointments, DashboardStats, Patient } from '@/lib/api';
import { useWebSocket } from '@/hooks/useWebSocket';

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [appointments, setAppointments] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);

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
    <>
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
      <AppointmentList appointments={appointments} onPatientClick={(p) => setSelectedPatient(p)} />
    </div>

    {selectedPatient && (
      <div className="fixed inset-0 z-50 flex justify-end">
        <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={() => setSelectedPatient(null)} />
        <div className="relative w-full max-w-md bg-white shadow-2xl flex flex-col h-full animate-in slide-in-from-right duration-300">
          <div className="flex items-center justify-between p-6 border-b border-[rgba(90,173,168,0.2)]">
            <div>
              <h2 className="text-xl font-bold text-[#0f2b2a]">{selectedPatient.name}</h2>
              <p className="text-sm text-[#7bbfba]">{selectedPatient.age} yrs • {selectedPatient.gender} • {selectedPatient.location}</p>
            </div>
            <button onClick={() => setSelectedPatient(null)} className="p-2 rounded-xl hover:bg-[rgba(90,173,168,0.1)] transition-colors">
              <X className="w-5 h-5 text-[#3d7a76]" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div className="rounded-xl p-4" style={{ backgroundColor: 'rgba(90,173,168,0.1)', border: '1px solid rgba(90,173,168,0.2)' }}>
              <div className="flex items-center gap-2 mb-3">
                <FileText className="w-4 h-4 text-[#5aada8]" />
                <h3 className="font-semibold text-[#0f2b2a] text-sm">Chief Complaint</h3>
              </div>
              <p className="text-sm text-[#3d7a76]">{selectedPatient.reason}</p>
            </div>
            <div className="rounded-xl p-4" style={{ backgroundColor: 'rgba(90,173,168,0.1)', border: '1px solid rgba(90,173,168,0.2)' }}>
              <div className="flex items-center gap-2 mb-3">
                <Thermometer className="w-4 h-4 text-[#5aada8]" />
                <h3 className="font-semibold text-[#0f2b2a] text-sm">Status</h3>
              </div>
              <p className="text-sm text-[#3d7a76] capitalize">{selectedPatient.status}</p>
            </div>
            <div className="rounded-xl p-4" style={{ backgroundColor: 'rgba(90,173,168,0.1)', border: '1px solid rgba(90,173,168,0.2)' }}>
              <div className="flex items-center gap-2 mb-3">
                <FlaskConical className="w-4 h-4 text-[#5aada8]" />
                <h3 className="font-semibold text-[#0f2b2a] text-sm">Appointment Time</h3>
              </div>
              <p className="text-sm text-[#3d7a76]">{selectedPatient.time}</p>
            </div>
          </div>
        </div>
      </div>
    )}
    </>
  );
}
