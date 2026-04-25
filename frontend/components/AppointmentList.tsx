'use client';

import { useRouter } from 'next/navigation';
import { Patient } from '@/lib/api';

interface AppointmentListProps {
  appointments: Patient[];
}

export default function AppointmentList({ appointments }: AppointmentListProps) {
  const router = useRouter();

  const getStatusBadge = (status: Patient['status']) => {
    switch (status) {
      case 'stable':
        return <span className="px-2.5 py-1 bg-emerald-100 text-emerald-700 text-xs font-medium rounded-full">Stable</span>;
      case 'worsening':
        return <span className="px-2.5 py-1 bg-amber-100 text-amber-700 text-xs font-medium rounded-full">Worsening</span>;
      case 'critical':
        return <span className="px-2.5 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">Critical</span>;
      default:
        return null;
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="p-6 border-b border-slate-200 flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900">Today's Appointments</h2>
        <button
          onClick={() => router.push('/appointments')}
          className="text-sm text-primary font-medium hover:text-primary-dark transition-colors"
        >
          View All
        </button>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 text-slate-500 text-sm border-b border-slate-200">
              <th className="font-medium p-4 pl-6">Patient</th>
              <th className="font-medium p-4">Time</th>
              <th className="font-medium p-4">Reason</th>
              <th className="font-medium p-4">Location</th>
              <th className="font-medium p-4 pr-6">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {appointments.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-slate-500">
                  No appointments scheduled for today.
                </td>
              </tr>
            ) : (
              appointments.map((patient) => (
                <tr key={patient.id} className="hover:bg-slate-50 transition-colors group cursor-pointer">
                  <td className="p-4 pl-6">
                    <div>
                      <p className="font-medium text-slate-900 group-hover:text-primary transition-colors">{patient.name}</p>
                      <p className="text-xs text-slate-500">{patient.age} yrs • {patient.gender}</p>
                    </div>
                  </td>
                  <td className="p-4 text-sm text-slate-600">{patient.time}</td>
                  <td className="p-4 text-sm text-slate-600">{patient.reason}</td>
                  <td className="p-4 text-sm text-slate-500">{patient.location}</td>
                  <td className="p-4 pr-6">{getStatusBadge(patient.status)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
