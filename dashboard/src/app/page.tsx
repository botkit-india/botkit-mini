'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const features = [
  {
    icon: '🕷️',
    title: 'Smart Web Crawler',
    desc: 'Automatically crawls your entire website and learns from every page in minutes.'
  },
  {
    icon: '🧠',
    title: 'RAG-Powered AI',
    desc: 'Answers questions using only your website content — no hallucinations, ever.'
  },
  {
    icon: '💬',
    title: 'Embeddable Widget',
    desc: 'One line of code. Chat bubble appears on your website instantly.'
  },
  {
    icon: '📱',
    title: 'WhatsApp Bot',
    desc: 'Same trained bot deployed on your WhatsApp Business number. India-first.'
  },
  {
    icon: '🇮🇳',
    title: 'Hindi + 9 Languages',
    desc: 'Built for India. Supports Hindi, Marathi, Tamil, Telugu and more.'
  },
  {
    icon: '📊',
    title: 'Analytics Dashboard',
    desc: 'See what customers ask, what the bot answers, and what gaps to fill.'
  }
];

const plans = [
  {
    name: 'Starter',
    price: '999',
    desc: 'Perfect for small businesses',
    features: ['500 conversations/mo', '1 website', 'Hindi + English', 'Basic analytics'],
    cta: 'Start Free Trial',
    highlight: false
  },
  {
    name: 'Growth',
    price: '2,499',
    desc: 'For growing businesses',
    features: ['3,000 conversations/mo', '3 websites', 'WhatsApp bot', '5 languages', 'Advanced analytics'],
    cta: 'Start Free Trial',
    highlight: true
  },
  {
    name: 'Pro',
    price: '5,999',
    desc: 'For agencies and enterprises',
    features: ['15,000 conversations/mo', '10 websites', 'All features', 'All 10+ languages', 'White-label', 'Custom export'],
    cta: 'Contact Us',
    highlight: false
  }
];

const testimonials = [
  {
    name: 'Priya Sharma',
    role: 'Founder, FitLife India',
    text: 'Our support queries dropped by 70% in the first week. BotKit handles everything from pricing to class schedules.',
    avatar: 'PS'
  },
  {
    name: 'Rajesh Kumar',
    role: 'Director, Pune Coaching Academy',
    text: 'Students get instant answers about admissions at 2 AM. We never miss an inquiry now.',
    avatar: 'RK'
  },
  {
    name: 'Anita Desai',
    role: 'Owner, Wellness Clinic',
    text: 'Setup took 10 minutes. The bot speaks Hindi and answers appointment queries perfectly.',
    avatar: 'AD'
  }
];

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-white">

      {/* Navbar */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? 'bg-white/90 backdrop-blur-md shadow-sm' : 'bg-transparent'
      }`}>
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg gradient-btn flex items-center justify-center text-white text-sm font-bold">
              B
            </div>
            <span className="font-bold text-gray-900">BotKit India</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-gray-600 hover:text-gray-900 transition">Features</a>
            <a href="#pricing" className="text-sm text-gray-600 hover:text-gray-900 transition">Pricing</a>
            <a href="#testimonials" className="text-sm text-gray-600 hover:text-gray-900 transition">Testimonials</a>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900 transition">
              Sign in
            </Link>
            <Link
              href="/signup"
              className="gradient-btn text-white text-sm font-medium px-4 py-2 rounded-lg"
            >
              Start Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-20 px-6 relative overflow-hidden">
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-indigo-100 rounded-full blur-3xl opacity-40 -z-10" />
        <div className="absolute top-40 right-1/4 w-80 h-80 bg-amber-100 rounded-full blur-3xl opacity-40 -z-10" />

        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-indigo-50 text-indigo-600 text-xs font-medium px-3 py-1.5 rounded-full mb-6">
            <span className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-pulse" />
            Now with Hindi + 9 Indian Languages
          </div>

          <h1 className="text-5xl md:text-7xl font-bold text-gray-900 leading-tight mb-6">
            AI Chatbot for Your{' '}
            <span className="gradient-text">Indian Business</span>
          </h1>

          <p className="text-xl text-gray-500 max-w-2xl mx-auto mb-10 leading-relaxed">
            Paste your website URL. Get a 24/7 AI support agent in 10 minutes.
            Trained on your content. Speaks Hindi. Starts at{' '}
            <span className="text-gray-900 font-semibold">Rs.999/month.</span>
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link
              href="/signup"
              className="gradient-btn text-white font-semibold px-8 py-4 rounded-xl text-lg w-full sm:w-auto text-center"
            >
              Start Free Trial
            </Link>
            <a
              href="#features"
              className="text-gray-600 font-medium px-8 py-4 rounded-xl text-lg border border-gray-200 hover:bg-gray-50 transition w-full sm:w-auto text-center"
            >
              See How It Works
            </a>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 max-w-lg mx-auto">
            {[
              { num: '10 min', label: 'Setup time' },
              { num: 'Rs.999', label: 'Starting price' },
              { num: '10+', label: 'Indian languages' }
            ].map((stat, i) => (
              <div key={i} className="text-center">
                <div className="text-2xl font-bold text-gray-900">{stat.num}</div>
                <div className="text-xs text-gray-500 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Hero mockup */}
        <div className="max-w-5xl mx-auto mt-16">
          <div className="bg-gray-900 rounded-2xl p-1 shadow-2xl">
            <div className="bg-gray-800 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <div className="flex-1 bg-gray-700 rounded-md h-6 ml-2" />
              </div>
              <div className="bg-gray-900 rounded-lg p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <div className="h-4 bg-indigo-500 rounded w-32 mb-2" />
                    <div className="h-3 bg-gray-700 rounded w-24" />
                  </div>
                  <div className="h-8 bg-indigo-500 rounded-lg w-28" />
                </div>
                <div className="grid grid-cols-3 gap-3 mb-6">
                  {[1,2,3].map(i => (
                    <div key={i} className="bg-gray-800 rounded-lg p-3">
                      <div className="h-3 bg-gray-700 rounded w-3/4 mb-2" />
                      <div className="h-6 bg-indigo-500/30 rounded w-1/2" />
                    </div>
                  ))}
                </div>
                <div className="space-y-2">
                  {[1,2,3].map(i => (
                    <div key={i} className="bg-gray-800 rounded-lg p-3 flex items-center gap-3">
                      <div className="w-8 h-8 bg-indigo-500/30 rounded-lg" />
                      <div className="flex-1">
                        <div className="h-3 bg-gray-700 rounded w-1/2 mb-1" />
                        <div className="h-2 bg-gray-700 rounded w-1/3" />
                      </div>
                      <div className="h-6 bg-green-500/30 rounded-full w-16" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 px-6 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Live in <span className="gradient-text">10 minutes</span>
            </h2>
            <p className="text-gray-500 text-lg">No technical knowledge required.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: '01', title: 'Paste your URL', desc: 'Enter your website URL. Our crawler reads every page automatically.', icon: '🔗' },
              { step: '02', title: 'AI learns your content', desc: 'Our RAG engine processes and indexes all your content in minutes.', icon: '🧠' },
              { step: '03', title: 'Add one line of code', desc: 'Copy the script tag and paste it on your website. Done.', icon: '✨' }
            ].map((item, i) => (
              <div key={i} className="relative">
                <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                  <div className="text-3xl mb-4">{item.icon}</div>
                  <div className="text-xs font-bold text-indigo-500 mb-2">{item.step}</div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">{item.title}</h3>
                  <p className="text-gray-500 text-sm leading-relaxed">{item.desc}</p>
                </div>
                {i < 2 && (
                  <div className="hidden md:block absolute top-1/2 -right-4 text-gray-300 text-2xl">
                    {'->'}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Everything your business needs
            </h2>
            <p className="text-gray-500 text-lg max-w-2xl mx-auto">
              Built specifically for Indian SMBs. Not a global tool with Indian language as an afterthought.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <div
                key={i}
                className="group bg-white rounded-2xl p-6 border border-gray-100 hover:border-indigo-200 hover:shadow-lg transition-all duration-300"
              >
                <div className="text-3xl mb-4">{f.icon}</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-20 px-6 bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Simple, honest pricing
            </h2>
            <p className="text-gray-500 text-lg">
              In Indian Rupees. Pay via UPI, cards, or net banking.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {plans.map((plan, i) => (
              <div
                key={i}
                className={`rounded-2xl p-6 ${
                  plan.highlight
                    ? 'gradient-btn text-white shadow-xl scale-105'
                    : 'bg-white border border-gray-100'
                }`}
              >
                {plan.highlight && (
                  <div className="text-xs font-bold bg-white/20 text-white px-3 py-1 rounded-full w-fit mb-4">
                    Most Popular
                  </div>
                )}
                <h3 className={`text-lg font-bold mb-1 ${plan.highlight ? 'text-white' : 'text-gray-900'}`}>
                  {plan.name}
                </h3>
                <p className={`text-xs mb-4 ${plan.highlight ? 'text-white/70' : 'text-gray-500'}`}>
                  {plan.desc}
                </p>
                <div className="mb-6">
                  <span className={`text-4xl font-bold ${plan.highlight ? 'text-white' : 'text-gray-900'}`}>
                    Rs.{plan.price}
                  </span>
                  <span className={`text-sm ${plan.highlight ? 'text-white/70' : 'text-gray-500'}`}>/month</span>
                </div>
                <ul className="space-y-2 mb-6">
                  {plan.features.map((f, j) => (
                    <li key={j} className={`text-sm flex items-center gap-2 ${plan.highlight ? 'text-white/90' : 'text-gray-600'}`}>
                      <span className={plan.highlight ? 'text-white' : 'text-indigo-500'}>✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/signup"
                  className={`block text-center py-2.5 rounded-xl text-sm font-semibold transition ${
                    plan.highlight
                      ? 'bg-white text-indigo-600 hover:bg-white/90'
                      : 'bg-indigo-600 text-white hover:bg-indigo-700'
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
          <p className="text-center text-gray-500 text-sm mt-8">
            14-day free trial on all plans · No credit card required · Annual billing saves 2 months
          </p>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Loved by Indian businesses
            </h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((t, i) => (
              <div key={i} className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
                <div className="flex items-center gap-1 mb-4">
                  {[1,2,3,4,5].map(s => (
                    <span key={s} className="text-amber-400 text-sm">★</span>
                  ))}
                </div>
                <p className="text-gray-600 text-sm leading-relaxed mb-4">&quot;{t.text}&quot;</p>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full gradient-btn flex items-center justify-center text-white text-xs font-bold">
                    {t.avatar}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-gray-900">{t.name}</div>
                    <div className="text-xs text-gray-500">{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-3xl mx-auto">
          <div className="gradient-btn rounded-3xl p-12 text-center text-white">
            <h2 className="text-4xl font-bold mb-4">
              Ready to automate your support?
            </h2>
            <p className="text-white/80 text-lg mb-8">
              Join hundreds of Indian businesses saving hours every day.
            </p>
            <Link
              href="/signup"
              className="inline-block bg-white text-indigo-600 font-bold px-8 py-4 rounded-xl text-lg hover:bg-white/90 transition"
            >
              Start Free Trial — No Credit Card
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t border-gray-100">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded gradient-btn flex items-center justify-center text-white text-xs font-bold">B</div>
            <span className="font-semibold text-gray-900">BotKit India</span>
          </div>
          <p className="text-sm text-gray-500">
            Built with love in Pune, India · 2026
          </p>
          <div className="flex items-center gap-6">
            <a href="#" className="text-sm text-gray-500 hover:text-gray-900 transition">Privacy</a>
            <a href="#" className="text-sm text-gray-500 hover:text-gray-900 transition">Terms</a>
            <a href="#" className="text-sm text-gray-500 hover:text-gray-900 transition">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
