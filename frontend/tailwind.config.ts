import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#F7F6F3',
        surface: '#FFFFFF',
        'surface-2': '#F1EFEA',
        border: '#E2DFD8',
        'border-strong': '#CFCBC1',
        ink: '#1C1B19',
        'ink-2': '#5B5850',
        'ink-3': '#8A867C',
        accent: {
          50: '#EEF7F6',
          100: '#DCEEEC',
          600: '#0F6B64',
          700: '#0B4F4A',
        },
        ok: '#2E7D5B',
        warn: '#B7791F',
        bad: '#C2412D',
        info: '#356CA5',
        // Roster status cell colors (WCAG AA compliant)
        cell: {
          w: '#FFFFFF',
          wo: '#E9E4F4',
          ph: '#F8E7C6',
          hw: '#DCEEEC',
          l: '#F6D9D5',
          co: '#D9E7F5',
        },
      },
      borderRadius: {
        ctl: '6px',
        pop: '10px',
        chip: '4px',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      boxShadow: {
        layer: '0 8px 24px rgba(28, 27, 25, 0.10)',
      },
    },
  },
  plugins: [],
};

export default config;
