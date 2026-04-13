'use client';

import { useAppSelector } from '@/store';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { motion } from 'framer-motion';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const sidebarOpen = useAppSelector((s) => s.ui.sidebarOpen);

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <Sidebar />
      <motion.div
        animate={{ marginLeft: sidebarOpen ? 256 : 72 }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className="flex-1 flex flex-col min-w-0"
      >
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </motion.div>
    </div>
  );
}
