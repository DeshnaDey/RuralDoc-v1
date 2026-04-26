'use client';

import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Phone, MapPin, Pill, AlertCircle, FileText, Activity } from 'lucide-react';

interface VisitEntry {
  date: string;
  diagnosis: string;
  treatment: string;
  doctor: string;
  notes: string;
  status: 'stable' | 'worsening' | 'critical';
}

interface PatientHistory {
  id: string;
  name: string;
  age: number;
  gender: string;
  location: string;
  phone: string;
  bloodGroup: string;
  allergies: string;
  currentMeds: string;
  visits: VisitEntry[];
  labResults: { date: string; test: string; result: string; flag: 'normal' | 'high' | 'low' }[];
}

const PATIENT_DB: Record<string, PatientHistory> = {
  case_01: {
    id: 'case_01', name: 'Rajesh Kumar', age: 45, gender: 'Male',
    location: 'Urban slum, Delhi', phone: '98100-11111', bloodGroup: 'B+',
    allergies: 'Penicillin', currentMeds: 'Rifampicin 600mg, INH 300mg',
    visits: [
      { date: '2026-04-24', diagnosis: 'Pulmonary TB (confirmed)', treatment: 'Continued DOTS regimen', doctor: 'Dr. Sharma', notes: 'Patient compliant. Sputum smear +ve at 2 months.', status: 'critical' },
      { date: '2026-03-10', diagnosis: 'Suspected TB', treatment: 'Sputum test ordered, DOTS initiated', doctor: 'Dr. Sharma', notes: 'Cough > 3 weeks, night sweats, weight loss.', status: 'critical' },
      { date: '2026-01-15', diagnosis: 'Chronic cough', treatment: 'Antibiotic course, CXR ordered', doctor: 'Dr. Sharma', notes: 'Initial presentation — CXR showed infiltrates.', status: 'worsening' },
    ],
    labResults: [
      { date: '2026-04-20', test: 'Sputum AFB smear', result: 'Positive (2+)', flag: 'high' },
      { date: '2026-03-12', test: 'Chest X-ray', result: 'Bilateral infiltrates upper lobe', flag: 'high' },
      { date: '2026-03-12', test: 'Haemoglobin', result: '9.8 g/dL', flag: 'low' },
    ],
  },
  case_02: {
    id: 'case_02', name: 'Sunita Devi', age: 32, gender: 'Female',
    location: 'Village A, Bihar', phone: '98100-22222', bloodGroup: 'O+',
    allergies: 'None known', currentMeds: 'Artesunate + SP regimen',
    visits: [
      { date: '2026-04-25', diagnosis: 'P. falciparum malaria', treatment: 'Artesunate 200mg OD × 3 days + SP', doctor: 'Dr. Sharma', notes: 'RDT positive. Fever 103°F, chills.', status: 'worsening' },
      { date: '2025-11-05', diagnosis: 'Seasonal fever', treatment: 'Paracetamol, hydration', doctor: 'Dr. Sharma', notes: 'Self-resolving viral fever.', status: 'stable' },
    ],
    labResults: [
      { date: '2026-04-25', test: 'Malaria RDT', result: 'Positive — P. falciparum', flag: 'high' },
      { date: '2026-04-25', test: 'Haemoglobin', result: '10.2 g/dL', flag: 'low' },
    ],
  },
  case_03: {
    id: 'case_03', name: 'Amit Singh', age: 28, gender: 'Male',
    location: 'Village B, UP', phone: '98100-33333', bloodGroup: 'A+',
    allergies: 'Sulfa drugs', currentMeds: 'None',
    visits: [
      { date: '2026-04-20', diagnosis: 'Hypertension (Stage 1)', treatment: 'Lifestyle modification advised', doctor: 'Dr. Sharma', notes: 'BP 138/88 — monitor. Return in 1 month.', status: 'stable' },
      { date: '2026-02-10', diagnosis: 'Routine checkup', treatment: 'Nil', doctor: 'Dr. Sharma', notes: 'All parameters normal.', status: 'stable' },
    ],
    labResults: [
      { date: '2026-04-20', test: 'BP Reading', result: '138/88 mmHg', flag: 'high' },
      { date: '2026-04-20', test: 'Random Blood Sugar', result: '92 mg/dL', flag: 'normal' },
    ],
  },
  case_04: {
    id: 'case_04', name: 'Priya Sharma', age: 50, gender: 'Female',
    location: 'Town C, MP', phone: '98100-44444', bloodGroup: 'AB+',
    allergies: 'None known', currentMeds: 'Metformin 500mg BD',
    visits: [
      { date: '2026-04-22', diagnosis: 'Type 2 Diabetes — controlled', treatment: 'Continue Metformin', doctor: 'Dr. Sharma', notes: 'HbA1c 6.9% — within target.', status: 'stable' },
      { date: '2026-01-18', diagnosis: 'Type 2 Diabetes', treatment: 'Metformin 500mg BD started', doctor: 'Dr. Sharma', notes: 'FBS 162, newly diagnosed.', status: 'worsening' },
    ],
    labResults: [
      { date: '2026-04-22', test: 'HbA1c', result: '6.9%', flag: 'normal' },
      { date: '2026-04-22', test: 'Fasting Blood Sugar', result: '118 mg/dL', flag: 'high' },
      { date: '2026-01-18', test: 'Fasting Blood Sugar', result: '162 mg/dL', flag: 'high' },
    ],
  },
  case_05: {
    id: 'case_05', name: 'Mohammad Ali', age: 60, gender: 'Male',
    location: 'Village C, Rajasthan', phone: '98100-55555', bloodGroup: 'O-',
    allergies: 'Aspirin', currentMeds: 'Atenolol 50mg OD',
    visits: [
      { date: '2026-04-23', diagnosis: 'Ischaemic heart disease (suspected)', treatment: 'Refer to cardiologist', doctor: 'Dr. Sharma', notes: 'Exertional chest pain, ST changes on ECG.', status: 'worsening' },
      { date: '2026-03-01', diagnosis: 'Hypertension', treatment: 'Atenolol 50mg', doctor: 'Dr. Sharma', notes: 'BP 158/95 — antihypertensive initiated.', status: 'worsening' },
    ],
    labResults: [
      { date: '2026-04-23', test: 'ECG', result: 'ST depression V4-V6', flag: 'high' },
      { date: '2026-04-23', test: 'BP', result: '162/96 mmHg', flag: 'high' },
    ],
  },
  case_06: {
    id: 'case_06', name: 'Geeta Bai', age: 38, gender: 'Female',
    location: 'Village D, Haryana', phone: '98100-66666', bloodGroup: 'B+',
    allergies: 'None known', currentMeds: 'Iron + Folate daily',
    visits: [
      { date: '2026-04-21', diagnosis: 'Antenatal — 28 weeks', treatment: 'Continue supplements', doctor: 'Dr. Sharma', notes: 'Fundal height appropriate. FHR 144 bpm.', status: 'stable' },
      { date: '2026-03-05', diagnosis: 'Antenatal — 22 weeks', treatment: 'Iron + Folate started', doctor: 'Dr. Sharma', notes: 'Hb 9.4 — mild anaemia, supplemented.', status: 'stable' },
    ],
    labResults: [
      { date: '2026-04-21', test: 'Haemoglobin', result: '10.8 g/dL', flag: 'low' },
      { date: '2026-04-21', test: 'BP', result: '110/70 mmHg', flag: 'normal' },
      { date: '2026-03-05', test: 'Haemoglobin', result: '9.4 g/dL', flag: 'low' },
    ],
  },
};

const STATUS_STYLE = {
  stable:    { bg: 'bg-emerald-100', text: 'text-emerald-700', dot: '#10b981' },
  worsening: { bg: 'bg-amber-100',   text: 'text-amber-700',   dot: '#f59e0b' },
  critical:  { bg: 'bg-red-100',     text: 'text-red-700',     dot: '#ef4444' },
};

const FLAG_STYLE = {
  normal: 'text-emerald-600',
  high:   'text-red-600',
  low:    'text-amber-600',
};

export default function PatientHistoryPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const patient = PATIENT_DB[id];

  if (!patient) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4 text-[#7bbfba]">
        <AlertCircle className="w-10 h-10" />
        <p className="font-medium text-[#3d7a76]">Patient record not found.</p>
        <button onClick={() => router.back()} className="text-sm font-semibold text-[#5aada8] hover:underline">← Go back</button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
      {/* Back */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-sm font-semibold text-[#3d7a76] hover:text-[#0f2b2a] transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Appointments
      </button>

      {/* Patient header card */}
      <div
        className="rounded-2xl p-6 shadow-sm"
        style={{ backgroundColor: 'rgba(90,173,168,0.15)', border: '1px solid rgba(90,173,168,0.3)' }}
      >
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center text-white text-xl font-bold flex-shrink-0"
              style={{ backgroundColor: '#5aada8' }}
            >
              {patient.name[0]}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#0f2b2a]">{patient.name}</h1>
              <p className="text-[#7bbfba] text-sm mt-0.5">{patient.age} yrs · {patient.gender} · {patient.bloodGroup}</p>
            </div>
          </div>
          <div className="flex flex-col gap-1.5 text-sm text-[#3d7a76]">
            <div className="flex items-center gap-2"><Phone className="w-4 h-4 text-[#7bbfba]" />{patient.phone}</div>
            <div className="flex items-center gap-2"><MapPin className="w-4 h-4 text-[#7bbfba]" />{patient.location}</div>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          <div
            className="rounded-xl px-3 py-2"
            style={{ backgroundColor: 'rgba(90,173,168,0.12)', border: '1px solid rgba(90,173,168,0.2)' }}
          >
            <p className="text-[#7bbfba] text-xs mb-0.5">Allergies</p>
            <p className="font-medium text-[#0f2b2a]">{patient.allergies}</p>
          </div>
          <div
            className="rounded-xl px-3 py-2 flex-1"
            style={{ backgroundColor: 'rgba(90,173,168,0.12)', border: '1px solid rgba(90,173,168,0.2)' }}
          >
            <p className="text-[#7bbfba] text-xs mb-0.5 flex items-center gap-1"><Pill className="w-3 h-3" /> Current Medications</p>
            <p className="font-medium text-[#0f2b2a]">{patient.currentMeds}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Visit History */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="font-bold text-[#0f2b2a] flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#5aada8]" /> Visit History
          </h2>
          <div className="relative">
            {/* timeline line */}
            <div className="absolute left-4 top-3 bottom-3 w-px" style={{ backgroundColor: 'rgba(90,173,168,0.3)' }} />
            <div className="space-y-4 pl-10">
              {patient.visits.map((v, i) => {
                const st = STATUS_STYLE[v.status];
                return (
                  <div
                    key={i}
                    className="relative rounded-2xl p-4 shadow-sm"
                    style={{ backgroundColor: 'rgba(90,173,168,0.10)', border: '1px solid rgba(90,173,168,0.22)' }}
                  >
                    {/* dot */}
                    <div
                      className="absolute -left-[1.85rem] top-5 w-3 h-3 rounded-full border-2 border-white"
                      style={{ backgroundColor: st.dot }}
                    />
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <p className="font-bold text-[#0f2b2a] text-sm">{v.diagnosis}</p>
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full flex-shrink-0 ${st.bg} ${st.text}`}>{v.status}</span>
                    </div>
                    <p className="text-xs text-[#7bbfba] mb-2">{v.date} · {v.doctor}</p>
                    <p className="text-sm text-[#3d7a76]"><span className="font-medium text-[#0f2b2a]">Rx:</span> {v.treatment}</p>
                    <p className="text-xs text-[#7bbfba] mt-1 italic">{v.notes}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Lab Results */}
        <div className="space-y-4">
          <h2 className="font-bold text-[#0f2b2a] flex items-center gap-2">
            <Activity className="w-5 h-5 text-[#5aada8]" /> Lab Results
          </h2>
          <div
            className="rounded-2xl overflow-hidden shadow-sm"
            style={{ backgroundColor: 'rgba(90,173,168,0.10)', border: '1px solid rgba(90,173,168,0.28)' }}
          >
            {patient.labResults.map((lr, i) => (
              <div
                key={i}
                className="px-4 py-3 flex items-start justify-between gap-2 text-sm"
                style={{ borderBottom: i < patient.labResults.length - 1 ? '1px solid rgba(90,173,168,0.15)' : 'none' }}
              >
                <div>
                  <p className="font-medium text-[#0f2b2a]">{lr.test}</p>
                  <p className="text-xs text-[#7bbfba] mt-0.5">{lr.date}</p>
                </div>
                <p className={`font-semibold text-sm flex-shrink-0 ${FLAG_STYLE[lr.flag]}`}>{lr.result}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
