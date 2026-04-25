'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight, X, Calendar, Clock, MapPin, User } from 'lucide-react';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];

const MOCK_APPOINTMENTS = [
  { id: '1', patientName: 'Sunita Devi', age: 34, gender: 'Female', date: '2026-04-26', time: '09:00', reason: 'Fever and chills', location: 'Raipur', status: 'worsening' },
  { id: '2', patientName: 'Ramesh Kumar', age: 52, gender: 'Male', date: '2026-04-26', time: '10:30', reason: 'Follow-up TB', location: 'Bilaspur', status: 'stable' },
  { id: '3', patientName: 'Priya Sharma', age: 28, gender: 'Female', date: '2026-04-26', time: '11:00', reason: 'Antenatal check', location: 'Durg', status: 'stable' },
  { id: '4', patientName: 'Mohan Lal', age: 61, gender: 'Male', date: '2026-04-25', time: '09:30', reason: 'Chest pain', location: 'Korba', status: 'critical' },
  { id: '5', patientName: 'Geeta Bai', age: 45, gender: 'Female', date: '2026-04-25', time: '14:00', reason: 'Diabetes follow-up', location: 'Raipur', status: 'stable' },
  { id: '6', patientName: 'Arjun Singh', age: 19, gender: 'Male', date: '2026-04-24', time: '10:00', reason: 'Snakebite', location: 'Jagdalpur', status: 'critical' },
  { id: '7', patientName: 'Kavita Patel', age: 38, gender: 'Female', date: '2026-04-23', time: '11:30', reason: 'Malaria screening', location: 'Bastar', status: 'stable' },
];

const STATUS_STYLES: Record<string, string> = {
  stable: 'bg-emerald-100 text-emerald-700',
  worsening: 'bg-amber-100 text-amber-700',
  critical: 'bg-red-100 text-red-700',
};

export default function AppointmentsPage() {
  const router = useRouter();
  const today = new Date();
  const [currentMonth, setCurrentMonth] = useState(today.getMonth());
  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [selectedDate, setSelectedDate] = useState(today.toISOString().split('T')[0]);
  const [selectedAppointment, setSelectedAppointment] = useState<typeof MOCK_APPOINTMENTS[0] | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
  const firstDay = new Date(currentYear, currentMonth, 1).getDay();

  const prevMonth = () => {
    if (currentMonth === 0) { setCurrentMonth(11); setCurrentYear(y => y - 1); }
    else setCurrentMonth(m => m - 1);
  };
  const nextMonth = () => {
    if (currentMonth === 11) { setCurrentMonth(0); setCurrentYear(y => y + 1); }
    else setCurrentMonth(m => m + 1);
  };

  const getAppointmentsForDate = (dateStr: string) =>
    MOCK_APPOINTMENTS.filter(a => a.date === dateStr);

  const selectedAppts = getAppointmentsForDate(selectedDate);

  const hasAppointments = (day: number) => {
    const d = `${currentYear}-${String(currentMonth + 1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
    return MOCK_APPOINTMENTS.some(a => a.date === d);
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[#0f2b2a] tracking-tight">Appointments</h1>
          <p className="text-[#7bbfba] mt-1">View and manage clinic appointments.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="px-4 py-2 rounded-xl text-white font-medium text-sm transition-colors"
          style={{ backgroundColor: '#5aada8' }}
        >
          + New Appointment
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar */}
        <div className="lg:col-span-1 rounded-2xl p-5 shadow-sm" style={{ backgroundColor: 'rgba(90,173,168,0.1)', border: '1px solid rgba(90,173,168,0.25)' }}>
          <div className="flex items-center justify-between mb-4">
            <button onClick={prevMonth} className="p-1.5 rounded-lg hover:bg-[rgba(90,173,168,0.2)] transition-colors">
              <ChevronLeft className="w-4 h-4 text-[#3d7a76]" />
            </button>
            <h2 className="font-bold text-[#0f2b2a]">{MONTHS[currentMonth]} {currentYear}</h2>
            <button onClick={nextMonth} className="p-1.5 rounded-lg hover:bg-[rgba(90,173,168,0.2)] transition-colors">
              <ChevronRight className="w-4 h-4 text-[#3d7a76]" />
            </button>
          </div>

          <div className="grid grid-cols-7 mb-2">
            {DAYS.map(d => (
              <div key={d} className="text-center text-xs font-semibold text-[#7bbfba] py-1">{d}</div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-y-1">
            {Array.from({ length: firstDay }).map((_, i) => <div key={`empty-${i}`} />)}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const day = i + 1;
              const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
              const isSelected = dateStr === selectedDate;
              const isToday = dateStr === today.toISOString().split('T')[0];
              const hasAppt = hasAppointments(day);
              return (
                <button
                  key={day}
                  onClick={() => setSelectedDate(dateStr)}
                  className={`relative w-8 h-8 mx-auto flex items-center justify-center rounded-full text-sm transition-colors ${
                    isSelected ? 'text-white font-bold' :
                    isToday ? 'font-bold text-[#3d8880]' :
                    'text-[#0f2b2a] hover:bg-[rgba(90,173,168,0.2)]'
                  }`}
                  style={isSelected ? { backgroundColor: '#5aada8' } : {}}
                >
                  {day}
                  {hasAppt && !isSelected && (
                    <span className="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-[#5aada8]" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Appointment list for selected date */}
        <div className="lg:col-span-2 rounded-2xl shadow-sm overflow-hidden" style={{ backgroundColor: 'rgba(90,173,168,0.08)', border: '1px solid rgba(90,173,168,0.25)' }}>
          <div className="p-5 border-b" style={{ borderColor: 'rgba(90,173,168,0.2)' }}>
            <h2 className="font-bold text-[#0f2b2a]">
              {new Date(selectedDate + 'T00:00:00').toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}
            </h2>
            <p className="text-sm text-[#7bbfba]">{selectedAppts.length} appointment{selectedAppts.length !== 1 ? 's' : ''}</p>
          </div>

          <div className="divide-y" style={{ borderColor: 'rgba(90,173,168,0.15)' }}>
            {selectedAppts.length === 0 ? (
              <div className="p-12 text-center text-[#7bbfba]">
                <Calendar className="w-8 h-8 mx-auto mb-3 opacity-40" />
                <p>No appointments on this day.</p>
              </div>
            ) : (
              selectedAppts.map(appt => (
                <div
                  key={appt.id}
                  className="p-4 flex items-center justify-between cursor-pointer transition-colors hover:bg-[rgba(90,173,168,0.1)]"
                  onClick={() => setSelectedAppointment(appt)}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0" style={{ backgroundColor: '#5aada8' }}>
                      {appt.patientName.split(' ').map(n => n[0]).join('').slice(0,2)}
                    </div>
                    <div>
                      <p className="font-semibold text-[#0f2b2a]">{appt.patientName}</p>
                      <p className="text-xs text-[#7bbfba]">{appt.age} yrs • {appt.gender} • {appt.reason}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${STATUS_STYLES[appt.status]}`}>
                      {appt.status}
                    </span>
                    <span className="text-sm text-[#3d7a76] font-medium">{appt.time}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Patient detail drawer */}
      {selectedAppointment && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={() => setSelectedAppointment(null)} />
          <div className="relative w-full max-w-md bg-white shadow-2xl flex flex-col h-full animate-in slide-in-from-right duration-300">
            <div className="flex items-center justify-between p-6 border-b" style={{ borderColor: 'rgba(90,173,168,0.2)' }}>
              <div>
                <h2 className="text-xl font-bold text-[#0f2b2a]">{selectedAppointment.patientName}</h2>
                <p className="text-sm text-[#7bbfba]">{selectedAppointment.age} yrs • {selectedAppointment.gender}</p>
              </div>
              <button onClick={() => setSelectedAppointment(null)} className="p-2 rounded-xl hover:bg-[rgba(90,173,168,0.1)] transition-colors">
                <X className="w-5 h-5 text-[#3d7a76]" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {[
                { icon: Clock, label: 'Time', value: selectedAppointment.time },
                { icon: Calendar, label: 'Date', value: selectedAppointment.date },
                { icon: User, label: 'Reason', value: selectedAppointment.reason },
                { icon: MapPin, label: 'Location', value: selectedAppointment.location },
              ].map(({ icon: Icon, label, value }) => (
                <div key={label} className="rounded-xl p-4" style={{ backgroundColor: 'rgba(90,173,168,0.1)', border: '1px solid rgba(90,173,168,0.2)' }}>
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className="w-4 h-4 text-[#5aada8]" />
                    <span className="text-xs font-semibold text-[#3d7a76] uppercase tracking-wide">{label}</span>
                  </div>
                  <p className="text-sm text-[#0f2b2a] font-medium">{value}</p>
                </div>
              ))}
              <button
                onClick={() => router.push(`/patients?id=${selectedAppointment.id}`)}
                className="w-full py-3 rounded-xl text-white font-semibold text-sm transition-colors mt-2"
                style={{ backgroundColor: '#5aada8' }}
              >
                View Full Patient History →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Appointment Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xl font-bold text-[#0f2b2a]">New Appointment</h2>
              <button onClick={() => setModalOpen(false)} className="text-[#7bbfba] hover:text-[#3d7a76] transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              {['Patient Name', 'Date', 'Time', 'Reason'].map(field => (
                <div key={field}>
                  <label className="block text-sm font-medium text-[#3d7a76] mb-1">{field}</label>
                  <input
                    type={field === 'Date' ? 'date' : field === 'Time' ? 'time' : 'text'}
                    className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none"
                    style={{ border: '1px solid rgba(90,173,168,0.4)', backgroundColor: 'rgba(90,173,168,0.05)' }}
                  />
                </div>
              ))}
              <button
                onClick={() => setModalOpen(false)}
                className="w-full py-2.5 rounded-xl text-white font-semibold text-sm mt-2"
                style={{ backgroundColor: '#5aada8' }}
              >
                Schedule Appointment
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
