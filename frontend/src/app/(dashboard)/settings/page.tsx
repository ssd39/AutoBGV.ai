'use client';

import { motion } from 'framer-motion';
import { Settings, Key, Bell, Shield, Database } from 'lucide-react';
import { CLIENT_ID } from '@/lib/constants';

export default function SettingsPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div className="card p-5">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center">
            <Settings className="w-5 h-5 text-gray-600" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Settings</h1>
            <p className="text-sm text-gray-500">Platform configuration and preferences</p>
          </div>
        </div>
      </div>

      {/* Client Info */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-4 h-4 text-gray-500" />
          <h2 className="text-sm font-semibold text-gray-900">Client Configuration</h2>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <div>
              <p className="text-sm font-medium text-gray-700">Client ID</p>
              <p className="text-xs text-gray-400">Your unique platform identifier</p>
            </div>
            <code className="text-xs bg-gray-100 text-gray-700 px-2.5 py-1 rounded-lg font-mono">
              {CLIENT_ID}
            </code>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <div>
              <p className="text-sm font-medium text-gray-700">Authentication</p>
              <p className="text-xs text-gray-400">Auth mechanism for API access</p>
            </div>
            <span className="badge bg-amber-50 text-amber-700 text-xs">Hardcoded (Dev Mode)</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="text-sm font-medium text-gray-700">Environment</p>
              <p className="text-xs text-gray-400">Current deployment environment</p>
            </div>
            <span className="badge bg-blue-50 text-blue-700 text-xs">Development</span>
          </div>
        </div>
      </motion.div>

      {/* Services */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }} className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-4 h-4 text-gray-500" />
          <h2 className="text-sm font-semibold text-gray-900">Service Endpoints</h2>
        </div>
        <div className="space-y-2">
          {[
            { name: 'Workflow Service',     url: 'http://localhost:8001', status: 'active' },
            { name: 'Agent Service',        url: 'http://localhost:8002', status: 'stub'   },
            { name: 'Verification Service', url: 'http://localhost:8003', status: 'stub'   },
          ].map((svc) => (
            <div key={svc.name} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
              <div>
                <p className="text-sm font-medium text-gray-700">{svc.name}</p>
                <code className="text-xs text-gray-400 font-mono">{svc.url}</code>
              </div>
              <span className={`badge text-xs ${svc.status === 'active' ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                {svc.status}
              </span>
            </div>
          ))}
        </div>
      </motion.div>

      {/* API Keys (coming soon) */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="card p-5">
        <div className="flex items-center gap-2 mb-2">
          <Key className="w-4 h-4 text-gray-500" />
          <h2 className="text-sm font-semibold text-gray-900">API Keys & Integrations</h2>
        </div>
        <p className="text-sm text-gray-500 text-center py-6">
          API key management and third-party integrations (Twilio, WhatsApp, AWS S3) coming soon.
        </p>
      </motion.div>
    </div>
  );
}
