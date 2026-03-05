import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const LOVABLE_API_KEY = Deno.env.get("LOVABLE_API_KEY");
    if (!LOVABLE_API_KEY) {
      throw new Error("LOVABLE_API_KEY is not configured");
    }

    const { profile } = await req.json();
    if (!profile) {
      return new Response(JSON.stringify({ error: "Missing profile data" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const today = new Date().toISOString().split("T")[0];

    const systemPrompt = `You are an AI scholarship matching engine. Given a student's profile, find and recommend real, currently available scholarships that the student is likely eligible for.

IMPORTANT: Today's date is ${today}. All scholarship deadlines MUST be in the future (after ${today}). Do NOT return scholarships with past deadlines.

Consider all profile attributes:
- Name, age, country of residence
- Institution name
- Education level and field of study
- GPA
- Interests and extracurricular activities
- Financial need level and annual household income
- Preferred scholarship category

For each scholarship, provide:
- A real or realistic scholarship name
- The organization/provider offering it
- Award amount
- Application deadline (MUST be after ${today}, use realistic future dates)
- A match score from 0-100 based on how well the student fits
- A brief description of eligibility and what makes this student a good match
- An application URL if known (or a realistic placeholder)
- 2-3 specific reasons why this scholarship matches the student
- A list of 3-5 documents typically required to apply (e.g., transcripts, recommendation letters, essays, financial statements)

Return 5-8 scholarships, sorted by match score (highest first). Focus on scholarships that genuinely match the student's profile.`;

    const userPrompt = `Find scholarships for this student profile:
- Full Name: ${profile.full_name || "Not provided"}
- Age: ${profile.age || "Not provided"}
- Country: ${profile.country || "Not provided"}
- Institution: ${profile.institution_name || "Not provided"}
- Education Level: ${profile.education_level || "Not provided"}
- Field of Study: ${profile.field_of_study || "Not provided"}
- GPA: ${profile.gpa || "Not provided"}
- Interests & Activities: ${profile.interests || "Not provided"}
- Financial Need: ${profile.financial_need || "Not provided"}
- Annual Household Income: ${profile.annual_income ? "$" + profile.annual_income : "Not provided"}
- Preferred Category: ${profile.category || "Not provided"}`;

    const response = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${LOVABLE_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "google/gemini-3-flash-preview",
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
        tools: [
          {
            type: "function",
            function: {
              name: "return_scholarships",
              description: "Return a list of matched scholarships for the student.",
              parameters: {
                type: "object",
                properties: {
                  scholarships: {
                    type: "array",
                    items: {
                      type: "object",
                      properties: {
                        name: { type: "string", description: "Scholarship name" },
                        provider: { type: "string", description: "Organization offering the scholarship" },
                        amount: { type: "string", description: "Award amount (e.g. $5,000)" },
                        deadline: { type: "string", description: "Application deadline in YYYY-MM-DD format. Must be after today." },
                        match_score: { type: "number", description: "Match score 0-100" },
                        description: { type: "string", description: "Brief description of eligibility and why the student matches" },
                        url: { type: "string", description: "Application URL" },
                        match_reasons: {
                          type: "array",
                          items: { type: "string" },
                          description: "2-3 specific reasons why this scholarship matches the student",
                        },
                        documents_required: {
                          type: "array",
                          items: { type: "string" },
                          description: "3-5 documents typically required to apply (e.g., transcripts, recommendation letters, essays)",
                        },
                      },
                      required: ["name", "provider", "amount", "deadline", "match_score", "description", "match_reasons", "documents_required"],
                      additionalProperties: false,
                    },
                  },
                },
                required: ["scholarships"],
                additionalProperties: false,
              },
            },
          },
        ],
        tool_choice: { type: "function", function: { name: "return_scholarships" } },
      }),
    });

    if (!response.ok) {
      if (response.status === 429) {
        return new Response(JSON.stringify({ error: "Rate limit exceeded. Please try again in a moment." }), {
          status: 429,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      if (response.status === 402) {
        return new Response(JSON.stringify({ error: "AI credits exhausted. Please add funds to continue." }), {
          status: 402,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
      const errorText = await response.text();
      console.error("AI gateway error:", response.status, errorText);
      throw new Error(`AI gateway error: ${response.status}`);
    }

    const data = await response.json();
    const toolCall = data.choices?.[0]?.message?.tool_calls?.[0];

    if (!toolCall) {
      throw new Error("No tool call in AI response");
    }

    const scholarships = JSON.parse(toolCall.function.arguments);

    return new Response(JSON.stringify(scholarships), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("match-scholarships error:", error);
    return new Response(JSON.stringify({ error: error.message || "Unknown error" }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
