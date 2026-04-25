'use client';

import { useRouter } from 'next/navigation';
import { Patient } from '@/lib/api';

interface AppointmentListProps {
  appointments: Patient[];
  onPatientClick?: (patient: Patient) => void;
}

export default function AppointmentList({ appointments, onPatientClick }: AppointmentListProps) {
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
    <div
      className="rounded-2xl shadow-sm overflow-hidden"
      style={{ backgroundColor: 'rgba(90, 173, 168, 0.15)', border: '1px solid rgba(90, 173, 168, 0.28)' }}
    >
      <div
        className="p-6 flex items-center justify-between"
        style={{ borderBottom: '1px solid rgba(90, 173, 168, 0.25)' }}
      >
        <h2 className="text-lg font-bold text-[#0f2b2a]">Today's Appointments</h2>
        <button
          onClick={() => router.push('/appointments')}
          className="text-sm font-semibold text-[#3d8880] hover:text-[#0f2b2a] transition-colors"
        >
          View All
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr
              className="text-sm"
              style={{ backgroundColor: 'rgba(90, 173, 168, 0.12)', borderBottom: '1px solid rgba(90, 173, 168, 0.2)' }}
            >
              <th className="font-semibold p-4 pl-6 text-[#3d7a76]">Patient</th>
              <th className="font-semibold p-4 text-[#3d7a76]">Time</th>
              <th className="font-semibold p-4 text-[#3d7a76]">Reason</th>
              <th className="font-semibold p-4 text-[#3d7a76]">Location</th>
              <th className="font-semibold p-4 pr-6 text-[#3d7a76]">Status</th>
            </tr>
          </thead>
          <tbody>
            {appointments.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-[#7bbfba]">
                  No appointments scheduled for today.
                </td>
              </tr>
            ) : (
              appointments.map((patient) => (
                <tr
                  key={patient.id}
                  className="group cursor-pointer transition-colors"
                  style={{ borderBottom: '1px solid rgba(90, 173, 168, 0.15)' }}
                  onClick={() => onPatientClick?.(patient)}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'rgba(90,173,168,0.1)')}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = '')}
                >
                  <td className="p-4 pl-6">
                    <p className="font-medium text-[#0f2b2a]">{patient.name}</p>
                    <p className="text-xs text-[#7bbfba]">{patient.age} yrs • {patient.gender}</p>
                  </td>
                  <td className="p-4 text-sm text-[#3d7a76]">{patient.time}</td>
                  <td className="p-4 text-sm text-[#3d7a76]">{patient.reason}</td>
                  <td className="p-4 text-sm text-[#7bbfba]">{patient.location}</td>
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
