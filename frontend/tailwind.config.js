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
    			background: '#FFFBF7',
    			foreground: '#2D241E',
    			primary: {
    				DEFAULT: '#FF6B00',
    				foreground: '#FFFFFF',
    				hover: '#E65A00',
    				light: '#FFD8C2'
    			},
    			secondary: {
    				DEFAULT: '#FFD8C2',
    				foreground: '#2D241E'
    			},
    			destructive: {
    				DEFAULT: '#FF453A',
    				foreground: '#FFFFFF'
    			},
    			muted: {
    				DEFAULT: '#F5EFE6',
    				foreground: '#786C66'
    			},
    			accent: {
    				DEFAULT: '#CCF381',
    				foreground: '#2D241E',
    				blue: '#4D96FF',
    				pink: '#FF8CC6'
    			},
    			popover: {
    				DEFAULT: '#FFFFFF',
    				foreground: '#2D241E'
    			},
    			card: {
    				DEFAULT: '#FFFFFF',
    				foreground: '#2D241E'
    			},
    			orange: {
    				50: '#FFF7ED',
    				100: '#FFEDD5',
    				200: '#FFD8C2',
    				300: '#FDBA74',
    				400: '#FB923C',
    				500: '#F97316',
    				600: '#FF6B00',
    				700: '#C2410C',
    				800: '#9A3412',
    				900: '#7C2D12'
    			}
    		},
    		borderRadius: {
    			lg: '1.5rem',
    			md: '1rem',
    			sm: '0.75rem'
    		},
    		fontFamily: {
    			sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
    			heading: ['Syne', 'system-ui', 'sans-serif']
    		},
    		boxShadow: {
    			'soft-orange': '0 10px 40px -10px rgba(255, 107, 0, 0.15)',
    			'float': '0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.01)'
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
    				from: { opacity: '0', transform: 'translateY(10px)' },
    				to: { opacity: '1', transform: 'translateY(0)' }
    			}
    		},
    		animation: {
    			'accordion-down': 'accordion-down 0.2s ease-out',
    			'accordion-up': 'accordion-up 0.2s ease-out',
    			'fade-in': 'fade-in 0.5s ease-out forwards'
    		}
    	}
    },
    plugins: [require("tailwindcss-animate")],
};
