import { Bell, Search, User } from 'lucide-react';

export default function TopNav() {
  return (
    <header className="h-16 bg-white border-b border-[#c8e8e5] flex items-center justify-between px-6 sticky top-0 z-10">
      {/* Full-width pill search — matches the mockup */}
      <div className="flex items-center flex-1 mr-6">
        <div className="relative w-full">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#7bbfba]" />
          <input
            type="text"
            placeholder="Search patients, appointments..."
            className="w-full pl-11 pr-5 py-2.5 bg-white border border-[#b8deda] rounded-full
                       text-sm text-[#0f2b2a] placeholder-[#9dbdba]
                       focus:outline-none focus:ring-2 focus:ring-[#5aada8]/30
                       focus:border-[#5aada8] transition-all"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <button className="relative p-2 text-[#7bbfba] hover:text-[#3d8880] transition-colors rounded-full hover:bg-[#e8f6f5]">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-400 rounded-full border-2 border-white" />
        </button>
        <div className="h-6 w-px bg-[#c8e8e5]" />
        <button className="flex items-center gap-2 hover:bg-[#e8f6f5] p-1 pr-3 rounded-full transition-colors">
          <div className="w-8 h-8 rounded-full bg-[#5aada8] flex items-center justify-center text-white">
            <User className="w-4 h-4" />
          </div>
          <span className="text-sm font-medium text-[#0f2b2a]">Dr. Sharma</span>
        </button>
      </div>
    </header>
  );
}
