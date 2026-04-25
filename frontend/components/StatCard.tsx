import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: {
    value: string;
    positive: boolean;
  };
  className?: string;
}

export default function StatCard({ title, value, icon: Icon, trend, className = '' }: StatCardProps) {
  return (
    <div
      className={`rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow ${className}`}
      style={{ backgroundColor: 'rgba(90, 173, 168, 0.18)', border: '1px solid rgba(90, 173, 168, 0.28)' }}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-[#3d7a76] mb-1">{title}</p>
          <h3 className="text-3xl font-bold text-[#0f2b2a]">{value}</h3>

          {trend && (
            <p className={`text-sm mt-2 font-medium flex items-center gap-1 ${trend.positive ? 'text-emerald-600' : 'text-red-500'}`}>
              <span>{trend.positive ? '↑' : '↓'}</span>
              {trend.value}
              <span className="text-[#7bbfba] font-normal ml-1">vs last week</span>
            </p>
          )}
        </div>
        <div
          className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: '#5aada8' }}
        >
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
    </div>
  );
}
