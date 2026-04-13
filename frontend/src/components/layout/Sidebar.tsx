'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard, GitBranch, Play, BarChart2, Settings,
  ChevronLeft, ChevronRight, Shield, Zap,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store';
import { toggleSidebar } from '@/store/uiSlice';
import { CLIENT_ID } from '@/lib/constants';
import clsx from 'clsx';

const navItems = [
  { href: '/',          label: 'Dashboard',  Icon: LayoutDashboard },
  { href: '/workflows', label: 'Workflows',  Icon: GitBranch       },
  { href: '/sessions',  label: 'Sessions',   Icon: Play            },
  { href: '/analytics', label: 'Analytics',  Icon: BarChart2       },
  { href: '/settings',  label: 'Settings',   Icon: Settings        },
];

export function Sidebar() {
  const pathname = usePathname();
  const dispatch = useAppDispatch();
  const sidebarOpen = useAppSelector((s) => s.ui.sidebarOpen);

  return (
    <motion.aside
      animate={{ width: sidebarOpen ? 256 : 72 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
      className="fixed left-0 top-0 h-screen bg-white border-r border-gray-200 flex flex-col z-30 overflow-hidden"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-gray-100">
        <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center flex-shrink-0">
          <Shield className="w-4 h-4 text-white" />
        </div>
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.15 }}
              className="overflow-hidden"
            >
              <p className="font-bold text-gray-900 text-sm leading-tight">AutoBGV</p>
              <p className="text-xs text-gray-500 truncate">Doc Verification Platform</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map(({ href, label, Icon }) => {
          const isActive = href === '/' ? pathname === '/' : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'sidebar-link',
                isActive && 'active'
              )}
              title={!sidebarOpen ? label : undefined}
            >
              <Icon className={clsx('w-5 h-5 flex-shrink-0', isActive ? 'text-brand-600' : 'text-gray-500')} />
              <AnimatePresence>
                {sidebarOpen && (
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.1 }}
                    className="truncate"
                  >
                    {label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          );
        })}
      </nav>

      {/* Client Info */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="px-4 py-3 border-t border-gray-100"
          >
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-brand-100 flex items-center justify-center">
                <Zap className="w-3.5 h-3.5 text-brand-600" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-gray-900 truncate">{CLIENT_ID}</p>
                <p className="text-xs text-gray-400">Development Mode</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toggle button */}
      <button
        onClick={() => dispatch(toggleSidebar())}
        className="flex items-center justify-center h-10 w-full border-t border-gray-100 text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors"
      >
        {sidebarOpen ? (
          <ChevronLeft className="w-4 h-4" />
        ) : (
          <ChevronRight className="w-4 h-4" />
        )}
      </button>
    </motion.aside>
  );
}
