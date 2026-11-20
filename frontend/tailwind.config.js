/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: ["./src/**/*.{js,jsx,ts,tsx}"],
    theme: {
    	extend: {
    		colors: {
    			border: 'hsl(var(--border))',
    			input: 'hsl(var(--input))',
    			ring: 'hsl(var(--ring))',
    			background: 'hsl(var(--background))',
    			foreground: 'hsl(var(--foreground))',
    			primary: {
    				DEFAULT: 'hsl(var(--primary))',
    				foreground: 'hsl(var(--primary-foreground))',
    				hover: '#F2622A',
    				light: '#FFE5D8',
    				ink: '#C44A15'
    			},
    			secondary: {
    				DEFAULT: 'hsl(var(--secondary))',
    				foreground: 'hsl(var(--secondary-foreground))'
    			},
    			destructive: {
    				DEFAULT: 'hsl(var(--destructive))',
    				foreground: 'hsl(var(--destructive-foreground))'
    			},
    			muted: {
    				DEFAULT: 'hsl(var(--muted))',
    				foreground: 'hsl(var(--muted-foreground))'
    			},
    			accent: {
    				DEFAULT: 'hsl(var(--accent))',
    				foreground: 'hsl(var(--accent-foreground))'
    			},
    			popover: {
    				DEFAULT: 'hsl(var(--popover))',
    				foreground: 'hsl(var(--popover-foreground))'
    			},
    			card: {
    				DEFAULT: 'hsl(var(--card))',
    				foreground: 'hsl(var(--card-foreground))'
    			},
    			ink: { DEFAULT: '#242323', 700: '#3A3837', 500: '#6B6560', 300: '#A39C95' },
    			ivory: '#FFF9F3',
    			peach: '#FFE5D8',
    			stone: '#F1EFEB',
    			plum: { DEFAULT: '#49344D', 50: '#F4EFF5', 100: '#E6DCE8', 500: '#7A5E80', 700: '#49344D' },
    			sage: { DEFAULT: '#A9B8A1', 50: '#F1F4EF', 100: '#DFE6DB', 400: '#A9B8A1', 700: '#5E7356' },
    			amber: { 50: '#FDF5E7', 100: '#F9E5C0', 700: '#8A5A0B' },
    			brick: { 50: '#FCEEEC', 100: '#F6D3CE', 700: '#B42318' },
    			orange: {
    				50: '#FFF6F0',
    				100: '#FFE5D8',
    				200: '#FFCBB2',
    				300: '#FFA67F',
    				400: '#FF8A5B',
    				500: '#FF7138',
    				600: '#E85D24',
    				700: '#C44A15',
    				800: '#9A3A12',
    				900: '#6E2A0E'
    			}
    		},
    		borderRadius: {
    			xl: '14px',
    			lg: '12px',
    			md: '8px',
    			sm: '6px'
    		},
    		fontFamily: {
    			sans: ['Inter Variable', 'Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
    			heading: ['Fraunces Variable', 'Fraunces', 'Georgia', 'serif'],
    			display: ['Fraunces Variable', 'Fraunces', 'Georgia', 'serif']
    		},
    		boxShadow: {
    			'soft-orange': '0 8px 24px -12px rgba(255, 113, 56, 0.45)',
    			'float': '0 12px 32px -12px rgba(36, 35, 35, 0.18)',
    			'card': '0 1px 2px rgba(36, 35, 35, 0.04), 0 1px 1px rgba(36, 35, 35, 0.02)',
    			'lift': '0 6px 20px -8px rgba(36, 35, 35, 0.16)'
    		},
    		keyframes: {
    			'accordion-down': {
    				from: { height: '0' },
    				to: { height: 'var(--radix-accordion-content-height)' }
    			},
    			'accordion-up': {
    				from: { height: 'var(--radix-accordion-content-height)' },
    				to: { height: '0' }
    			},
    			'fade-in': {
    				from: { opacity: '0', transform: 'translateY(6px)' },
    				to: { opacity: '1', transform: 'translateY(0)' }
    			},
    			'pulse-dot': {
    				'0%, 100%': { opacity: '1' },
    				'50%': { opacity: '0.35' }
    			}
    		},
    		animation: {
    			'accordion-down': 'accordion-down 0.2s ease-out',
    			'accordion-up': 'accordion-up 0.2s ease-out',
    			'fade-in': 'fade-in 0.25s ease-out both',
    			'pulse-dot': 'pulse-dot 1.4s ease-in-out infinite'
    		}
    	}
    },
    plugins: [require("tailwindcss-animate")],
};
