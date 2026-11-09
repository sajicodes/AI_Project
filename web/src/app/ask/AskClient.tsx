"use client";

import Image from "next/image";
import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState, useTransition } from "react";
import {
  AcademicLevel,
  AskResponse,
  CAPTION,
  SAMPLE_QUESTIONS,
  SourceCard,
  askQuestion,
  validateIdentity,
} from "@/lib/api";
import {
  StudentSession,
  clearSession,
  loadSession,
  markGreeted,
  saveSession,
} from "@/lib/session";
import styles from "./ask.module.css";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: string;
  sources?: SourceCard[];
};

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function SourcesList({ sources }: { sources: SourceCard[] }) {
  if (!sources.length) {
    return <p className={styles.hint}>No retrieved passages to display.</p>;
  }
  return (
    <div className={styles.sourcesPane}>
      <p className={styles.sourcesTitle}>Sources &amp; evidence</p>
      {sources.map((src, idx) => {
        const scoreBit =
          typeof src.score === "number" ? ` · Relevance ${src.score.toFixed(2)}` : "";
        return (
          <article className={styles.sourceCard} key={`${src.chunk_id || src.title}-${idx}`}>
            <h4>{src.title || "Untitled source"}</h4>
            <p className={styles.sourceMeta}>
              {src.location || "—"} · Level: {src.level || "—"} · Year:{" "}
              {src.year || "—"}
              {scoreBit}
              {src.url ? (
                <>
                  {" · "}
                  <a href={src.url} target="_blank" rel="noopener noreferrer">
                    Open source
                  </a>
                </>
              ) : null}
            </p>
            {src.excerpt ? <p className={styles.sourceExcerpt}>{src.excerpt}</p> : null}
          </article>
        );
      })}
    </div>
  );
}

function StatusLabel({ status }: { status?: string }) {
  if (!status || status === "conversational") return null;
  if (status === "answered" || status === "greeting") {
    return (
      <p className={styles.statusOk}>
        {status === "greeting" ? "Welcome" : "From the catalogs"}
      </p>
    );
  }
  if (status === "abstained") {
    return (
      <p className={styles.statusAbstain}>I couldn&apos;t find this in the catalogs</p>
    );
  }
  if (status === "error") {
    return <p className={styles.statusErr}>Generation error</p>;
  }
  return null;
}

export default function AskClient() {
  const [ready, setReady] = useState(false);
  const [session, setSession] = useState<StudentSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [level, setLevel] = useState<AcademicLevel>("all");
  const [draft, setDraft] = useState("");
  const [fullName, setFullName] = useState("");
  const [ucmId, setUcmId] = useState("");
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    const existing = loadSession();
    setSession(existing);
    if (existing && !existing.greeted) {
      const greeting = `Hi ${existing.firstName}! How can I help with a UCM catalog or policy question today?`;
      setMessages([
        {
          id: uid(),
          role: "assistant",
          content: greeting,
          status: "greeting",
          sources: [],
        },
      ]);
      setSession(markGreeted(existing));
    }
    setReady(true);
  }, []);

  const onlyGreeting = useMemo(
    () =>
      messages.length === 1 &&
      messages[0]?.role === "assistant" &&
      messages[0]?.status === "greeting",
    [messages],
  );

  const showEmpty = ready && session && (messages.length === 0 || onlyGreeting);

  async function onCheckIn(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFormErrors({});
    try {
      const result = await validateIdentity(fullName, ucmId);
      if (!result.ok) {
        setFormErrors(result.errors || {});
        return;
      }
      const next: StudentSession = {
        fullName: result.full_name || fullName.trim(),
        firstName: result.first_name || "there",
        maskedId: result.masked_id || "••••",
        greeted: true,
      };
      saveSession(next);
      setSession(next);
      setMessages([
        {
          id: uid(),
          role: "assistant",
          content:
            result.greeting ||
            `Hi ${next.firstName}! How can I help with a UCM catalog or policy question today?`,
          status: "greeting",
          sources: [],
        },
      ]);
    } catch (err) {
      setFormErrors({
        form:
          err instanceof Error
            ? err.message
            : "Could not reach CampusAsk API. Is the API running?",
      });
    } finally {
      setBusy(false);
    }
  }

  async function sendPrompt(prompt: string) {
    const cleaned = prompt.trim();
    if (!cleaned || !session || busy) return;
    setBusy(true);
    setDraft("");
    const userMsg: ChatMessage = { id: uid(), role: "user", content: cleaned };
    setMessages((prev) => [...prev, userMsg]);
    try {
      const result: AskResponse = await askQuestion({
        question: cleaned,
        academicLevel: level,
        firstName: session.firstName,
      });
      const assistant: ChatMessage = {
        id: uid(),
        role: "assistant",
        content: result.answer,
        status: result.status,
        sources: result.status === "conversational" ? [] : result.sources || [],
      };
      startTransition(() => {
        setMessages((prev) => [...prev, assistant]);
      });
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          content:
            err instanceof Error
              ? err.message
              : "CampusAsk could not reach the API.",
          status: "error",
          sources: [],
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function onSubmitComposer(e: FormEvent) {
    e.preventDefault();
    void sendPrompt(draft);
  }

  function onNewConversation() {
    setMessages([]);
  }

  function onSwitchStudent() {
    clearSession();
    setSession(null);
    setMessages([]);
    setFullName("");
    setUcmId("");
    setFormErrors({});
  }

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.lockup}>
          <Image
            className={styles.sideLogo}
            src="/ucm/ucm-logo.webp"
            alt="University of Central Missouri"
            width={210}
            height={110}
            priority
          />
          <div>
            <p className={styles.sideBrand}>CampusAsk</p>
            <p className={styles.sideMules}>Academic Catalog Desk</p>
            <p className={styles.sideTag}>{CAPTION}</p>
          </div>
        </div>

        {session ? (
          <div className={styles.chip}>
            <p className={styles.chipLabel}>Signed in</p>
            <p className={styles.chipName}>{session.fullName}</p>
            <p className={styles.chipId}>UCM ID {session.maskedId}</p>
          </div>
        ) : null}

        <div>
          <label className={styles.fieldLabel} htmlFor="academic-level">
            Academic level
          </label>
          <select
            id="academic-level"
            className={styles.select}
            value={level}
            onChange={(e) => setLevel(e.target.value as AcademicLevel)}
            disabled={!session}
          >
            <option value="all">All</option>
            <option value="undergraduate">Undergraduate</option>
            <option value="graduate">Graduate</option>
          </select>
        </div>

        <div className={styles.sideActions}>
          <button
            type="button"
            className={styles.ghostBtn}
            onClick={onNewConversation}
            disabled={!session}
          >
            New conversation
          </button>
          {session ? (
            <button type="button" className={styles.secondaryBtn} onClick={onSwitchStudent}>
              Switch student
            </button>
          ) : null}
          <Link className={styles.ghostBtn} href="/" style={{ textAlign: "center", lineHeight: "2.6rem" }}>
            Back to home
          </Link>
        </div>
      </aside>

      <section className={styles.main}>
        <header className={styles.topbar}>
          <Image
            className={styles.askLogo}
            src="/ucm/ucm-logo.webp"
            alt="University of Central Missouri"
            width={220}
            height={115}
            priority
          />
          <div className={styles.brandBlock}>
            <p className={styles.askUni}>Academic Catalog Desk</p>
            <p className={styles.askTitle}>CampusAsk</p>
            <p className={styles.askTag}>{CAPTION}</p>
          </div>
        </header>

        <div className={styles.content}>
          {!ready ? <p className={styles.hint}>Loading…</p> : null}

          {ready && !session ? (
            <div className={styles.identityPanel}>
              <p className={styles.identityEyebrow}>Academic Catalog Desk</p>
              <h2 className={styles.identityTitle}>Student check-in</h2>
              <p className={styles.identityCopy}>
                Enter your name and UCM ID to start. Your ID stays in this browser
                session only—it is never sent to the language model.
              </p>
              <form className={styles.form} onSubmit={onCheckIn}>
                <div>
                  <label className={styles.inputLabel} htmlFor="full-name">
                    Full name
                  </label>
                  <input
                    id="full-name"
                    className={styles.input}
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Alex Rivera"
                    maxLength={80}
                    autoComplete="name"
                    required
                  />
                  {formErrors.full_name ? (
                    <p className={styles.error}>{formErrors.full_name}</p>
                  ) : null}
                </div>
                <div>
                  <label className={styles.inputLabel} htmlFor="ucm-id">
                    UCM ID number
                  </label>
                  <input
                    id="ucm-id"
                    className={styles.input}
                    value={ucmId}
                    onChange={(e) => setUcmId(e.target.value)}
                    placeholder="e.g. 700782694"
                    maxLength={12}
                    inputMode="numeric"
                    autoComplete="off"
                    required
                  />
                  {formErrors.ucm_id ? (
                    <p className={styles.error}>{formErrors.ucm_id}</p>
                  ) : null}
                </div>
                {formErrors.form ? <p className={styles.error}>{formErrors.form}</p> : null}
                <button className={styles.primaryBtn} type="submit" disabled={busy}>
                  {busy ? "Checking…" : "Continue to CampusAsk"}
                </button>
              </form>
              <p className={styles.hint} style={{ marginTop: "1rem" }}>
                Ask is locked until student check-in is complete.
              </p>
            </div>
          ) : null}

          {session ? (
            <>
              {showEmpty ? (
                <>
                  {onlyGreeting ? (
                    <div className={styles.thread}>
                      {messages.map((m) => (
                        <div
                          key={m.id}
                          className={`${styles.row} ${styles.rowAssistant}`}
                        >
                          <div className={`${styles.bubble} ${styles.bubbleAssistant}`}>
                            <StatusLabel status={m.status} />
                            {m.content}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className={styles.empty}>
                      <Image
                        className={styles.emptyMo}
                        src="/ucm/mo-the-mule.webp"
                        alt="Mo the Mule studying in the library"
                        width={480}
                        height={319}
                        priority
                      />
                      <div>
                        <p className={styles.emptyTitle}>Ask CampusAsk</p>
                        <p className={styles.emptyText}>{CAPTION}</p>
                        <p className={styles.emptyHint}>
                          Catalog answers with citations—or a clear abstention when
                          evidence is missing.
                        </p>
                      </div>
                    </div>
                  )}
                  <div>
                    <p className={styles.chipLabel}>Try a catalog question</p>
                    <div className={styles.chips}>
                      {SAMPLE_QUESTIONS.map((sample) => (
                        <button
                          key={sample.id}
                          type="button"
                          className={styles.chipBtn}
                          disabled={busy}
                          onClick={() => void sendPrompt(sample.question)}
                        >
                          {sample.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                <div className={styles.thread}>
                  {messages.map((m) => {
                    if (m.role === "user") {
                      return (
                        <div key={m.id} className={`${styles.row} ${styles.rowUser}`}>
                          <div className={`${styles.bubble} ${styles.bubbleUser}`}>
                            {m.content}
                          </div>
                        </div>
                      );
                    }
                    const withSources =
                      (m.sources?.length ?? 0) > 0 && m.status !== "conversational";
                    if (withSources) {
                      return (
                        <div key={m.id} className={styles.layoutAnswer}>
                          <div className={`${styles.bubble} ${styles.bubbleAssistant}`}>
                            <StatusLabel status={m.status} />
                            {m.content}
                          </div>
                          <SourcesList sources={m.sources || []} />
                        </div>
                      );
                    }
                    return (
                      <div
                        key={m.id}
                        className={`${styles.row} ${styles.rowAssistant}`}
                      >
                        <div className={`${styles.bubble} ${styles.bubbleAssistant}`}>
                          <StatusLabel status={m.status} />
                          {m.content}
                        </div>
                      </div>
                    );
                  })}
                  {(busy || pending) && (
                    <p className={styles.hint}>
                      Searching catalogs and drafting a grounded answer…
                    </p>
                  )}
                </div>
              )}

              <form className={styles.composer} onSubmit={onSubmitComposer}>
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="Ask a UCM policy question…"
                  disabled={busy}
                  aria-label="Ask a UCM policy question"
                />
                <button className={styles.sendBtn} type="submit" disabled={busy || !draft.trim()}>
                  Send
                </button>
              </form>
            </>
          ) : null}
        </div>
      </section>
    </div>
  );
}
