import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { GoogleOAuthProvider } from '@react-oauth/google';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'BotKit India — AI Chatbot for Indian Businesses',
  description: 'Paste a URL. Get a 24/7 AI support agent in 10 minutes. Hindi + 9 Indian languages. Starting at ₹999/month.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <GoogleOAuthProvider
          clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || ''}
        >
          {children}
        </GoogleOAuthProvider>
      </body>
    </html>
  );
}