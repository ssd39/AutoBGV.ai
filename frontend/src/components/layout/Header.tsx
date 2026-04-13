'use client';

import { Bell, Search, Plus } from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/workflows': 'Workflows',
  '/workflows/create': 'Create Workflow',
  '/sessions': 'Sessions',
  '/analytics': 'Analytics',
  '/settings': 'Settings',
};

export function Header() {
  const pathname = usePathname();
  const router = useRouter();

  const title = Object.entries(PAGE_TITLES)
    .sort((a, b) => b[0].length - a[0].length)
    .find(([key]) => pathname.startsWith(key))?.[1] || 'AutoBGV';

  const showCreateButton = pathname === '/workflows';

  return (
    <header className="sticky top-0 z-20 bg-white border-b border-gray-200 h-14 flex items-center px-6 gap-4">
      {/* Title */}
      <div className="flex-1">
        <h2 className="text-base font-semibold text-gray-900">{title}</h2>
      </div>

      {/* Search bar */}
      <div className="hidden md:flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-lg px-3 py-1.5 w-64">
        <Search className="w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search workflows..."
          className="bg-transparent text-sm text-gray-600 placeholder-gray-400 outline-none flex-1"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {showCreateButton && (
          <Link
            href="/workflows/create"
            className="btn-primary btn-sm"
          >
            <Plus className="w-4 h-4" />
            New Workflow
          </Link>
        )}

        <button className="relative w-8 h-8 flex items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-brand-500 rounded-full" />
        </button>

        {/* Avatar */}
        <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center">
          <span className="text-xs font-semibold text-brand-700">C</span>
        </div>
      </div>
    </header>
  );
}
