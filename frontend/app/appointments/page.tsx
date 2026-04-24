'use client';

import { useState } from 'react';
import { Calendar, X } from 'lucide-react';

interface NewAppointmentForm {
  patientName: string;
  date: string;
  time: string;
  reason: string;
}

const EMPTY_FORM: NewAppointmentForm = {
  patientName: '',
  date: '',
  time: '',
  reason: '',
};

export default function AppointmentsPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<NewAppointmentForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      // When the backend /appointments endpoint is ready, replace with:
      // await fetch('/api/appointments', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(form) });
      await new Promise(resolve => setTimeout(resolve, 600)); // mock delay
      setSuccessMsg(`Appointment for "${form.patientName}" scheduled successfully.`);
      setForm(EMPTY_FORM);
      setTimeout(() => {
        setSuccessMsg('');
        setModalOpen(false);
      }, 1800);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Appointments</h1>
          <p className="text-slate-500 mt-1">Schedule and manage clinic appointments.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="bg-primary text-white px-4 py-2 rounded-lg font-medium hover:bg-primary-dark transition-colors"
        >
          New Appointment
        </button>
      </div>

      <div className="bg-white p-12 rounded-xl border border-slate-200 shadow-sm flex flex-col items-center justify-center text-center">
        <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center text-primary mb-4">
          <Calendar className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 mb-2">Scheduling Module</h2>
        <p className="text-slate-500 max-w-md">
          The full calendar and scheduling view is coming soon. Use the dashboard to view today's priority appointments.
        </p>
      </div>

      {/* New Appointment Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xl font-bold text-slate-900">New Appointment</h2>
              <button
                onClick={() => { setModalOpen(false); setForm(EMPTY_FORM); setSuccessMsg(''); }}
                className="text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {successMsg ? (
              <div className="py-8 text-center">
                <div className="text-emerald-600 font-medium text-lg">{successMsg}</div>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Patient Name *</label>
                  <input
                    name="patientName"
                    value={form.patientName}
                    onChange={handleChange}
                    required
                    placeholder="e.g. Sunita Devi"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Date *</label>
                    <input
                      name="date"
                      type="date"
                      value={form.date}
                      onChange={handleChange}
                      required
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Time *</label>
                    <input
                      name="time"
                      type="time"
                      value={form.time}
                      onChange={handleChange}
                      required
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Reason for Visit</label>
                  <textarea
                    name="reason"
                    value={form.reason}
                    onChange={handleChange}
                    rows={2}
                    placeholder="e.g. Follow-up, vaccination, fever"
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary resize-none"
                  />
                </div>

                <div className="flex gap-3 pt-1">
                  <button
                    type="button"
                    onClick={() => { setModalOpen(false); setForm(EMPTY_FORM); }}
                    className="flex-1 border border-slate-300 text-slate-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="flex-1 bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors disabled:opacity-60"
                  >
                    {submitting ? 'Scheduling…' : 'Schedule'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
