'use client';

import { motion } from 'framer-motion';
import { BarChart2 } from 'lucide-react';

export default function AnalyticsPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="card p-16 text-center">
        <div className="w-16 h-16 rounded-2xl bg-brand-50 flex items-center justify-center mx-auto mb-4">
          <BarChart2 className="w-8 h-8 text-brand-400" />
        </div>
        <h2 className="text-base font-semibold text-gray-900 mb-2">Analytics — Coming Soon</h2>
        <p className="text-sm text-gray-500 max-w-sm mx-auto">
          Document verification rates, session completion trends, and SLA compliance dashboards will be available here.
        </p>
      </motion.div>
    </div>
  );
}
