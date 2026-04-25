"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Users, Calendar, Package, Settings } from 'lucide-react';

const NAV_ITEMS = [
  { name: 'Dashboard',    href: '/',             icon: LayoutDashboard },
  { name: 'Patients',     href: '/patients',     icon: Users           },
  { name: 'Appointments', href: '/appointments', icon: Calendar        },
  { name: 'Inventory',    href: '/inventory',    icon: Package         },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 hidden md:flex flex-col" style={{ backgroundColor: '#5aada8' }}>
      {/* Brand */}
      <div className="h-16 flex items-center px-6">
        <div className="flex items-center gap-2.5 text-white">
          {/* Three-petal clover mark matching the mockup */}
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22V12"/>
            <path d="M12 12C12 9 10 7 7 7C4 7 2 9 2 12C2 15 4 17 7 17C9.5 17 11.5 15.5 12 12Z"/>
            <path d="M12 12C12 9 14 7 17 7C20 7 22 9 22 12C22 15 20 17 17 17C14.5 17 12.5 15.5 12 12Z"/>
            <path d="M12 12C9 12 7 10 7 7C7 4 9 2 12 2C15 2 17 4 17 7C17 9.5 15.5 11.5 12 12Z"/>
          </svg>
          <span className="text-xl font-bold tracking-tight">RuralDoc</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors text-white ${
                isActive
                  ? 'bg-white/25 font-semibold'
                  : 'opacity-75 hover:opacity-100 hover:bg-white/15'
              }`}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* White pill button at bottom — matches the mockup */}
      <div className="p-5">
        <Link
          href="/settings"
          className="flex items-center gap-3 px-5 py-2.5 bg-white rounded-full
                     text-[#3d8880] font-semibold text-sm
                     hover:bg-white/90 transition-colors shadow-sm"
        >
          <Settings className="w-4 h-4" />
          Settings
        </Link>
      </div>
    </aside>
  );
}
