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
  const user = getUser();
  const [bots, setBots] = useState<Bot[]>([]);
  const [url, setUrl] = useState('');
  const [creating, setCreating] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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

    try {
      const res = await crawlWebsite(url);
      const botId = res.data.bot_id;
      setStatusMsg('Crawling website...');

      // Poll status
      const interval = setInterval(async () => {
        const s = await getBotStatus(botId);
        const data = s.data;
        setStatusMsg(`Crawling... ${data.pages_crawled} pages found`);

        if (data.status === 'ready') {
          clearInterval(interval);
          setStatusMsg('');
          setUrl('');
          setCreating(false);
          fetchBots();
        } else if (data.status === 'error') {
          clearInterval(interval);
          setStatusMsg('Error: ' + data.error);
          setCreating(false);
        }
      }, 2000);

    } catch (err: any) {
      setStatusMsg('Failed: ' + (err.response?.data?.detail || 'Unknown error'));
      setCreating(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Navbar */}
      <nav className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-lg font-bold text-blue-600">BotKit India</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{user?.name}</span>
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-red-500 transition"
          >
            Logout
          </button>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-8">

        {/* Create Bot */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-800 mb-1">
            Create New Chatbot
          </h2>
          <p className="text-sm text-gray-500 mb-4">
            Paste any website URL and we'll train a bot on its content.
          </p>
          <form onSubmit={handleCreateBot} className="flex gap-3">
            <input
              type="url"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://yourwebsite.com"
              required
              disabled={creating}
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={creating}
              className="bg-blue-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition whitespace-nowrap"
            >
              {creating ? 'Creating...' : 'Create Bot'}
            </button>
          </form>
          {statusMsg && (
            <p className="text-sm text-blue-600 mt-3">{statusMsg}</p>
          )}
        </div>

        {/* Bot List */}
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Your Bots ({bots.length})
        </h2>

        {loading ? (
          <p className="text-sm text-gray-400">Loading...</p>
        ) : bots.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center">
            <p className="text-gray-400 text-sm">
              No bots yet. Create your first one above.
            </p>
          </div>
        ) : (
          <div className="grid gap-4">
            {bots.map(bot => (
              <div
                key={bot.bot_id}
                className="bg-white rounded-2xl border border-gray-200 p-5 flex items-center justify-between"
              >
                <div>
                  <p className="text-sm font-medium text-gray-800 truncate max-w-xs">
                    {bot.url}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {bot.pages_crawled} pages · Bot ID: {bot.bot_id}
                  </p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => router.push(`/chat/${bot.bot_id}`)}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition"
                  >
                    Chat
                  </button>
                  <button
                    onClick={() => {
                      const snippet = `<script src="http://localhost:8000/static/widget.js" data-bot-id="${bot.bot_id}"></script>`;
                      navigator.clipboard.writeText(snippet);
                      alert('Widget code copied!');
                    }}
                    className="border border-gray-300 text-gray-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition"
                  >
                    Copy Widget
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}