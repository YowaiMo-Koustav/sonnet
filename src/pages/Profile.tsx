import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { User, BookOpen, GraduationCap, Loader2, Building2, Wallet, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { supabase } from "@/integrations/supabase/client";
import AppLayout from "@/components/AppLayout";

const Profile = () => {
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const navigate = useNavigate();
  const { toast } = useToast();

  const [form, setForm] = useState({
    full_name: "", age: "", education_level: "", field_of_study: "",
    institution_name: "", gpa: "", country: "", interests: "",
    financial_need: "", annual_income: "", category: "",
  });

  useEffect(() => {
    const loadProfile = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;
      const { data, error } = await supabase.functions.invoke("manage-profile", {
        body: { action: "get" },
      });
      setFetching(false);
      if (error) return;
      const p = data?.profile;
      if (p) setForm({
        full_name: p.full_name || "", age: p.age?.toString() || "",
        education_level: p.education_level || "", field_of_study: p.field_of_study || "",
        institution_name: p.institution_name || "", gpa: p.gpa?.toString() || "",
        country: p.country || "", interests: p.interests || "",
        financial_need: p.financial_need || "", annual_income: p.annual_income?.toString() || "",
        category: p.category || "",
      });
    };
    loadProfile();
  }, []);

  const handleSave = async () => {
    if (!form.full_name) return;
    setLoading(true);
    const { error } = await supabase.functions.invoke("manage-profile", {
      body: { action: "upsert", profile: form },
    });
    setLoading(false);
    if (error) {
      toast({ title: "Error", description: error.message, variant: "destructive" });
    } else {
      toast({ title: "Profile saved!" });
      navigate("/scholarships");
    }
  };

  const update = (key: string, value: string) => setForm((prev) => ({ ...prev, [key]: value }));

  const inputClass = "h-11 rounded-lg font-body bg-background border-border focus:ring-accent/30";
  const labelClass = "font-body text-xs uppercase tracking-wider text-muted-foreground font-medium";

  const sections = [
    {
      icon: User, title: "Personal",
      fields: (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label className={labelClass}>Full Name</Label>
            <Input value={form.full_name} onChange={(e) => update("full_name", e.target.value)} className={inputClass} placeholder="Jane Doe" />
          </div>
          <div className="space-y-1.5">
            <Label className={labelClass}>Age</Label>
            <Input type="number" value={form.age} onChange={(e) => update("age", e.target.value)} className={inputClass} placeholder="18" />
          </div>
          <div className="sm:col-span-2 space-y-1.5">
            <Label className={labelClass}>Country</Label>
            <Input value={form.country} onChange={(e) => update("country", e.target.value)} className={inputClass} placeholder="United States" />
          </div>
        </div>
      ),
    },
    {
      icon: Building2, title: "Institution",
      fields: (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2 space-y-1.5">
            <Label className={labelClass}>Institution Name</Label>
            <Input value={form.institution_name} onChange={(e) => update("institution_name", e.target.value)} className={inputClass} placeholder="MIT, Stanford, etc." />
          </div>
          <div className="space-y-1.5">
            <Label className={labelClass}>Education Level</Label>
            <Select value={form.education_level} onValueChange={(v) => update("education_level", v)}>
              <SelectTrigger className={inputClass}><SelectValue placeholder="Select level" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="high_school">High School</SelectItem>
                <SelectItem value="undergraduate">Undergraduate</SelectItem>
                <SelectItem value="graduate">Graduate</SelectItem>
                <SelectItem value="doctorate">Doctorate</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className={labelClass}>GPA</Label>
            <Input type="number" step="0.01" value={form.gpa} onChange={(e) => update("gpa", e.target.value)} className={inputClass} placeholder="3.5" />
          </div>
          <div className="sm:col-span-2 space-y-1.5">
            <Label className={labelClass}>Field of Study</Label>
            <Input value={form.field_of_study} onChange={(e) => update("field_of_study", e.target.value)} className={inputClass} placeholder="Computer Science" />
          </div>
        </div>
      ),
    },
    {
      icon: BookOpen, title: "Category",
      fields: (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label className={labelClass}>Scholarship Category</Label>
            <Select value={form.category} onValueChange={(v) => update("category", v)}>
              <SelectTrigger className={inputClass}><SelectValue placeholder="Select category" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="merit">Merit-Based</SelectItem>
                <SelectItem value="need">Need-Based</SelectItem>
                <SelectItem value="athletic">Athletic</SelectItem>
                <SelectItem value="stem">STEM</SelectItem>
                <SelectItem value="arts">Arts & Humanities</SelectItem>
                <SelectItem value="community">Community Service</SelectItem>
                <SelectItem value="minority">Minority / Underrepresented</SelectItem>
                <SelectItem value="international">International Students</SelectItem>
                <SelectItem value="research">Research</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className={labelClass}>Interests & Activities</Label>
            <Textarea value={form.interests} onChange={(e) => update("interests", e.target.value)} className="rounded-lg font-body min-h-[80px] bg-background border-border" placeholder="Research, community service, athletics..." />
          </div>
        </div>
      ),
    },
    {
      icon: Wallet, title: "Financial",
      fields: (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label className={labelClass}>Financial Need Level</Label>
            <Select value={form.financial_need} onValueChange={(v) => update("financial_need", v)}>
              <SelectTrigger className={inputClass}><SelectValue placeholder="Select level" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="moderate">Moderate</SelectItem>
                <SelectItem value="high">High</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className={labelClass}>Annual Household Income ($)</Label>
            <Input type="number" value={form.annual_income} onChange={(e) => update("annual_income", e.target.value)} className={inputClass} placeholder="45000" />
          </div>
        </div>
      ),
    },
  ];

  if (fetching) {
    return (
      <AppLayout>
        <div className="min-h-[80vh] flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="py-8 px-4 sm:px-8 lg:px-12">
        <div className="max-w-2xl mx-auto">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
            <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-muted-foreground mb-2">Step 1 of 2</p>
            <h1 className="text-2xl font-display font-bold mb-1 tracking-tight">Your Profile</h1>
            <p className="text-sm text-muted-foreground font-body mb-8">Tell us about yourself so our AI can find the best scholarships for you.</p>
          </motion.div>

          <div className="space-y-5">
            {sections.map((section, i) => (
              <motion.div
                key={section.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08 * (i + 1), duration: 0.5 }}
                className="bg-card rounded-xl p-5 shadow-card border border-border"
              >
                <div className="flex items-center gap-2.5 mb-4">
                  <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center">
                    <section.icon className="w-4 h-4 text-accent" />
                  </div>
                  <h2 className="text-sm font-display font-semibold uppercase tracking-wide">{section.title}</h2>
                </div>
                {section.fields}
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className="mt-6 pb-8"
          >
            <Button
              onClick={handleSave}
              disabled={loading || !form.full_name}
              className="w-full h-12 rounded-xl bg-accent text-accent-foreground hover:bg-accent/90 font-display font-semibold text-sm uppercase tracking-wider group"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <span className="flex items-center gap-2">
                  <GraduationCap className="w-4 h-4" />
                  Find My Scholarships
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </span>
              )}
            </Button>
          </motion.div>
        </div>
      </div>
    </AppLayout>
  );
};

export default Profile;
