import { motion } from "framer-motion";
import { GraduationCap, ArrowRight, Volume2, VolumeX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import type { User } from "@supabase/supabase-js";

const FEATURES = [
  {
    tag: "MATCH",
    text: "Uses your profile to find perfect scholarship matches tailored to your goals",
  },
  {
    tag: "RANK",
    text: "Semantically re-ranks results for precision using on-device intelligence",
  },
  {
    tag: "SECURE",
    text: "Keeps your data safe — you own your information with secure authentication",
  },
];

const GrainOverlay = () => (
  <div
    className="pointer-events-none fixed inset-0 z-50 opacity-[0.03]"
    style={{
      backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
      backgroundRepeat: "repeat",
      backgroundSize: "128px 128px",
    }}
  />
);

const FloatingOrbs = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none">
    {[
      { x: "15%", y: "20%", size: 400, color: "152, 60%, 52%", delay: 0 },
      { x: "75%", y: "60%", size: 300, color: "152, 60%, 52%", delay: 2 },
      { x: "50%", y: "80%", size: 500, color: "200, 50%, 40%", delay: 4 },
    ].map((orb, i) => (
      <motion.div
        key={i}
        className="absolute rounded-full"
        style={{
          width: orb.size,
          height: orb.size,
          left: orb.x,
          top: orb.y,
          background: `radial-gradient(circle, hsl(${orb.color} / 0.08) 0%, transparent 70%)`,
          filter: "blur(60px)",
        }}
        animate={{
          x: [0, 30, -20, 0],
          y: [0, -40, 20, 0],
          scale: [1, 1.1, 0.95, 1],
        }}
        transition={{
          duration: 12,
          repeat: Infinity,
          delay: orb.delay,
          ease: "easeInOut",
        }}
      />
    ))}
  </div>
);

const Landing = () => {
  const navigate = useNavigate();
  const [isMuted, setIsMuted] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    audioRef.current = new Audio("https://assets.mixkit.co/active_storage/sfx/2515/2515-preview.mp3");
    audioRef.current.loop = true;
    audioRef.current.volume = 0.15;
    return () => {
      audioRef.current?.pause();
    };
  }, []);

  const toggleSound = () => {
    if (!audioRef.current) return;
    if (isMuted) {
      audioRef.current.play().catch(() => {});
    } else {
      audioRef.current.pause();
    }
    setIsMuted(!isMuted);
  };

  const containerVariants = {
    hidden: {},
    visible: {
      transition: { staggerChildren: 0.12, delayChildren: 0.3 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30, filter: "blur(10px)" },
    visible: {
      opacity: 1,
      y: 0,
      filter: "blur(0px)",
      transition: { duration: 0.8, ease: [0.22, 1, 0.36, 1] as const },
    },
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[hsl(0,0%,3%)] text-[hsl(0,0%,95%)]">
      <GrainOverlay />
      <FloatingOrbs />

      {/* Grid */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: `linear-gradient(hsl(0 0% 50%) 1px, transparent 1px), linear-gradient(90deg, hsl(0 0% 50%) 1px, transparent 1px)`,
          backgroundSize: "80px 80px",
        }}
      />

      {/* Top bar */}
      <header className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-4 sm:px-6 md:px-10 py-4 sm:py-5">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="flex items-center gap-3"
        >
          <div className="w-9 h-9 rounded-lg bg-accent/15 border border-accent/25 flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-accent" />
          </div>
          <span className="font-display font-bold text-lg tracking-tight">SONNET</span>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="flex items-center gap-3"
        >
          <button
            onClick={toggleSound}
            className="w-9 h-9 rounded-lg border border-[hsl(0,0%,20%)] flex items-center justify-center hover:bg-[hsl(0,0%,10%)] transition-colors"
          >
            {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
          </button>
        </motion.div>
      </header>

      {/* Hero */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-10 min-h-screen flex flex-col items-center justify-center px-6 text-center"
      >
        <motion.div variants={itemVariants} className="mb-6">
          <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[hsl(0,0%,18%)] bg-[hsl(0,0%,8%)] text-xs font-mono uppercase tracking-widest text-[hsl(0,0%,55%)]">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            AI-Powered Scholarship Discovery
          </span>
        </motion.div>

        <motion.h1
          variants={itemVariants}
          className="text-[clamp(2.2rem,8vw,8rem)] font-display font-bold leading-[0.9] tracking-[-0.04em] max-w-5xl"
        >
          Find Your
          <br />
          <span className="text-gradient-accent">Perfect</span>{" "}
          Scholarship
        </motion.h1>

        <motion.p
          variants={itemVariants}
          className="mt-4 sm:mt-6 text-sm sm:text-base md:text-lg font-body max-w-xl leading-relaxed text-[hsl(0,0%,55%)] px-4 sm:px-0"
        >
          Sonnet AI uses your profile to find tailored scholarship matches,
          re-ranks results with on-device intelligence, and keeps your data
          safe with secure authentication.
        </motion.p>

        <motion.div variants={itemVariants} className="mt-10">
          <Button
            size="lg"
            onClick={() => navigate(user ? "/profile" : "/auth")}
            className="relative bg-accent text-accent-foreground hover:bg-accent/90 font-display font-semibold text-sm uppercase tracking-wider px-10 py-7 rounded-xl group overflow-hidden"
          >
            <span className="relative flex items-center gap-2.5">
              {user ? "Go to Profile" : "Get Started"}
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </span>
          </Button>
        </motion.div>

        {/* Features */}
        <motion.div
          variants={itemVariants}
          className="mt-16 sm:mt-28 grid grid-cols-1 md:grid-cols-3 gap-px max-w-4xl w-full rounded-xl overflow-hidden border border-[hsl(0,0%,14%)]"
        >
          {FEATURES.map((f) => (
            <motion.div
              key={f.tag}
              whileHover={{ backgroundColor: "hsl(0 0% 8%)" }}
              className="p-6 md:p-8 bg-[hsl(0,0%,5%)] transition-colors"
            >
              <span className="text-[10px] font-mono font-semibold uppercase tracking-[0.2em] text-accent mb-3 block">
                {f.tag}
              </span>
              <p className="text-sm font-body leading-relaxed text-[hsl(0,0%,55%)]">
                {f.text}
              </p>
            </motion.div>
          ))}
        </motion.div>

        {/* Footer */}
        <motion.p
          variants={itemVariants}
          className="mt-16 mb-8 text-xs font-mono uppercase tracking-widest text-[hsl(0,0%,30%)]"
        >
          Gemini AI · TensorFlow.js · Supabase Auth
        </motion.p>
      </motion.div>
    </div>
  );
};

export default Landing;
