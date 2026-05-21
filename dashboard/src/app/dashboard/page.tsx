'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getMyBots, crawlWebsite, getBotStatus } from '@/lib/api';
import { getUser, logout } from '@/lib/auth';

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

  useEffect(() => {
    setUser(getUser());
    fetchBots();
  }, []);

  async function fetchBots() {
    try {
      const res = await getMyBots();
      setBots(res.data.bots);
    } catch {
      logout();
    } finally {
      setLoading(false);
    }
  }

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

  function copyWidget(botId: string) {
    const snippet = `<script src="http://localhost:8000/static/widget.js" data-bot-id="${botId}" data-bot-name="Website Assistant" data-color="#6366f1"></script>`;
    navigator.clipboard.writeText(snippet);
    setCopiedId(botId);
    setTimeout(() => setCopiedId(null), 2000);
  }

  const totalPages = bots.reduce((sum, b) => sum + (b.pages_crawled || 0), 0);

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
              onClick={logout}
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
                  <div className="flex items-center justify-between">
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

                    <div className="flex items-center gap-3">
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
