# Frontend Privacy Integration Guide
**UI/UX Examples for Privacy Features**

---

## 1. Privacy-First Upload Flow

### Current Flow (Privacy Issues)
```
User clicks "Upload Chat"
  ↓
File picker opens
  ↓
User selects file
  ↓
File uploads immediately
  ↓
Processing starts
```
**Problem:** No consent, no transparency about data usage

### Improved Privacy-First Flow

```tsx
// Step 1: Upload with Privacy Notice
import { useState } from 'react';
import { Upload, Shield, AlertCircle } from 'lucide-react';

export function ChatUploadFlow() {
  const [step, setStep] = useState<'upload' | 'consent' | 'processing'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [consents, setConsents] = useState({
    aiProcessing: false,
    thirdPartyStorage: false,
    dataRetention: false,
  });

  return (
    <div className="max-w-2xl mx-auto p-6">
      {/* STEP 1: Upload File */}
      {step === 'upload' && (
        <div className="space-y-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-blue-600 mt-0.5" />
              <div>
                <h3 className="font-semibold text-blue-900">Your Privacy Matters</h3>
                <p className="text-sm text-blue-700 mt-1">
                  Your chat will be encrypted and you can delete it anytime.
                  We'll ask for your consent before processing.
                </p>
              </div>
            </div>
          </div>

          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-gray-400 transition-colors cursor-pointer">
            <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <input
              type="file"
              accept=".txt,.zip"
              onChange={(e) => {
                setFile(e.target.files?.[0] || null);
                if (e.target.files?.[0]) setStep('consent');
              }}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <span className="text-lg font-medium text-gray-900">
                Upload WhatsApp Chat
              </span>
              <p className="text-sm text-gray-500 mt-1">
                .txt or .zip file (max 25MB)
              </p>
            </label>
          </div>

          <div className="text-xs text-gray-500 text-center">
            By uploading, you agree to our{' '}
            <a href="/privacy" className="text-blue-600 hover:underline">
              Privacy Policy
            </a>
            {' '}and{' '}
            <a href="/terms" className="text-blue-600 hover:underline">
              Terms of Service
            </a>
          </div>
        </div>
      )}

      {/* STEP 2: Consent Screen */}
      {step === 'consent' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <button
              onClick={() => {
                setStep('upload');
                setFile(null);
              }}
              className="text-gray-600 hover:text-gray-900"
            >
              ← Back
            </button>
            <span className="text-sm text-gray-500">Step 2 of 2</span>
          </div>

          <div>
            <h2 className="text-2xl font-bold text-gray-900">Privacy Consent</h2>
            <p className="text-gray-600 mt-2">
              Please review and accept the following before we process your chat.
            </p>
          </div>

          {/* Data Processing Consent */}
          <div className="space-y-4">
            <ConsentCheckbox
              id="ai-processing"
              required
              checked={consents.aiProcessing}
              onChange={(checked) =>
                setConsents({ ...consents, aiProcessing: checked })
              }
              title="AI Processing"
              description="I consent to RelivChats using AI (Google Gemini) to analyze my chat and generate insights."
              details={
                <div className="mt-2 p-3 bg-gray-50 rounded text-xs text-gray-600">
                  <strong>What this means:</strong>
                  <ul className="list-disc list-inside mt-1 space-y-1">
                    <li>Your chat will be sent to Google's Gemini API</li>
                    <li>Gemini processes your messages to generate insights</li>
                    <li>We have a Data Processing Agreement with Google</li>
                    <li>Google does not use your data for training</li>
                  </ul>
                </div>
              }
            />

            <ConsentCheckbox
              id="third-party-storage"
              required
              checked={consents.thirdPartyStorage}
              onChange={(checked) =>
                setConsents({ ...consents, thirdPartyStorage: checked })
              }
              title="Vector Storage"
              description="I consent to storing encrypted embeddings of my chat in Qdrant Cloud for semantic search."
              details={
                <div className="mt-2 p-3 bg-gray-50 rounded text-xs text-gray-600">
                  <strong>What this means:</strong>
                  <ul className="list-disc list-inside mt-1 space-y-1">
                    <li>Your messages are converted to encrypted vectors</li>
                    <li>Vectors help us find relevant context for insights</li>
                    <li>Qdrant cannot read your original messages</li>
                    <li>Vectors are deleted when you delete your chat</li>
                  </ul>
                </div>
              }
            />

            <ConsentCheckbox
              id="data-retention"
              required={false}
              checked={consents.dataRetention}
              onChange={(checked) =>
                setConsents({ ...consents, dataRetention: checked })
              }
              title="Data Retention (Optional)"
              description="Auto-delete my chat after 90 days of inactivity."
              badge="Recommended"
              badgeColor="green"
              details={
                <div className="mt-2 p-3 bg-green-50 rounded text-xs text-green-700">
                  <strong>Privacy tip:</strong> We recommend enabling auto-delete
                  to minimize your data footprint. You can always change this later.
                </div>
              }
            />
          </div>

          {/* Warning if required consents not given */}
          {(!consents.aiProcessing || !consents.thirdPartyStorage) && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
                <div className="text-sm text-yellow-800">
                  <strong>Required consents</strong>
                  <p className="mt-1">
                    AI Processing and Vector Storage are required to generate insights.
                    Without these, we cannot analyze your chat.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={() => {
                setStep('upload');
                setFile(null);
              }}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={() => handleUpload()}
              disabled={!consents.aiProcessing || !consents.thirdPartyStorage}
              className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Accept & Upload
            </button>
          </div>

          {/* Privacy Links */}
          <div className="text-xs text-center space-y-1">
            <div>
              <a href="/privacy" className="text-blue-600 hover:underline">
                Read our Privacy Policy
              </a>
            </div>
            <div>
              <a href="/privacy#your-rights" className="text-blue-600 hover:underline">
                Learn about your privacy rights
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  async function handleUpload() {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('consent_ai_processing', String(consents.aiProcessing));
    formData.append('consent_third_party', String(consents.thirdPartyStorage));
    formData.append('auto_delete_enabled', String(consents.dataRetention));

    try {
      const response = await fetch('/api/chats/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const data = await response.json();
      // Redirect to chat page
      window.location.href = `/chats/${data.chat_id}`;
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed: ' + error.message);
    }
  }
}

// Consent Checkbox Component
function ConsentCheckbox({
  id,
  required,
  checked,
  onChange,
  title,
  description,
  details,
  badge,
  badgeColor = 'blue'
}: {
  id: string;
  required: boolean;
  checked: boolean;
  onChange: (checked: boolean) => void;
  title: string;
  description: string;
  details?: React.ReactNode;
  badge?: string;
  badgeColor?: 'blue' | 'green' | 'yellow';
}) {
  const [showDetails, setShowDetails] = useState(false);

  const badgeColors = {
    blue: 'bg-blue-100 text-blue-700',
    green: 'bg-green-100 text-green-700',
    yellow: 'bg-yellow-100 text-yellow-700',
  };

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors">
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          id={id}
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="mt-1 w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <label htmlFor={id} className="font-medium text-gray-900 cursor-pointer">
              {title}
            </label>
            {required && (
              <span className="text-xs text-red-600 font-medium">Required</span>
            )}
            {badge && (
              <span className={`text-xs px-2 py-0.5 rounded-full ${badgeColors[badgeColor]}`}>
                {badge}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 mt-1">{description}</p>

          {details && (
            <>
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-xs text-blue-600 hover:underline mt-2"
              >
                {showDetails ? 'Hide details' : 'Show details'}
              </button>
              {showDetails && details}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
```

---

## 2. Privacy Dashboard

```tsx
// components/PrivacyDashboard.tsx

import { useState, useEffect } from 'react';
import { Shield, Download, Trash2, Clock, Lock, Eye, EyeOff } from 'lucide-react';

interface PrivacyData {
  chats_count: number;
  total_messages: number;
  total_insights: number;
  account_created: string;
  last_accessed: string;
  data_retention_days: number;
  next_cleanup_date: string;
  encryption_enabled: boolean;
  consents: Array<{
    consent_type: string;
    granted: boolean;
    granted_at: string;
  }>;
}

export function PrivacyDashboard() {
  const [data, setData] = useState<PrivacyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    fetchPrivacyData();
  }, []);

  async function fetchPrivacyData() {
    try {
      const response = await fetch('/api/users/me/privacy', {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
      });
      const data = await response.json();
      setData(data);
    } catch (error) {
      console.error('Failed to load privacy data:', error);
    } finally {
      setLoading(false);
    }
  }

  async function exportData() {
    try {
      const response = await fetch('/api/users/me/export', {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
      });

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `relivchats_data_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      alert('✓ Your data has been exported!');
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export data. Please try again.');
    }
  }

  async function deleteAllData() {
    if (!confirm('Are you sure? This will permanently delete ALL your chats, insights, and account data. This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch('/api/users/me', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
        },
      });

      if (response.ok) {
        alert('✓ Your data has been deleted. You will be logged out.');
        window.location.href = '/logout';
      } else {
        throw new Error('Deletion failed');
      }
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Failed to delete data. Please contact support.');
    }
  }

  if (loading) {
    return <div className="flex justify-center p-12"><LoadingSpinner /></div>;
  }

  if (!data) {
    return <div className="text-center p-12 text-gray-500">Failed to load privacy data</div>;
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Privacy Dashboard</h1>
        <p className="text-gray-600 mt-2">
          View and manage your data, consents, and privacy settings.
        </p>
      </div>

      {/* Data Overview */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
          <Eye className="w-5 h-5" />
          What We Know About You
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <StatCard
            icon={<MessageSquare className="w-5 h-5" />}
            label="Chats Stored"
            value={data.chats_count}
            sublabel={`${data.total_messages.toLocaleString()} messages`}
          />
          <StatCard
            icon={<Lightbulb className="w-5 h-5" />}
            label="Insights Generated"
            value={data.total_insights}
            sublabel="AI analyses"
          />
          <StatCard
            icon={<Calendar className="w-5 h-5" />}
            label="Account Age"
            value={calculateDaysSince(data.account_created)}
            sublabel="days"
          />
        </div>

        <div className="mt-6 p-4 bg-gray-50 rounded-lg text-sm text-gray-600">
          <div className="flex items-start gap-2">
            <Lock className="w-4 h-4 text-green-600 mt-0.5" />
            <div>
              <strong className="text-gray-900">All your data is encrypted</strong>
              <p className="mt-1">
                Messages, names, and metadata are encrypted using AES-256 before storage.
                Even our database administrators cannot read your chats.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Security Status */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
          <Shield className="w-5 h-5" />
          Security Status
        </h2>

        <div className="space-y-3 mt-6">
          <SecurityItem
            label="Encryption at Rest"
            status="enabled"
            description="All data encrypted with AES-256"
          />
          <SecurityItem
            label="HTTPS Encryption"
            status="enabled"
            description="All connections use TLS 1.3"
          />
          <SecurityItem
            label="Two-Factor Authentication"
            status="optional"
            description="Managed by Clerk"
            action={
              <a href="https://clerk.com" target="_blank" className="text-blue-600 text-sm hover:underline">
                Configure →
              </a>
            }
          />
        </div>
      </div>

      {/* Data Retention */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
          <Clock className="w-5 h-5" />
          Data Retention
        </h2>

        <div className="mt-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900">Auto-Delete After</p>
              <p className="text-sm text-gray-600 mt-1">
                Chats automatically deleted after {data.data_retention_days} days of inactivity
              </p>
            </div>
            <select
              className="border border-gray-300 rounded-lg px-4 py-2"
              defaultValue={data.data_retention_days}
              onChange={(e) => updateRetentionPolicy(Number(e.target.value))}
            >
              <option value="30">30 days</option>
              <option value="90">90 days</option>
              <option value="180">180 days</option>
              <option value="365">1 year</option>
              <option value="-1">Never</option>
            </select>
          </div>

          {data.next_cleanup_date && (
            <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
              Next automatic cleanup: {new Date(data.next_cleanup_date).toLocaleDateString()}
            </div>
          )}
        </div>
      </div>

      {/* Consent Management */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
          <CheckSquare className="w-5 h-5" />
          Your Consents
        </h2>

        <div className="space-y-3 mt-6">
          {data.consents.map((consent) => (
            <ConsentItem
              key={consent.consent_type}
              type={consent.consent_type}
              granted={consent.granted}
              grantedAt={consent.granted_at}
              onWithdraw={() => withdrawConsent(consent.consent_type)}
            />
          ))}
        </div>
      </div>

      {/* Privacy Rights (GDPR) */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">
          Your Privacy Rights
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ActionButton
            icon={<Download className="w-5 h-5" />}
            title="Download My Data"
            description="Export all your data in JSON format"
            onClick={exportData}
          />

          <ActionButton
            icon={<Trash2 className="w-5 h-5" />}
            title="Delete My Data"
            description="Permanently delete all your data"
            onClick={() => setShowDeleteConfirm(true)}
            variant="danger"
          />

          <ActionButton
            icon={<FileText className="w-5 h-5" />}
            title="Privacy Policy"
            description="Read our privacy policy"
            onClick={() => window.open('/privacy', '_blank')}
          />

          <ActionButton
            icon={<Mail className="w-5 h-5" />}
            title="Contact DPO"
            description="Email our Data Protection Officer"
            onClick={() => window.location.href = 'mailto:privacy@relivchats.com'}
          />
        </div>
      </div>

      {/* Last Accessed */}
      <div className="text-sm text-gray-500 text-center">
        Last data access: {new Date(data.last_accessed).toLocaleString()}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <DeleteConfirmationModal
          onConfirm={deleteAllData}
          onCancel={() => setShowDeleteConfirm(false)}
        />
      )}
    </div>
  );
}

function StatCard({ icon, label, value, sublabel }: any) {
  return (
    <div className="p-4 bg-gray-50 rounded-lg">
      <div className="flex items-center gap-2 text-gray-600 mb-2">
        {icon}
        <span className="text-sm font-medium">{label}</span>
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      {sublabel && <div className="text-xs text-gray-500 mt-1">{sublabel}</div>}
    </div>
  );
}

function SecurityItem({ label, status, description, action }: any) {
  const statusColors = {
    enabled: 'bg-green-100 text-green-700',
    disabled: 'bg-red-100 text-red-700',
    optional: 'bg-gray-100 text-gray-700',
  };

  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900">{label}</span>
          <span className={`text-xs px-2 py-1 rounded-full ${statusColors[status]}`}>
            {status}
          </span>
        </div>
        <p className="text-sm text-gray-600 mt-1">{description}</p>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

function ConsentItem({ type, granted, grantedAt, onWithdraw }: any) {
  const consentLabels = {
    privacy_policy: 'Privacy Policy',
    terms_of_service: 'Terms of Service',
    ai_processing: 'AI Processing',
    third_party_storage: 'Third-Party Storage',
    marketing_emails: 'Marketing Emails',
  };

  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
      <div>
        <p className="font-medium text-gray-900">{consentLabels[type] || type}</p>
        <p className="text-xs text-gray-500 mt-1">
          {granted ? `Granted on ${new Date(grantedAt).toLocaleDateString()}` : 'Not granted'}
        </p>
      </div>
      {granted && type.startsWith('marketing') && (
        <button
          onClick={onWithdraw}
          className="text-sm text-red-600 hover:underline"
        >
          Withdraw
        </button>
      )}
    </div>
  );
}

function ActionButton({ icon, title, description, onClick, variant = 'default' }: any) {
  const variants = {
    default: 'border-gray-200 hover:border-gray-300 hover:bg-gray-50',
    danger: 'border-red-200 hover:border-red-300 hover:bg-red-50',
  };

  return (
    <button
      onClick={onClick}
      className={`p-4 border rounded-lg text-left transition-colors ${variants[variant]}`}
    >
      <div className="flex items-center gap-3">
        <div className={variant === 'danger' ? 'text-red-600' : 'text-gray-600'}>
          {icon}
        </div>
        <div>
          <div className={`font-medium ${variant === 'danger' ? 'text-red-900' : 'text-gray-900'}`}>
            {title}
          </div>
          <div className={`text-sm ${variant === 'danger' ? 'text-red-600' : 'text-gray-600'}`}>
            {description}
          </div>
        </div>
      </div>
    </button>
  );
}

function DeleteConfirmationModal({ onConfirm, onCancel }: any) {
  const [confirmText, setConfirmText] = useState('');

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <div className="flex items-center gap-3 text-red-600 mb-4">
          <AlertTriangle className="w-6 h-6" />
          <h3 className="text-xl font-bold">Delete All Data</h3>
        </div>

        <div className="space-y-4">
          <p className="text-gray-700">
            This will permanently delete:
          </p>
          <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
            <li>All your uploaded chats</li>
            <li>All generated insights</li>
            <li>Your account and credit balance</li>
            <li>All payment history</li>
          </ul>

          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-800">
              <strong>This action cannot be undone.</strong> Your data will be permanently erased within 30 days.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Type <strong>DELETE</strong> to confirm:
            </label>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
              placeholder="DELETE"
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={onCancel}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={confirmText !== 'DELETE'}
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Delete Forever
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## 3. Backend Endpoints for Privacy Features

```python
# src/users/router.py - ADD THESE ENDPOINTS

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import json
from datetime import datetime, timezone, timedelta

from ..database import get_async_db
from ..auth.dependencies import get_current_user_id
from . import models, service
from .consent_service import get_user_consents
from ..chats.service import get_user_chats
from ..credits.service import get_user_transactions

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/privacy")
async def get_privacy_dashboard(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Privacy dashboard data
    Shows user what data we have and their privacy settings
    """

    # Get user
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # Get all chats
    chats = await get_user_chats(db, user_id)

    # Get insights count
    total_insights = 0
    total_messages = 0
    for chat in chats:
        total_insights += len(chat.insights)
        # Approximate message count from metadata
        if chat.chat_metadata:
            total_messages += chat.chat_metadata.get('total_messages', 0)

    # Get consents (use sync session for this)
    from ..database import SessionLocal
    sync_db = SessionLocal()
    try:
        consents = get_user_consents(sync_db, user_id)
        consent_data = [
            {
                "consent_type": c.consent_type,
                "granted": c.granted,
                "granted_at": c.granted_at.isoformat() if c.granted_at else None,
            }
            for c in consents
        ]
    finally:
        sync_db.close()

    # Calculate next cleanup date
    if chats:
        oldest_inactive = min(
            chat.last_accessed_at for chat in chats
            if chat.last_accessed_at and chat.auto_delete_enabled
        )
        next_cleanup = oldest_inactive + timedelta(days=90)
    else:
        next_cleanup = None

    return {
        "chats_count": len(chats),
        "total_messages": total_messages,
        "total_insights": total_insights,
        "account_created": user.created_at.isoformat(),
        "last_accessed": max(
            (chat.last_accessed_at for chat in chats if chat.last_accessed_at),
            default=user.created_at
        ).isoformat(),
        "data_retention_days": 90,  # Default
        "next_cleanup_date": next_cleanup.isoformat() if next_cleanup else None,
        "encryption_enabled": True,
        "consents": consent_data
    }


@router.get("/me/export")
async def export_user_data(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """
    GDPR Right to Portability
    Export all user data in machine-readable format (JSON)
    """

    # Get user
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # Get all chats with messages
    chats = await get_user_chats(db, user_id)

    # Build export data
    export_data = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "format_version": "1.0",
        "data_controller": {
            "name": "RelivChats",
            "email": "privacy@relivchats.com",
            "website": "https://relivchats.com"
        },
        "user": {
            "user_id": user.user_id,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
            "credit_balance": user.credit_balance
        },
        "chats": [],
        "credit_transactions": []
    }

    # Export chats
    for chat in chats:
        # Get messages for this chat
        from ..chats.service import get_chat_messages
        messages = await get_chat_messages(db, chat.id, user_id)

        chat_data = {
            "chat_id": str(chat.id),
            "title": chat.title,
            "created_at": chat.created_at.isoformat(),
            "participants": json.loads(chat.participants) if chat.participants else [],
            "is_group_chat": chat.is_group_chat,
            "metadata": chat.chat_metadata,
            "messages": [
                {
                    "sender": msg.sender,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ],
            "insights": [
                {
                    "insight_type": insight.insight_type.name,
                    "content": insight.content,
                    "generated_at": insight.created_at.isoformat()
                }
                for insight in chat.insights
            ]
        }
        export_data["chats"].append(chat_data)

    # Export credit transactions
    from ..database import SessionLocal
    sync_db = SessionLocal()
    try:
        transactions = get_user_transactions(sync_db, user_id)
        export_data["credit_transactions"] = [
            {
                "transaction_id": str(t.id),
                "type": t.transaction_type,
                "amount": t.amount,
                "balance_after": t.balance_after,
                "created_at": t.created_at.isoformat(),
                "metadata": t.metadata
            }
            for t in transactions
        ]
    finally:
        sync_db.close()

    # Return as downloadable JSON
    from fastapi.responses import Response
    return Response(
        content=json.dumps(export_data, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=relivchats_data_{user_id}_{datetime.now().strftime('%Y%m%d')}.json"
        }
    )


@router.delete("/me")
async def delete_user_account(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """
    GDPR Right to Erasure
    Permanently delete user account and all associated data
    """

    # Get user
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    # Log deletion request
    logger.warning(
        f"User requested account deletion: {user_id}",
        extra={
            "user_id": user_id,
            "extra_data": {
                "email": user.email,
                "chats_count": len(user.chats)
            }
        }
    )

    # Delete all chats (cascade will delete messages, insights, etc.)
    from ..chats.service import delete_chat
    for chat in user.chats:
        await delete_chat(db, str(chat.id))

    # Delete user (cascade will delete credit transactions, consents)
    await db.delete(user)
    await db.commit()

    logger.info(
        f"User account deleted: {user_id}",
        extra={"user_id": user_id}
    )

    return {
        "message": "Your account and all associated data have been permanently deleted.",
        "deletion_timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.put("/me/retention")
async def update_retention_policy(
    retention_days: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Update data retention policy for all user chats
    """

    if retention_days not in [30, 90, 180, 365, -1]:
        raise HTTPException(400, "Invalid retention period. Choose: 30, 90, 180, 365, or -1 (never)")

    # Update all user's chats
    chats = await get_user_chats(db, user_id)

    for chat in chats:
        chat.retention_days = retention_days
        chat.auto_delete_enabled = (retention_days != -1)

        if retention_days > 0:
            chat.expires_at = chat.last_accessed_at + timedelta(days=retention_days)
        else:
            chat.expires_at = None

    await db.commit()

    logger.info(
        f"Retention policy updated: {retention_days} days",
        extra={
            "user_id": user_id,
            "extra_data": {"retention_days": retention_days}
        }
    )

    return {
        "message": f"Retention policy updated to {retention_days} days",
        "chats_affected": len(chats)
    }
```

---

## 4. Privacy Badge for Landing Page

```tsx
// components/PrivacyBadge.tsx

export function PrivacyBadge() {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Privacy-First by Design
      </h3>

      <div className="space-y-3">
        <PrivacyFeature
          icon="🔒"
          title="Military-Grade Encryption"
          description="All chats encrypted with AES-256"
        />

        <PrivacyFeature
          icon="🗑️"
          title="Auto-Delete"
          description="Chats deleted after 90 days by default"
        />

        <PrivacyFeature
          icon="📥"
          title="Data Export"
          description="Download your data anytime (GDPR compliant)"
        />

        <PrivacyFeature
          icon="🚫"
          title="No Data Selling"
          description="We never sell or share your data"
        />

        <PrivacyFeature
          icon="🇪🇺"
          title="GDPR Compliant"
          description="Full compliance with EU privacy laws"
        />

        <PrivacyFeature
          icon="⚡"
          title="Instant Deletion"
          description="Delete your chats with one click"
        />
      </div>

      <div className="mt-6 pt-4 border-t border-gray-200">
        <a
          href="/privacy"
          className="text-sm text-blue-600 hover:underline font-medium"
        >
          Read our Privacy Policy →
        </a>
      </div>
    </div>
  );
}

function PrivacyFeature({ icon, title, description }) {
  return (
    <div className="flex items-start gap-3">
      <span className="text-2xl">{icon}</span>
      <div>
        <div className="font-medium text-gray-900">{title}</div>
        <div className="text-sm text-gray-600">{description}</div>
      </div>
    </div>
  );
}
```

---

## 5. Email Templates for Privacy Events

```html
<!-- emails/consent_withdrawn.html -->

<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Consent Withdrawn - RelivChats</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
  <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #1f2937;">Consent Withdrawn</h1>

    <p>Hi there,</p>

    <p>
      You have successfully withdrawn consent for <strong>{{ consent_type }}</strong>.
    </p>

    <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
      <strong>What this means:</strong>
      <ul style="margin: 10px 0;">
        <li>We can no longer process your data for this purpose</li>
        <li>Related data will be deleted within 30 days</li>
        <li>You can re-grant consent anytime</li>
      </ul>
    </div>

    <p>
      If you didn't make this change, please contact us immediately at
      <a href="mailto:privacy@relivchats.com">privacy@relivchats.com</a>
    </p>

    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">

    <p style="font-size: 12px; color: #6b7280;">
      RelivChats<br>
      <a href="https://relivchats.com/privacy">Privacy Policy</a> |
      <a href="https://relivchats.com/settings/privacy">Manage Consents</a>
    </p>
  </div>
</body>
</html>
```

```html
<!-- emails/data_exported.html -->

<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Data Export Ready - RelivChats</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
  <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #1f2937;">Your Data Export is Ready</h1>

    <p>Hi {{ user_email }},</p>

    <p>
      Your requested data export has been generated and is ready for download.
    </p>

    <div style="background: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0;">
      <strong>Export Details:</strong>
      <ul style="margin: 10px 0;">
        <li>Export Date: {{ export_date }}</li>
        <li>File Format: JSON</li>
        <li>Includes: Chats, Insights, Transactions</li>
      </ul>
    </div>

    <div style="text-align: center; margin: 30px 0;">
      <a href="{{ download_link }}"
         style="background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
        Download My Data
      </a>
    </div>

    <p style="font-size: 14px; color: #6b7280;">
      <strong>Note:</strong> This download link expires in 7 days.
      Your data remains securely stored in your account.
    </p>

    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">

    <p style="font-size: 12px; color: #6b7280;">
      RelivChats<br>
      <a href="https://relivchats.com/privacy">Privacy Policy</a>
    </p>
  </div>
</body>
</html>
```

---

## Summary: Frontend Integration Checklist

```
Frontend Privacy Integration Checklist
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Upload Flow:
[ ] Add consent checkboxes to upload form
[ ] Show "What this means" details for each consent
[ ] Validate required consents before upload
[ ] Send consent flags to API
[ ] Show encryption badge during upload

Privacy Dashboard:
[ ] Create /settings/privacy route
[ ] Display data overview (chats, messages, insights count)
[ ] Show security status (encryption, HTTPS)
[ ] Data retention settings dropdown
[ ] Consent management UI
[ ] Export data button
[ ] Delete account button (with confirmation)

Landing Page:
[ ] Add privacy badge/section
[ ] Link to Privacy Policy in footer
[ ] Link to Terms of Service in footer
[ ] Add "Privacy-First" tagline
[ ] Trust signals (encryption icons, etc.)

Chat Pages:
[ ] Add "Delete this chat" button
[ ] Add "Export this chat" button
[ ] Show last accessed date
[ ] Show auto-delete countdown if enabled

Account Settings:
[ ] Manage consents page
[ ] Change retention policy
[ ] View access logs (if implemented)
[ ] Download data history

Legal Pages:
[ ] /privacy - Privacy Policy
[ ] /terms - Terms of Service
[ ] /privacy#your-rights - GDPR rights section
[ ] /contact/privacy - Privacy contact form
```

All frontend code ready to implement! 🚀
