'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  GitBranch, Play, CheckCircle, Clock, TrendingUp,
  ArrowRight, Plus, Zap,
} from 'lucide-react';
import Link from 'next/link';
import { workflowApi } from '@/lib/api';

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3 },
};

const quickActions = [
  {
    title: 'Create New Workflow',
    description: 'Build a custom document verification workflow from scratch',
    href: '/workflows/create',
    icon: Plus,
    color: 'bg-brand-600',
  },
  {
    title: 'Browse Templates',
    description: 'Start with a pre-built KYC, loan, or insurance workflow',
    href: '/workflows/create?tab=templates',
    icon: Zap,
    color: 'bg-purple-600',
  },
  {
    title: 'View All Workflows',
    description: 'Manage and monitor your existing verification workflows',
    href: '/workflows',
    icon: GitBranch,
    color: 'bg-green-600',
  },
];

export default function DashboardPage() {
  const [totalWorkflows, setTotalWorkflows] = useState<number | null>(null);
  const [totalSessions, setTotalSessions] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        // Fetch all workflows (small page size — we only need totals)
        const data = await workflowApi.list({ page: 1, page_size: 100 });
        setTotalWorkflows(data.total);

        // Sum session counts across all loaded workflows
        const sessionSum = data.items.reduce(
          (acc, wf) => acc + (wf.session_count ?? 0),
          0
        );
        setTotalSessions(sessionSum);
      } catch {
        // If API is unreachable keep null so we show '—'
        setTotalWorkflows(null);
        setTotalSessions(null);
      } finally {
        setLoading(false);
      }
    }

    fetchStats();
  }, []);

  const fmt = (v: number | null) => (loading ? '…' : v === null ? '—' : String(v));

  const stats = [
    { label: 'Total Workflows', value: fmt(totalWorkflows), icon: GitBranch, color: 'text-blue-600',   bg: 'bg-blue-50'   },
    { label: 'Active Sessions', value: fmt(totalSessions),  icon: Play,      color: 'text-green-600',  bg: 'bg-green-50'  },
    { label: 'Docs Verified',   value: '—',                 icon: CheckCircle, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Avg. Completion', value: 'N/A',               icon: Clock,     color: 'text-orange-600', bg: 'bg-orange-50' },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Welcome Banner */}
      <motion.div {...fadeUp} className="bg-gradient-to-r from-brand-600 to-brand-800 rounded-2xl p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-1">Welcome to AutoBGV</h1>
            <p className="text-brand-200 text-sm">
              AI-powered document verification, KYC &amp; background check platform
            </p>
          </div>
          <Link
            href="/workflows/create"
            className="hidden sm:flex items-center gap-2 bg-white text-brand-700 font-semibold text-sm px-4 py-2 rounded-lg hover:bg-brand-50 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Workflow
          </Link>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="bg-white/10 backdrop-blur-sm rounded-xl p-3"
            >
              <div className="flex items-center gap-2 mb-1">
                <stat.icon className="w-4 h-4 text-brand-200" />
                <span className="text-xs text-brand-200">{stat.label}</span>
              </div>
              <p className="text-2xl font-bold">{stat.value}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.3 }}
      >
        <h2 className="text-base font-semibold text-gray-900 mb-3">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {quickActions.map((action, i) => (
            <motion.div
              key={action.title}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.08 }}
            >
              <Link href={action.href} className="card-hover block p-5">
                <div className={`w-10 h-10 rounded-xl ${action.color} flex items-center justify-center mb-3`}>
                  <action.icon className="w-5 h-5 text-white" />
                </div>
                <h3 className="font-semibold text-gray-900 text-sm mb-1">{action.title}</h3>
                <p className="text-xs text-gray-500 leading-relaxed">{action.description}</p>
                <div className="flex items-center gap-1 mt-3 text-xs text-brand-600 font-medium">
                  Get started <ArrowRight className="w-3 h-3" />
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* What you can build */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.3 }}
      >
        <h2 className="text-base font-semibold text-gray-900 mb-3">Supported Workflow Types</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { label: 'KYC',               icon: '🪪', desc: 'Individual identity' },
            { label: 'Loan',              icon: '🏦', desc: 'Loan applications'   },
            { label: 'Insurance',         icon: '🛡️', desc: 'Claims & policies'   },
            { label: 'Background Check',  icon: '🔍', desc: 'Employment BGV'      },
            { label: 'Property',          icon: '🏠', desc: 'Property docs'       },
            { label: 'Business',          icon: '🏢', desc: 'MSME & enterprise'   },
          ].map((item, i) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.25 + i * 0.05 }}
              className="card p-4 text-center"
            >
              <div className="text-2xl mb-2">{item.icon}</div>
              <p className="text-xs font-semibold text-gray-800">{item.label}</p>
              <p className="text-xs text-gray-400 mt-0.5">{item.desc}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* How it works */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.3 }}
        className="card p-6"
      >
        <h2 className="text-base font-semibold text-gray-900 mb-4">How it works</h2>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {[
            { step: '1', title: 'Create Workflow',     desc: 'Define documents & questions for verification',      icon: '⚙️' },
            { step: '2', title: 'Initiate Session',    desc: 'Start a session for your customer with one click',   icon: '🚀' },
            { step: '3', title: 'AI Calls Customer',   desc: 'Voice AI calls and guides customer via WhatsApp',    icon: '🤖' },
            { step: '4', title: 'Verify & Report',     desc: 'Documents are verified and results shared with you', icon: '✅' },
          ].map((item, i) => (
            <div key={item.step} className="relative">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-brand-50 border-2 border-brand-200 flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-bold text-brand-700">{item.step}</span>
                </div>
                <div>
                  <p className="text-xl mb-1">{item.icon}</p>
                  <p className="text-sm font-semibold text-gray-900">{item.title}</p>
                  <p className="text-xs text-gray-500 mt-1 leading-relaxed">{item.desc}</p>
                </div>
              </div>
              {i < 3 && (
                <div className="hidden sm:block absolute top-4 left-full w-full border-t-2 border-dashed border-gray-200 -translate-x-4" />
              )}
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
