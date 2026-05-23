'use client';

import { useState, useRef, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { sendQuestion } from '@/lib/api';

interface Message {
  role: 'user' | 'bot';
  text: string;
  sources?: string[];
  time: string;
}

function SourceLinks({ sources }: { sources: string[] }) {
  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {sources.map((s, idx) => {
        let hostname = s;
        try {
          hostname = new URL(s).hostname;
        } catch {
          hostname = s;
        }
        return (
          <a
            key={idx}
            href={s}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs bg-indigo-50 text-indigo-600 px-2 py-1 rounded-full hover:bg-indigo-100 transition"
          >
            <span>🔗</span>
            {hostname}
          </a>
        );
      })}
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-sm flex-shrink-0">
        🤖
      </div>
      <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
        <div className="flex items-center gap-1">
          {[0, 1, 2].map(i => (
            <div
              key={i}
              className="w-2 h-2 bg-indigo-400 rounded-full"
              style={{
                animation: 'bounce 1.2s infinite ease-in-out',
                animationDelay: `${i * 0.2}s`
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

const suggestions = [
  'What does this website offer?',
  'How can I contact you?',
  'What are your pricing plans?',
  'Tell me about your services'
];

const DEFAULT_BOT_MESSAGE =
  'Hi! I am your website assistant. Ask me anything about this website and I will answer from its content.';

export default function ChatPage() {
  const { bot_id } = useParams();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const storageKey = bot_id ? `botkit-chat-${String(bot_id)}` : null;

  useEffect(() => {
    if (!storageKey || typeof window === 'undefined') return;

    const saved = window.localStorage.getItem(storageKey);
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Message[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
          setShowSuggestions(parsed.length <= 1);
          return;
        }
      } catch {}
    }

    setMessages([{
      role: 'bot',
      text: DEFAULT_BOT_MESSAGE,
      time: getTime()
    }]);
    setShowSuggestions(true);
  }, [storageKey]);

  useEffect(() => {
    if (!storageKey || typeof window === 'undefined' || messages.length === 0) return;
    window.localStorage.setItem(storageKey, JSON.stringify(messages));
  }, [messages, storageKey]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking]);

  async function handleSend(question?: string) {
    const q = question || input.trim();
    if (!q || thinking) return;
    setInput('');
    setShowSuggestions(false);

    const userMessage: Message = {
      role: 'user',
      text: q,
      time: getTime()
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);

    setThinking(true);

    try {
      const history = updatedMessages
        .slice(-8)
        .map(msg => ({
          role: msg.role === 'user' ? 'user' : 'assistant',
          content: msg.text
        }));

      const res = await sendQuestion(bot_id as string, q, undefined, history);
      setMessages(prev => [...prev, {
        role: 'bot',
        text: res.data.answer,
        sources: res.data.sources,
        time: getTime()
      }]);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'bot',
        text: 'Sorry, I ran into an error: ' + (err.response?.data?.detail || 'Something went wrong.'),
        time: getTime()
      }]);
    } finally {
      setThinking(false);
      inputRef.current?.focus();
    }
  }

  function getTime() {
    return new Date().toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit'
    });
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">

      {/* Header */}
      <nav className="bg-white border-b border-gray-100 px-6 py-4 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/dashboard')}
            className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-gray-500 hover:bg-gray-200 transition text-sm"
          >
            {'<-'}
          </button>
          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-sm">
            🤖
          </div>
          <div>
            <h1 className="text-sm font-semibold text-gray-900">Website Assistant</h1>
            <p className="text-xs text-green-500 flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full inline-block" />
              Online · Bot {bot_id}
            </p>
          </div>
        </div>
        <button
          onClick={() => {
            if (storageKey && typeof window !== 'undefined') {
              window.localStorage.removeItem(storageKey);
            }
            setMessages([{
              role: 'bot',
              text: DEFAULT_BOT_MESSAGE,
              time: getTime()
            }]);
            setShowSuggestions(true);
          }}
          className="text-xs text-gray-400 hover:text-gray-600 transition px-3 py-1.5 rounded-lg hover:bg-gray-100"
        >
          Clear chat
        </button>
      </nav>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-2xl mx-auto flex flex-col gap-4">

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
            >
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0 ${
                msg.role === 'user'
                  ? 'gradient-btn text-white'
                  : 'bg-indigo-100'
              }`}>
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>

              {/* Bubble */}
              <div className={`flex flex-col max-w-[75%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${
                  msg.role === 'user'
                    ? 'gradient-btn text-white rounded-tr-sm'
                    : 'bg-white border border-gray-100 text-gray-800 rounded-tl-sm'
                }`}>
                  {msg.text}
                </div>

                {msg.sources && msg.sources.length > 0 && (
                  <SourceLinks sources={msg.sources} />
                )}

                <span className="text-xs text-gray-400 mt-1 px-1">{msg.time}</span>
              </div>
            </div>
          ))}

          {/* Thinking */}
          {thinking && <ThinkingIndicator />}

          {/* Suggestion chips */}
          {showSuggestions && messages.length === 1 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(s)}
                  className="text-xs bg-white border border-gray-200 text-gray-600 px-3 py-2 rounded-full hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50 transition"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-100 px-4 py-4">
        <div className="max-w-2xl mx-auto">
          <div className="flex gap-3 items-end">
            <div className="flex-1 bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3 flex items-center gap-3 focus-within:border-indigo-300 focus-within:bg-white transition">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                placeholder="Ask a question about this website..."
                disabled={thinking}
                className="flex-1 bg-transparent text-sm text-gray-900 placeholder-gray-400 outline-none disabled:opacity-50"
              />
            </div>
            <button
              onClick={() => handleSend()}
              disabled={thinking || !input.trim()}
              className="w-11 h-11 gradient-btn text-white rounded-xl flex items-center justify-center disabled:opacity-50 transition flex-shrink-0"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
          <p className="text-xs text-gray-400 text-center mt-2">
            Powered by BotKit India · Answers from website content only
          </p>
        </div>
      </div>
    </div>
  );
}
