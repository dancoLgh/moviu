import type { Config } from 'tailwindcss';
import { heroui } from '@heroui/theme';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './node_modules/@heroui/theme/dist/**/*.{js,ts,jsx,tsx}'
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: 'rgb(var(--background) / <alpha-value>)',
        foreground: 'rgb(var(--foreground) / <alpha-value>)',
        primary: 'rgb(var(--primary) / <alpha-value>)',
        brand: 'rgb(var(--brand) / <alpha-value>)',
        divider: 'rgb(var(--divider) / <alpha-value>)',
        content1: 'rgb(var(--content1) / <alpha-value>)',
        content2: 'rgb(var(--content2) / <alpha-value>)'
      }
    }
  },
  plugins: [
    heroui({
      themes: {
        light: {
          colors: {
            background: '#f8fafc',
            foreground: '#0f172a',
            primary: '#2563eb',
            brand: '#2563eb',
            divider: '#e2e8f0',
            content1: '#ffffff',
            content2: '#f1f5f9'
          }
        },
        dark: {
          colors: {
            background: '#020617',
            foreground: '#f8fafc',
            primary: '#60a5fa',
            brand: '#60a5fa',
            divider: '#1f2937',
            content1: '#0f172a',
            content2: '#1f2937'
          }
        }
      }
    })
  ]
};

export default config;
