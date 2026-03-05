import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Sparkles, ExternalLink, DollarSign, Calendar, Loader2, FileText, AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { supabase } from "@/integrations/supabase/client";
import { reRankScholarships, type Scholarship } from "@/lib/tf-rerank";
import AppLayout from "@/components/AppLayout";

const Scholarships = () => {
  const [scholarships, setScholarships] = useState<Scholarship[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const navigate = useNavigate();

  const fetchScholarships = async () => {
    setIsLoading(true);
    setErrorMsg("");
    setScholarships([]);

    try {
      const { data: profileData, error: profileError } = await supabase.functions.invoke("manage-profile", {
        body: { action: "get" },
      });
      if (profileError) throw new Error(profileError.message);
      const profile = profileData?.profile;
      if (!profile) throw new Error("No profile found. Please fill out your profile first.");

      const { data: aiData, error: aiError } = await supabase.functions.invoke("match-scholarships", {
        body: { profile },
      });
      if (aiError) throw new Error(aiError.message);
      if (aiData?.error) throw new Error(aiData.error);

      const rawScholarships: Scholarship[] = aiData?.scholarships || [];
      if (rawScholarships.length === 0) throw new Error("No scholarships found. Try updating your profile.");

      const profileText = [
        profile.full_name, profile.field_of_study, profile.education_level,
        profile.institution_name, profile.interests, profile.country,
        profile.category ? `Category: ${profile.category}` : "",
        profile.financial_need ? `Financial need: ${profile.financial_need}` : "",
        profile.annual_income ? `Annual income: $${profile.annual_income}` : "",
      ].filter(Boolean).join(". ");

      const ranked = await reRankScholarships(profileText, rawScholarships);
      setScholarships(ranked);
    } catch (err: any) {
      console.error("Scholarship matching error:", err);
      setErrorMsg(err.message || "An unknown error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchScholarships(); }, []);

  const getScoreBadge = (score: number) => {
    if (score >= 90) return "bg-accent/15 text-accent";
    if (score >= 80) return "bg-[hsl(45,80%,50%)]/15 text-[hsl(45,80%,45%)]";
    if (score >= 70) return "bg-[hsl(200,60%,50%)]/15 text-[hsl(200,60%,50%)]";
    return "bg-muted text-muted-foreground";
  };

  const isDeadlineSoon = (d: string) => {
    const diff = Math.ceil((new Date(d).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    return diff <= 30 && diff > 0;
  };
  const isDeadlinePassed = (d: string) => new Date(d) < new Date();

  return (
    <AppLayout>
      <div className="py-8 px-4 sm:px-8 lg:px-12">
        <div className="max-w-3xl mx-auto">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8 flex items-start justify-between">
            <div>
              <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-muted-foreground mb-2">Step 2 of 2</p>
              <h1 className="text-2xl font-display font-bold tracking-tight">Your Matches</h1>
              <p className="text-sm text-muted-foreground font-body mt-1">Scholarships found & ranked by AI</p>
            </div>
            {!isLoading && !errorMsg && (
              <Button variant="outline" size="sm" onClick={fetchScholarships} className="rounded-lg font-body gap-2 text-xs">
                <RefreshCw className="w-3.5 h-3.5" /> Refresh
              </Button>
            )}
          </motion.div>

          <AnimatePresence>
            {isLoading && !errorMsg && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-card rounded-xl p-16 shadow-card border border-border flex flex-col items-center justify-center text-center"
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  className="w-14 h-14 rounded-xl bg-accent/10 flex items-center justify-center mb-6"
                >
                  <Sparkles className="w-7 h-7 text-accent" />
                </motion.div>
                <p className="text-base font-display font-semibold mb-1">Finding Best Scholarships for You</p>
                <p className="text-xs text-muted-foreground font-body">This may take a moment...</p>
                <motion.div className="mt-6 h-0.5 w-40 bg-muted rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-accent rounded-full"
                    animate={{ x: ["-100%", "100%"] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                    style={{ width: "50%" }}
                  />
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>

          {errorMsg && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-destructive/5 border border-destructive/20 rounded-xl p-6 text-center">
              <p className="text-destructive font-body font-medium mb-1 text-sm">Matching failed</p>
              <p className="text-destructive/70 font-body text-xs mb-4">{errorMsg}</p>
              <Button variant="outline" size="sm" onClick={() => navigate("/profile")} className="rounded-lg font-body text-xs">
                Update Profile & Retry
              </Button>
            </motion.div>
          )}

          {!isLoading && !errorMsg && (
            <div className="space-y-3">
              {scholarships.map((s, i) => (
                <motion.div
                  key={`${s.name}-${i}`}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06, duration: 0.4 }}
                  whileHover={{ y: -1 }}
                  className="bg-card rounded-xl p-5 shadow-card border border-border hover:shadow-elevated hover:border-accent/20 transition-all duration-300"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
                        <h3 className="text-base font-display font-semibold tracking-tight">{s.name}</h3>
                        <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md ${getScoreBadge(s.final_score ?? s.match_score)}`}>
                          {s.final_score ?? s.match_score}%
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground font-body mb-2">{s.provider}</p>
                      <p className="text-sm text-foreground/80 font-body leading-relaxed mb-3">{s.description}</p>

                      {s.match_reasons && s.match_reasons.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mb-3">
                          {s.match_reasons.map((r, ri) => (
                            <span key={ri} className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-accent/8 text-accent-foreground border border-accent/10">
                              {r}
                            </span>
                          ))}
                        </div>
                      )}

                      {s.documents_required && s.documents_required.length > 0 && (
                        <div className="bg-muted/30 rounded-lg p-3 mb-3">
                          <div className="flex items-center gap-1.5 mb-1.5">
                            <FileText className="w-3 h-3 text-muted-foreground" />
                            <span className="text-[10px] font-mono font-medium text-muted-foreground uppercase tracking-wider">Documents</span>
                          </div>
                          <ul className="text-xs font-body text-foreground/60 space-y-0.5">
                            {s.documents_required.map((doc, di) => (
                              <li key={di} className="flex items-center gap-1.5">
                                <span className="w-1 h-1 rounded-full bg-accent/50 shrink-0" />
                                {doc}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div className="flex flex-wrap gap-4 text-xs font-body text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <DollarSign className="w-3.5 h-3.5" />{s.amount}
                        </span>
                        <span className={`flex items-center gap-1 ${isDeadlinePassed(s.deadline) ? "text-destructive" : isDeadlineSoon(s.deadline) ? "text-[hsl(45,80%,45%)]" : ""}`}>
                          <Calendar className="w-3.5 h-3.5" />
                          {new Date(s.deadline).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                          {isDeadlinePassed(s.deadline) && <span className="text-[10px] font-mono font-semibold ml-1">EXPIRED</span>}
                          {isDeadlineSoon(s.deadline) && !isDeadlinePassed(s.deadline) && (
                            <span className="flex items-center gap-0.5 text-[10px] font-mono font-semibold ml-1">
                              <AlertTriangle className="w-3 h-3" /> SOON
                            </span>
                          )}
                        </span>
                      </div>
                    </div>
                    {s.url && (
                      <Button variant="outline" size="sm" className="rounded-lg font-body text-xs shrink-0 gap-1.5" asChild>
                        <a href={s.url} target="_blank" rel="noopener noreferrer">
                          Apply <ExternalLink className="w-3 h-3" />
                        </a>
                      </Button>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
};

export default Scholarships;
