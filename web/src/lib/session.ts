/** Browser-session student identity. UCM ID never leaves the browser for LLM calls. */

export type StudentSession = {
  fullName: string;
  firstName: string;
  maskedId: string;
  greeted: boolean;
};

const KEY = "campusask.student.v1";

export function loadSession(): StudentSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StudentSession;
    if (!parsed?.fullName || !parsed?.firstName) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveSession(session: StudentSession): void {
  sessionStorage.setItem(KEY, JSON.stringify(session));
}

export function clearSession(): void {
  sessionStorage.removeItem(KEY);
}

export function markGreeted(session: StudentSession): StudentSession {
  const next = { ...session, greeted: true };
  saveSession(next);
  return next;
}
