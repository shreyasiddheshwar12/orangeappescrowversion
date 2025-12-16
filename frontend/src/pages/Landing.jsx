import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, Users, TrendingUp, Heart, ArrowRight, Instagram } from 'lucide-react';
import { Button } from '../components/ui/button';

const Landing = () => {
  const navigate = useNavigate();
  const [hoveredRole, setHoveredRole] = useState(null);

  const features = [
    {
      icon: <Users className="w-6 h-6" />,
      title: "Find Your Match",
      desc: "Brands meet creators. Magic happens."
    },
    {
      icon: <TrendingUp className="w-6 h-6" />,
      title: "Grow Together",
      desc: "Collabs that make both sides shine."
    },
    {
      icon: <Heart className="w-6 h-6" />,
      title: "Real Connections",
      desc: "No middlemen. Just good vibes."
    }
  ];

  return (
    <div className="min-h-screen gradient-hero overflow-hidden">
      {/* Hero Section */}
      <div className="relative">
        {/* Decorative blobs */}
        <div className="absolute top-20 left-10 w-72 h-72 bg-primary/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent/20 rounded-full blur-3xl animate-pulse" />
        
        {/* Navigation */}
        <nav className="relative z-10 flex items-center justify-between px-6 lg:px-12 py-6">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
              <span className="text-white text-xl">🍊</span>
            </div>
            <span className="font-heading font-bold text-2xl text-foreground">Orange</span>
          </div>
          <div className="flex gap-4">
            <Button 
              variant="ghost" 
              className="rounded-full"
              onClick={() => navigate('/login')}
              data-testid="nav-login-btn"
            >
              Log in
            </Button>
            <Button 
              className="btn-primary"
              onClick={() => navigate('/signup')}
              data-testid="nav-signup-btn"
            >
              Get Started
            </Button>
          </div>
        </nav>

        {/* Hero Content */}
        <div className="relative z-10 max-w-7xl mx-auto px-6 lg:px-12 pt-16 pb-24">
          <motion.div 
            className="text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 bg-white/80 backdrop-blur-sm px-4 py-2 rounded-full border border-orange-200 mb-8">
              <Sparkles className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium text-muted-foreground">Where creators & brands collab</span>
            </div>
            
            <h1 className="font-heading text-5xl md:text-7xl font-bold tracking-tight leading-[0.9] mb-6">
              <span className="text-foreground">Make your </span>
              <span className="text-gradient">content</span>
              <br />
              <span className="text-foreground">pay the bills 🍊</span>
            </h1>
            
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-12">
              Orange connects creators with brands that actually get it. 
              No awkward DM slides. Just sweet collabs.
            </p>

            {/* Role Selection Cards */}
            <div className="flex flex-col sm:flex-row gap-6 justify-center items-center mb-16">
              <motion.div
                className={`relative group cursor-pointer`}
                onMouseEnter={() => setHoveredRole('creator')}
                onMouseLeave={() => setHoveredRole(null)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => navigate('/signup?role=creator')}
                data-testid="role-creator-card"
              >
                <div className={`card-orange p-8 w-72 transition-all ${hoveredRole === 'creator' ? 'border-primary shadow-soft-orange' : ''}`}>
                  <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-4 mx-auto">
                    <span className="text-3xl">🎨</span>
                  </div>
                  <h3 className="font-heading font-bold text-xl mb-2">I'm a Creator 🍊</h3>
                  <p className="text-muted-foreground text-sm mb-4">
                    Show off your content & get paid collabs
                  </p>
                  <div className="flex items-center justify-center gap-2 text-primary font-semibold">
                    <span>Start creating</span>
                    <ArrowRight className="w-4 h-4" />
                  </div>
                </div>
              </motion.div>

              <motion.div
                className={`relative group cursor-pointer`}
                onMouseEnter={() => setHoveredRole('business')}
                onMouseLeave={() => setHoveredRole(null)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => navigate('/signup?role=business')}
                data-testid="role-business-card"
              >
                <div className={`card-orange p-8 w-72 transition-all ${hoveredRole === 'business' ? 'border-primary shadow-soft-orange' : ''}`}>
                  <div className="w-16 h-16 bg-accent/30 rounded-2xl flex items-center justify-center mb-4 mx-auto">
                    <span className="text-3xl">💼</span>
                  </div>
                  <h3 className="font-heading font-bold text-xl mb-2">I'm a Brand 🧡</h3>
                  <p className="text-muted-foreground text-sm mb-4">
                    Find creators who match your vibe
                  </p>
                  <div className="flex items-center justify-center gap-2 text-primary font-semibold">
                    <span>Find creators</span>
                    <ArrowRight className="w-4 h-4" />
                  </div>
                </div>
              </motion.div>
            </div>

            {/* Social Proof */}
            <div className="flex flex-wrap justify-center gap-8 items-center text-muted-foreground">
              <div className="flex items-center gap-2">
                <Instagram className="w-5 h-5" />
                <span className="text-sm">500+ Creators</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm">🎯 1000+ Collabs</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm">💰 ₹50L+ Earned</span>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Features Section */}
        <div className="relative z-10 bg-white/50 backdrop-blur-sm py-24">
          <div className="max-w-7xl mx-auto px-6 lg:px-12">
            <div className="text-center mb-16">
              <h2 className="font-heading text-4xl md:text-5xl font-bold mb-4">
                Why Orange? 🍊
              </h2>
              <p className="text-muted-foreground text-lg">
                Good brands advertise. Great brands collaborate.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {features.map((feature, index) => (
                <motion.div
                  key={index}
                  className="card-orange p-8 text-center"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                >
                  <div className="w-14 h-14 bg-primary/10 rounded-2xl flex items-center justify-center mb-4 mx-auto text-primary">
                    {feature.icon}
                  </div>
                  <h3 className="font-heading font-bold text-xl mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground">{feature.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="relative z-10 py-24">
          <div className="max-w-4xl mx-auto px-6 lg:px-12 text-center">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6 }}
              className="card-orange p-12 bg-gradient-to-br from-primary/5 to-accent/10"
            >
              <h2 className="font-heading text-3xl md:text-4xl font-bold mb-4">
                Ready to squeeze the juice? 🧃
              </h2>
              <p className="text-muted-foreground text-lg mb-8">
                Join Orange today and start making content that pays.
              </p>
              <Button 
                className="btn-primary text-lg px-12 py-6"
                onClick={() => navigate('/signup')}
                data-testid="cta-get-started-btn"
              >
                Get Started Free
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </motion.div>
          </div>
        </div>

        {/* Footer */}
        <footer className="relative z-10 border-t border-orange-100 py-8">
          <div className="max-w-7xl mx-auto px-6 lg:px-12 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                <span className="text-white">🍊</span>
              </div>
              <span className="font-heading font-bold text-lg">Orange</span>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2024 Orange. Made with 🧡 for creators.
            </p>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default Landing;
