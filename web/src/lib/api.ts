/** CampusAsk API client. Point at Railway/Render/Fly via NEXT_PUBLIC_API_URL. */

export type AcademicLevel = "all" | "undergraduate" | "graduate";

export type SourceCard = {
  title?: string;
  location?: string;
  url?: string;
  excerpt?: string;
  level?: string;
  year?: string;
  score?: number;
  chunk_id?: string;
};

export type AskResponse = {
  status: "answered" | "abstained" | "conversational" | "error" | string;
  answer: string;
  sources: SourceCard[];
  cited_ids: string[];
  invalid_citation_ids: string[];
  max_score: number | null;
  error: string | null;
  intent: string | null;
  suggested_academic_level?: "undergraduate" | "graduate" | null;
  /** Optional alias some API builds may return for the synced level dropdown. */
  academic_level?: "undergraduate" | "graduate" | "all" | null;
};

export type IdentityResponse = {
  ok: boolean;
  full_name: string | null;
  first_name: string | null;
  masked_id: string | null;
  greeting: string | null;
  errors: Record<string, string>;
};

export type SampleQuestion = {
  id: string;
  label: string;
  question: string;
};

export const SAMPLE_QUESTIONS: SampleQuestion[] = [
  {
    id: "thesis",
    label: "Thesis vs non-thesis",
    question:
      "What is the difference between a thesis and non-thesis master's option?",
  },
  {
    id: "probation",
    label: "Academic probation GPA",
    question:
      "What GPA places an undergraduate student on academic probation?",
  },
  {
    id: "credits",
    label: "Full-time credit hours",
    question:
      "How many credit hours are required for full-time graduate enrollment?",
  },
];

export const CAPTION =
  "Official UCM policy answers, grounded in the catalogs.";

function apiBase(): string {
  const raw = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").trim();
  return raw.replace(/\/$/, "");
}

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`API returned non-JSON (${res.status})`);
  }
  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return data as T;
}

export async function validateIdentity(
  fullName: string,
  ucmId: string,
): Promise<IdentityResponse> {
  const res = await fetch(`${apiBase()}/v1/identity/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ full_name: fullName, ucm_id: ucmId }),
  });
  return parseJson<IdentityResponse>(res);
}

export async function askQuestion(input: {
  question: string;
  academicLevel: AcademicLevel;
  firstName?: string | null;
}): Promise<AskResponse> {
  const res = await fetch(`${apiBase()}/v1/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: input.question,
      academic_level: input.academicLevel,
      first_name: input.firstName || undefined,
    }),
  });
  return parseJson<AskResponse>(res);
}

export async function checkHealth(): Promise<{
  status: string;
  index_loaded?: boolean;
  llm_configured?: boolean;
}> {
  const res = await fetch(`${apiBase()}/health`, { cache: "no-store" });
  return parseJson(res);
}
