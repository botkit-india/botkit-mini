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
    <div className="text-xs text-gray-400 mt-1 px-1">
      {'Sources: '}
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
            className="text-blue-500 hover:underline mr-2"
          >
            {hostname}
          </a>
        );
      })}
    </div>
  );
}

export default function ChatPage() {
  const { bot_id } = useParams();
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages([{
      role: 'bot',
      text: 'Hi! Ask me anything about this website.',
      time: getTime()
    }]);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking]);

  async function handleSend() {
    if (!input.trim() || thinking) return;
    const question = input.trim();
    setInput('');

    setMessages(prev => [...prev, {
      role: 'user',
      text: question,
      time: getTime()
    }]);

    setThinking(true);

    try {
      const res = await sendQuestion(bot_id as string, question);
      setMessages(prev => [...prev, {
        role: 'bot',
        text: res.data.answer,
        sources: res.data.sources,
        time: getTime()
      }]);
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'bot',
        text: '⚠️ ' + (err.response?.data?.detail || 'Something went wrong.'),
        time: getTime()
      }]);
    } finally {
      setThinking(false);
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
      <nav className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => router.push('/dashboard')}
          className="text-gray-400 hover:text-gray-600 transition"
        >
          ← Back
        </button>
        <h1 className="text-sm font-semibold text-gray-800">
          Bot: {bot_id}
        </h1>
      </nav>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 max-w-2xl mx-auto w-full">
        <div className="flex flex-col gap-4">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-sm'
                  : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'
              }`}>
                {msg.text}
              </div>

              {msg.sources && msg.sources.length > 0 && (
                <SourceLinks sources={msg.sources} />
              )}

              <span className="text-xs text-gray-400 mt-1 px-1">{msg.time}</span>
            </div>
          ))}

          {/* Thinking indicator */}
          {thinking && (
            <div className="flex items-start">
              <div className="bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-bl-sm flex gap-1">
                {[0, 1, 2].map(i => (
                  <div
                    key={i}
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-2xl mx-auto flex gap-3">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="Ask a question..."
            disabled={thinking}
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={thinking || !input.trim()}
            className="bg-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
