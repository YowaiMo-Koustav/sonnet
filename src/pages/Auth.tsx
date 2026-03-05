import { useState } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { GraduationCap, Mail, Lock, Loader2, Eye, EyeOff, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { supabase } from "@/integrations/supabase/client";

const Auth = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        navigate("/profile", { replace: true });
      } else {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: window.location.origin },
        });
        if (error) throw error;
        toast({
          title: "Account created!",
          description: "Check your email to verify your account, then sign in.",
        });
        setIsLogin(true);
      }
    } catch (err: any) {
      toast({
        title: "Error",
        description: err.message || "Something went wrong",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20, filter: "blur(8px)" },
    visible: {
      opacity: 1, y: 0, filter: "blur(0px)",
      transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] as const },
    },
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[hsl(0,0%,3%)] text-[hsl(0,0%,95%)] flex items-center justify-center px-4">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: `linear-gradient(hsl(0 0% 50%) 1px, transparent 1px), linear-gradient(90deg, hsl(0 0% 50%) 1px, transparent 1px)`,
          backgroundSize: "80px 80px",
        }}
      />

      <motion.div
        initial="hidden"
        animate="visible"
        variants={{ visible: { transition: { staggerChildren: 0.1 } } }}
        className="relative z-10 w-full max-w-sm"
      >
        {/* Logo */}
        <motion.div variants={itemVariants} className="flex items-center justify-center gap-3 mb-10">
          <div className="w-10 h-10 rounded-lg bg-accent/15 border border-accent/25 flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-accent" />
          </div>
          <span className="font-display font-bold text-xl tracking-tight">SONNET</span>
        </motion.div>

        {/* Title */}
        <motion.div variants={itemVariants} className="text-center mb-8">
          <h1 className="text-2xl font-display font-bold tracking-tight mb-1">
            {isLogin ? "Welcome back" : "Create your account"}
          </h1>
          <p className="text-sm text-[hsl(0,0%,55%)] font-body">
            {isLogin ? "Sign in to find your scholarships" : "Start discovering scholarships today"}
          </p>
        </motion.div>

        {/* Form */}
        <motion.form variants={itemVariants} onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label className="text-xs uppercase tracking-wider text-[hsl(0,0%,55%)] font-mono">Email</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(0,0%,40%)]" />
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                className="h-11 pl-10 rounded-lg bg-[hsl(0,0%,7%)] border-[hsl(0,0%,15%)] text-[hsl(0,0%,90%)] placeholder:text-[hsl(0,0%,35%)] focus:border-accent/50 focus:ring-accent/20"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs uppercase tracking-wider text-[hsl(0,0%,55%)] font-mono">Password</Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(0,0%,40%)]" />
              <Input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                placeholder="••••••••"
                className="h-11 pl-10 pr-10 rounded-lg bg-[hsl(0,0%,7%)] border-[hsl(0,0%,15%)] text-[hsl(0,0%,90%)] placeholder:text-[hsl(0,0%,35%)] focus:border-accent/50 focus:ring-accent/20"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[hsl(0,0%,40%)] hover:text-[hsl(0,0%,60%)]"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="w-full h-11 rounded-lg bg-accent text-accent-foreground hover:bg-accent/90 font-display font-semibold text-sm uppercase tracking-wider group"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <span className="flex items-center gap-2">
                {isLogin ? "Sign In" : "Create Account"}
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </span>
            )}
          </Button>
        </motion.form>

        {/* Toggle */}
        <motion.p variants={itemVariants} className="text-center mt-6 text-sm text-[hsl(0,0%,50%)] font-body">
          {isLogin ? "Don't have an account?" : "Already have an account?"}{" "}
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-accent hover:text-accent/80 font-medium transition-colors"
          >
            {isLogin ? "Sign up" : "Sign in"}
          </button>
        </motion.p>
      </motion.div>
    </div>
  );
};

export default Auth;
