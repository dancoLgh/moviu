import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}'
  ],
  darkMode: ['class'],
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
  plugins: []
};

export default config;
