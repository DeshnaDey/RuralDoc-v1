/**
 * lib/api.ts — HTTP client for the RuralDoc backend.
 *
 * All fetch calls go to `/api/*` which next.config.ts proxies to the FastAPI
 * server (NEXT_PUBLIC_API_URL, default http://localhost:7860). This keeps the
 * frontend same-origin and avoids CORS configuration.
 *
 * Functions currently return mock data. Replace the mock block in each
 * function with the commented-out `fetch(...)` call once the backend endpoints
 * are wired up.
 */

// Types
export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: string;
  location: string;
  status: 'stable' | 'worsening' | 'critical';
  time: string;
  reason: string;
}

export interface DashboardStats {
  totalPatientsToday: number;
  criticalCases: number;
  budgetRemaining: number;
  activeScenarios: number;
}

// Mock Data
const MOCK_STATS: DashboardStats = {
  totalPatientsToday: 24,
  criticalCases: 2,
  budgetRemaining: 450,
  activeScenarios: 3,
};

const MOCK_APPOINTMENTS: Patient[] = [
  { id: 'case_01', name: 'Rajesh Kumar', age: 45, gender: 'male', location: 'Urban slum, Delhi', status: 'critical', time: '09:00 AM', reason: 'Chronic cough, suspected TB' },
  { id: 'case_02', name: 'Sunita Devi', age: 32, gender: 'female', location: 'Village A, Bihar', status: 'worsening', time: '09:30 AM', reason: 'High fever, chills' },
  { id: 'case_03', name: 'Amit Singh', age: 28, gender: 'male', location: 'Village B, UP', status: 'stable', time: '10:00 AM', reason: 'Routine checkup' },
  { id: 'case_04', name: 'Priya Sharma', age: 50, gender: 'female', location: 'Town C, MP', status: 'stable', time: '10:30 AM', reason: 'Follow-up' },
];

/**
 * Fetch dashboard statistics.
 * Replace the mock implementation with an actual fetch call when the backend is ready.
 */
export async function fetchDashboardStats(): Promise<DashboardStats> {
  // Simulate network delay
  await new Promise(resolve => setTimeout(resolve, 500));
  
  // Real implementation example:
  // const res = await fetch('/api/stats');
  // if (!res.ok) throw new Error('Failed to fetch stats');
  // return res.json();
  
  return MOCK_STATS;
}

/**
 * Fetch today's appointments.
 * Replace the mock implementation with an actual fetch call when the backend is ready.
 */
export async function fetchAppointments(): Promise<Patient[]> {
  // Simulate network delay
  await new Promise(resolve => setTimeout(resolve, 500));
  
  // Real implementation example:
  // const res = await fetch('/api/appointments');
  // if (!res.ok) throw new Error('Failed to fetch appointments');
  // return res.json();
  
  return MOCK_APPOINTMENTS;
}
