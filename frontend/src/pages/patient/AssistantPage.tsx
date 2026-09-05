import { useEffect, useRef, useState, type FormEvent } from "react";
import { Card } from "@/components/ui/Card";
import { useAsyncData } from "@/hooks/useAsyncData";
import { patientApi } from "@/services/patientApi";
import { assistantApi } from "@/services/assistantApi";
import type { AssistantMessage } from "@/types/assistant";

const SUGGESTED_QUESTIONS = [
  "What does my blood pressure mean?",
  "Why did my risk increase?",
  "What is my current health status?",
  "What factors are affecting my prediction?",
];

/**
 * The AI Health Assistant chat — explains the patient's own ML
 * predictions, trends, and vitals in plain language (see
 * app/services/assistant_service.py for the backend's hard rules: no
 * diagnosis, no medication advice, no invented data). This is what
 * replaced patient<->doctor messaging when the doctor role was removed.
 */
export function AssistantPage() {
  const { data: profile, error: profileError } = useAsyncData(() => patientApi.getMe(), []);
  const { data: history, isLoading: historyLoading, refetch } = useAsyncData(
    () => (profile ? assistantApi.listMessages(profile.id) : Promise.resolve([])),
    [profile?.id]
  );

  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (history) setMessages(history);
  }, [history]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function handleSend(e: FormEvent, overrideText?: string) {
    e.preventDefault();
    const content = (overrideText ?? input).trim();
    if (!content || !profile || isSending) return;

    setError(null);
    setInput("");
    setIsSending(true);

    // Optimistic bubble for the user's own message — replaced with the
    // server's canonical history (correct ids/timestamps) once the
    // request settles, whether it succeeds or fails, since the backend
    // persists the user's message even if the AI reply itself fails.
    setMessages((prev) => [
      ...prev,
      {
        id: `optimistic-${Date.now()}`,
        patient_id: profile.id,
        role: "user",
        content,
        is_emergency_override: false,
        created_at: new Date().toISOString(),
      },
    ]);

    try {
      await assistantApi.sendMessage(profile.id, content);
      refetch();
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      setError(
        status === 503
          ? "The AI Health Assistant isn't available right now. Please try again shortly."
          : "Couldn't send that message. Please try again."
      );
      refetch();
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div>
      <h1 className="font-display text-xl font-bold text-ink">AI Health Assistant</h1>
      <p className="mt-1 text-sm text-ink-soft">
        Ask about your vitals, trends, or risk predictions. This explains your own data — it isn't a diagnosis
        and isn't a substitute for professional medical care.
      </p>

      {profileError && (
        <p className="mt-4 rounded-lg bg-status-critical/10 px-3 py-2 text-sm text-status-critical">
          Couldn't load your profile, so the assistant can't access your data right now. Try refreshing
          the page.
        </p>
      )}

      <Card className="mt-6 flex h-[60vh] flex-col">
        <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto pr-1">
          {historyLoading ? (
            <p className="text-sm text-ink-soft">Loading…</p>
          ) : messages.length === 0 ? (
            <div>
              <p className="text-sm text-ink-soft">Ask me anything about your health data. For example:</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={(e) => handleSend(e, q)}
                    className="rounded-full border border-surface-border px-3 py-1.5 text-xs text-ink hover:border-teal-500 hover:text-teal-600"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
                    message.role === "user"
                      ? "bg-teal-500 text-white"
                      : message.is_emergency_override
                        ? "border border-status-critical bg-status-critical/10 text-ink"
                        : "bg-surface-sunken text-ink"
                  }`}
                >
                  {message.content}
                </div>
              </div>
            ))
          )}
        </div>

        {error && <p className="mt-2 text-sm text-status-critical">{error}</p>}

        <form onSubmit={handleSend} className="mt-4 flex gap-2 border-t border-surface-border pt-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your health data…"
            disabled={isSending}
            className="flex-1 rounded-lg border border-surface-border px-3 py-2 text-sm focus:border-teal-500 disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={isSending || !input.trim()}
            className="rounded-lg bg-teal-500 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-600 disabled:opacity-60"
          >
            {isSending ? "Sending…" : "Send"}
          </button>
        </form>
      </Card>
    </div>
  );
}
