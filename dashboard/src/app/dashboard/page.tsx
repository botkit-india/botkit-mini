'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useGoogleLogin } from '@react-oauth/google';
import { getMyBots, crawlWebsite, getBotStatus, uploadPDF, login, googleAuth } from '@/lib/api';
import { getToken, getUser, logout, clearAuth, setToken, setUser as persistUser } from '@/lib/auth';

interface Bot {
  bot_id: string;
  url: string;
  pages_crawled: number;
  status: string;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [bots, setBots] = useState<Bot[]>([]);
  const [url, setUrl] = useState('');
  const [creating, setCreating] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState<'info' | 'error'>('info');
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [uploadingBot, setUploadingBot] = useState<string | null>(null);
  const [uploadMsg, setUploadMsg] = useState('');
  const [uploadError, setUploadError] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  useEffect(() => {
    const storedUser = getUser();
    const token = getToken();
    setUser(storedUser);

    if (!token) {
      setLoading(false);
      return;
    }

    fetchBots();
  }, []);

  async function fetchBots() {
    try {
      const res = await getMyBots();
      setBots(res.data.bots);
    } catch {
      clearAuth();
      setUser(null);
      setBots([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleDashboardLogin(e: React.FormEvent) {
    e.preventDefault();
    setAuthError('');
    setAuthLoading(true);

    try {
      const res = await login(email, password);
      setToken(res.data.token);
      persistUser(res.data.user);
      setUser(res.data.user);
      setEmail('');
      setPassword('');
      await fetchBots();
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || 'Login failed.');
      setLoading(false);
    } finally {
      setAuthLoading(false);
    }
  }

  const handleGoogleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      setGoogleLoading(true);
      setAuthError('');
      try {
        const res = await googleAuth(tokenResponse.access_token);
        setToken(res.data.token);
        persistUser(res.data.user);
        setUser(res.data.user);
        await fetchBots();
      } catch (err: any) {
        setAuthError(err.response?.data?.detail || 'Google login failed.');
        setLoading(false);
      } finally {
        setGoogleLoading(false);
      }
    },
    onError: () => {
      setAuthError('Google login failed. Please try again.');
    }
  });

  async function handleCreateBot(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setCreating(true);
    setStatusMsg('Starting crawl...');
    setStatusType('info');

    try {
      const res = await crawlWebsite(url);
      const botId = res.data.bot_id;
      setStatusMsg('Crawling your website...');

      const interval = setInterval(async () => {
        const s = await getBotStatus(botId);
        const data = s.data;
        setStatusMsg(`Crawling... ${data.pages_crawled} pages found`);

        if (data.status === 'ready') {
          clearInterval(interval);
          setStatusMsg('');
          setUrl('');
          setCreating(false);
          setShowModal(false);
          fetchBots();
        } else if (data.status === 'error') {
          clearInterval(interval);
          setStatusMsg('Error: ' + data.error);
          setStatusType('error');
          setCreating(false);
        }
      }, 2000);

    } catch (err: any) {
      setStatusMsg('Failed: ' + (err.response?.data?.detail || 'Unknown error'));
      setStatusType('error');
      setCreating(false);
    }
  }

  async function handlePDFUpload(botId: string, file: File) {
    setUploadingBot(botId);
    setUploadMsg('Uploading and processing PDF...');
    setUploadError('');

    try {
      const res = await uploadPDF(botId, file);
      setUploadMsg(`✅ ${res.data.filename} added — ${res.data.pages_extracted} pages learned`);
      setTimeout(() => {
        setUploadMsg('');
        setUploadingBot(null);
      }, 3000);
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Upload failed.');
      setUploadingBot(null);
    }
  }

  function copyWidget(botId: string) {
    const snippet = `<script src="http://localhost:8000/static/widget.js" data-bot-id="${botId}" data-bot-name="Website Assistant" data-color="#6366f1"></script>`;
    navigator.clipboard.writeText(snippet);
    setCopiedId(botId);
    setTimeout(() => setCopiedId(null), 2000);
  }

  const totalPages = bots.reduce((sum, b) => sum + (b.pages_crawled || 0), 0);

  if (!loading && !user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 w-full max-w-md p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-blue-600">BotKit India</h1>
            <p className="text-gray-500 text-sm mt-1">
              This is your dashboard link. Sign in here to continue.
            </p>
          </div>

          {authError && (
            <div className="bg-red-50 text-red-600 text-sm px-4 py-3 rounded-lg mb-4">
              {authError}
            </div>
          )}

          <form onSubmit={handleDashboardLogin} className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="mt-1 w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                className="mt-1 w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button
              type="submit"
              disabled={authLoading}
              className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
            >
              {authLoading ? 'Signing in...' : 'Sign In to Dashboard'}
            </button>
          </form>

          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-gray-200" />
            <span className="text-xs text-gray-400">or</span>
            <div className="flex-1 h-px bg-gray-200" />
          </div>

          <button
            onClick={() => handleGoogleLogin()}
            disabled={googleLoading}
            className="w-full border border-gray-300 text-gray-700 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50 flex items-center justify-center gap-2 transition disabled:opacity-50"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            {googleLoading ? 'Signing in...' : 'Continue with Google'}
          </button>

          <p className="text-center text-sm text-gray-500 mt-6">
            Don&apos;t have an account? Use the signup page after opening the dashboard link.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Navbar */}
      <nav className="bg-white border-b border-gray-100 px-6 py-4 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg gradient-btn flex items-center justify-center text-white text-sm font-bold">
              B
            </div>
            <span className="font-bold text-gray-900">BotKit India</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 text-xs font-bold">
                {user?.name?.charAt(0).toUpperCase() || 'U'}
              </div>
              <span className="text-sm text-gray-600 hidden md:block">{user?.name}</span>
            </div>
            <button
              onClick={() => logout()}
              className="text-sm text-gray-400 hover:text-red-500 transition px-3 py-1.5 rounded-lg hover:bg-red-50"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Welcome back, {user?.name?.split(' ')[0]} 👋
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              Manage your AI chatbots
            </p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="gradient-btn text-white font-semibold px-5 py-2.5 rounded-xl text-sm flex items-center gap-2"
          >
            <span className="text-lg leading-none">+</span>
            New Chatbot
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {[
            { label: 'Total Bots', value: bots.length, icon: '🤖', color: 'bg-indigo-50 text-indigo-600' },
            { label: 'Pages Learned', value: totalPages, icon: '📄', color: 'bg-amber-50 text-amber-600' },
            { label: 'Plan', value: user?.plan || 'Free', icon: '⭐', color: 'bg-green-50 text-green-600' }
          ].map((stat, i) => (
            <div key={i} className="bg-white rounded-2xl p-5 border border-gray-100">
              <div className={`w-10 h-10 rounded-xl ${stat.color} flex items-center justify-center text-xl mb-3`}>
                {stat.icon}
              </div>
              <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
              <div className="text-xs text-gray-500 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Upload messages */}
        {uploadMsg && (
          <div className="mb-4 bg-green-50 text-green-600 text-sm px-4 py-3 rounded-xl">
            {uploadMsg}
          </div>
        )}
        {uploadError && (
          <div className="mb-4 bg-red-50 text-red-600 text-sm px-4 py-3 rounded-xl">
            ⚠️ {uploadError}
          </div>
        )}

        {/* Bot List */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">Your Chatbots</h2>
          <span className="text-sm text-gray-400">{bots.length} bot{bots.length !== 1 ? 's' : ''}</span>
        </div>

        {loading ? (
          <div className="grid gap-4">
            {[1,2,3].map(i => (
              <div key={i} className="bg-white rounded-2xl border border-gray-100 p-5 animate-pulse">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gray-100 rounded-xl" />
                  <div className="flex-1">
                    <div className="h-4 bg-gray-100 rounded w-1/3 mb-2" />
                    <div className="h-3 bg-gray-100 rounded w-1/4" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : bots.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-16 text-center">
            <div className="text-6xl mb-4">🤖</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No chatbots yet</h3>
            <p className="text-gray-500 text-sm mb-6">
              Create your first chatbot by pasting a website URL.
            </p>
            <button
              onClick={() => setShowModal(true)}
              className="gradient-btn text-white font-semibold px-6 py-3 rounded-xl text-sm"
            >
              Create Your First Bot
            </button>
          </div>
        ) : (
          <div className="grid gap-4">
            {bots.map(bot => {
              let hostname = bot.url;
              try { hostname = new URL(bot.url).hostname; } catch {}
              return (
                <div
                  key={bot.bot_id}
                  className="bg-white rounded-2xl border border-gray-100 p-5 hover:border-indigo-200 hover:shadow-sm transition-all duration-200"
                >
                  <div className="flex items-center justify-between flex-wrap gap-3">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-indigo-50 rounded-xl flex items-center justify-center text-2xl">
                        🌐
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900">{hostname}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {bot.pages_crawled} pages · ID: {bot.bot_id}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="inline-flex items-center gap-1.5 bg-green-50 text-green-600 text-xs font-medium px-3 py-1 rounded-full">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                        Ready
                      </span>

                      <button
                        onClick={() => router.push(`/chat/${bot.bot_id}`)}
                        className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
                      >
                        Chat
                      </button>

                      <button
                        onClick={() => copyWidget(bot.bot_id)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition border ${
                          copiedId === bot.bot_id
                            ? 'bg-green-50 text-green-600 border-green-200'
                            : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        {copiedId === bot.bot_id ? '✓ Copied!' : 'Copy Widget'}
                      </button>

                      {/* PDF Upload */}
                      <label className={`px-4 py-2 rounded-lg text-sm font-medium transition border cursor-pointer ${
                        uploadingBot === bot.bot_id
                          ? 'bg-amber-50 text-amber-600 border-amber-200'
                          : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                      }`}>
                        {uploadingBot === bot.bot_id ? '⏳ Processing...' : '📄 Add PDF'}
                        <input
                          type="file"
                          accept=".pdf"
                          className="hidden"
                          disabled={uploadingBot === bot.bot_id}
                          onChange={e => {
                            const file = e.target.files?.[0];
                            if (file) handlePDFUpload(bot.bot_id, file);
                            e.target.value = '';
                          }}
                        />
                      </label>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Bot Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Create New Chatbot</h3>
                <p className="text-sm text-gray-500 mt-0.5">Paste any website URL to get started</p>
              </div>
              <button
                onClick={() => { setShowModal(false); setStatusMsg(''); setUrl(''); }}
                className="text-gray-400 hover:text-gray-600 text-xl font-light"
              >
                x
              </button>
            </div>

            <form onSubmit={handleCreateBot} className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700">Website URL</label>
                <input
                  type="url"
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  placeholder="https://yourwebsite.com"
                  required
                  disabled={creating}
                  className="mt-1 w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                />
              </div>

              {statusMsg && (
                <div className={`text-sm px-4 py-3 rounded-lg ${
                  statusType === 'error'
                    ? 'bg-red-50 text-red-600'
                    : 'bg-indigo-50 text-indigo-600'
                }`}>
                  {statusType === 'info' && (
                    <span className="inline-block w-3 h-3 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mr-2" />
                  )}
                  {statusMsg}
                </div>
              )}

              <button
                type="submit"
                disabled={creating}
                className="w-full gradient-btn text-white font-semibold py-3 rounded-xl text-sm disabled:opacity-50"
              >
                {creating ? 'Creating chatbot...' : 'Create Chatbot'}
              </button>
            </form>

            <p className="text-xs text-gray-400 text-center mt-4">
              Crawling takes 1-2 minutes depending on website size
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
