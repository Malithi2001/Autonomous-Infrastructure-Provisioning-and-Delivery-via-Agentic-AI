import { useState } from "react";
import {
  Bot,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  User,
  Wrench,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import clsx from "clsx";
import { format } from "date-fns";
import type { Message } from "@/types";

export function MessageBubble({ msg }: { msg: Message }) {
  const [stepsOpen, setStepsOpen] = useState(false);
  const isAssistant = msg.role === "assistant";

  return (
    <div
      className={clsx(
        "flex gap-3 animate-slide-up",
        isAssistant ? "items-start" : "items-start flex-row-reverse",
      )}
    >
      <div
        className={clsx(
          "mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border shadow-sm",
          isAssistant
            ? "border-primary-500/30 bg-primary-500/10"
            : "border-surface-500 bg-surface-700",
        )}
      >
        {isAssistant ? (
          <Bot size={17} className="text-primary-500 dark:text-primary-300" />
        ) : (
          <User size={17} className="text-ink-muted" />
        )}
      </div>
      <div
        className={clsx(
          "flex max-w-[82%] flex-1 flex-col",
          !isAssistant && "items-end",
        )}
      >
        <div
          className={clsx(
            "mb-1 flex items-center gap-2 px-1 text-[11px] uppercase tracking-[0.18em] text-ink-subtle",
            !isAssistant && "flex-row-reverse",
          )}
        >
          <span>{isAssistant ? "Assistant" : "You"}</span>
          <span className="h-1 w-1 rounded-full bg-surface-500" />
          <time title={format(msg.timestamp, "PPpp")}>
            {format(msg.timestamp, "HH:mm")}
          </time>
        </div>
        <div
          className={clsx(
            "rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-panel",
            isAssistant
              ? "border border-surface-600/80 bg-surface-800/95 text-ink"
              : "bg-primary-600 text-white shadow-primary-950/20",
            msg.error &&
              "border-red-500/50 bg-red-500/10 text-red-700 dark:text-red-100",
          )}
        >
          {isAssistant ? (
            msg.content ? (
              <div className="prose max-w-none text-sm dark:prose-invert prose-p:my-2 prose-pre:overflow-x-auto prose-pre:rounded-xl prose-pre:border prose-pre:border-surface-600 prose-pre:bg-surface-900 prose-code:rounded prose-code:bg-surface-700 prose-code:px-1 prose-code:py-0.5 prose-code:text-primary-700 dark:prose-code:text-primary-200">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-ink-muted">
                <span className="h-2 w-2 animate-pulse rounded-full bg-primary-400" />
                <span>Preparing response…</span>
              </div>
            )
          ) : (
            <p className="whitespace-pre-wrap">{msg.content}</p>
          )}
        </div>
        {msg.isStreaming && isAssistant && (
          <div className="mt-2 flex items-center gap-2 px-1 text-xs text-primary-700 dark:text-primary-300">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary-400" />
            Streaming response
          </div>
        )}
        {msg.error && (
          <div className="mt-2 flex items-center gap-1.5 px-1 text-xs text-red-600 dark:text-red-300">
            <CircleAlert size={13} />
            Request failed
          </div>
        )}
        {isAssistant && msg.steps && msg.steps.length > 0 && (
          <div className="mt-3 w-full">
            <button
              onClick={() => setStepsOpen((v) => !v)}
              className="flex items-center gap-1.5 text-xs text-ink-subtle transition-colors hover:text-ink"
            >
              {stepsOpen ? (
                <ChevronDown size={12} />
              ) : (
                <ChevronRight size={12} />
              )}
              <Wrench size={12} />
              {msg.steps.length} tool call{msg.steps.length > 1 ? "s" : ""}
            </button>
            {stepsOpen && (
              <div className="mt-2 space-y-2">
                {msg.steps.map((step, i) => (
                  <div
                    key={`${step.tool}-${i}`}
                    className="rounded-xl border border-surface-600 bg-surface-900/90 p-3 text-xs font-mono"
                  >
                    <p className="mb-1 text-primary-700 dark:text-primary-300">
                      → {step.tool}
                    </p>
                    <p className="mb-1 break-words text-ink-subtle">
                      Input:{" "}
                      {typeof step.input === "string"
                        ? step.input
                        : JSON.stringify(step.input)}
                    </p>
                    <p className="whitespace-pre-wrap text-ink-muted">
                      {step.output}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
