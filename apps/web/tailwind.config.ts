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
        brand: {
          DEFAULT: '#2563eb',
          foreground: '#ffffff'
        }
      }
    }
  },
  plugins: [
    heroui({
      themes: {
        light: {
          colors: {
            background: '#f8fafc',
            foreground: '#020617',
            brand: '#2563eb'
          }
        },
        dark: {
          colors: {
            background: '#020617',
            foreground: '#f8fafc',
            brand: '#60a5fa'
          }
        }
      }
    })
  ]
};

export default config;
