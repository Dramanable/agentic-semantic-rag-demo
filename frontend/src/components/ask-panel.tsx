import { Check, Copy, FileSearch, ListTree, Loader2, Send, Square } from "lucide-react";
import { FormEvent, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { EXAMPLE_QUESTIONS } from "@/examples";
import { Confidence, Source, Step, api } from "@/api";
import { cn } from "@/lib/utils";

interface Props {
  busy: boolean;
  hasDocuments: boolean;
  onError: (message: string) => void;
}

interface View {
  question: string;
  steps: Step[];
  sources: Source[];
  text: string;
  grounded: boolean;
  confidence: Confidence | null;
  requestId: string | null;
  state: "streaming" | "done" | "stopped";
}

function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const variant = confidence.level === "high" ? "success" : confidence.level === "medium" ? "warning" : "destructive";
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge variant={variant} className="cursor-help">
          {confidence.level} confidence · {(confidence.score * 100).toFixed(0)}%
        </Badge>
      </TooltipTrigger>
      <TooltipContent>How closely the best source matches your question. It measures retrieval, not truth: always check the sources.</TooltipContent>
    </Tooltip>
  );
}

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    void navigator.clipboard?.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <Button variant="ghost" size="icon" className="size-6" onClick={copy} aria-label="Copy request ID">
      {copied ? <Check /> : <Copy />}
    </Button>
  );
}

export function AskPanel({ busy, hasDocuments, onError }: Props) {
  const [question, setQuestion] = useState("");
  const [view, setView] = useState<View | null>(null);
  const controller = useRef<AbortController | null>(null);
  const streaming = view?.state === "streaming";

  const ask = async (text: string) => {
    controller.current = new AbortController();
    setView({ question: text, steps: [], sources: [], text: "", grounded: true, confidence: null, requestId: null, state: "streaming" });
    const patch = (change: (v: View) => View) => setView((v) => (v ? change(v) : v));
    try {
      await api.askStream(
        text,
        {
          onStep: (step) => patch((v) => ({ ...v, steps: [...v.steps, step] })),
          onSources: (sources) => patch((v) => ({ ...v, sources })),
          onToken: (token) => patch((v) => ({ ...v, text: v.text + token })),
          onDone: (a) =>
            patch((v) => ({ ...v, text: a.answer, grounded: a.grounded, confidence: a.confidence, sources: a.sources, steps: a.steps, requestId: a.request_id, state: "done" })),
        },
        controller.current.signal,
      );
    } catch (e) {
      if ((e as Error).name === "AbortError") patch((v) => ({ ...v, state: "stopped" }));
      else {
        onError((e as Error).message);
        setView(null);
      }
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (question.trim()) void ask(question);
  };

  const lastStep = view?.steps[view.steps.length - 1];

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Ask your documents</CardTitle>
          <CardDescription>Answers are built only from your documents, with their sources.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <form onSubmit={submit} className="flex gap-2">
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={hasDocuments ? "Ask a question…" : "Add a document first"}
              maxLength={1000}
              disabled={!hasDocuments}
              aria-label="Your question"
              className="h-11"
            />
            {streaming ? (
              <Button type="button" variant="outline" size="lg" className="px-5" onClick={() => controller.current?.abort()}>
                <Square /> Stop
              </Button>
            ) : (
              <Button type="submit" size="lg" className="px-5" disabled={busy || !hasDocuments || !question.trim()}>
                <Send /> Ask
              </Button>
            )}
          </form>
          {hasDocuments && !view && (
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUESTIONS.map((example) => (
                <button
                  key={example}
                  type="button"
                  className="rounded-full border bg-background px-3 py-1.5 text-left text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                  onClick={() => {
                    setQuestion(example);
                    void ask(example);
                  }}
                >
                  {example}
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {view && (
        <Card aria-live="polite">
          <CardHeader className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardDescription className="font-medium text-foreground">{view.question}</CardDescription>
              {view.confidence && view.confidence.level !== "none" && <ConfidenceBadge confidence={view.confidence} />}
              {view.state === "done" && !view.grounded && <Badge variant="warning">No relevant source</Badge>}
              {view.state === "stopped" && <Badge variant="secondary">Stopped</Badge>}
            </div>
          </CardHeader>
          <CardContent className="grid gap-4">
            {streaming && view.text === "" ? (
              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                {lastStep ? lastStep.detail : "Searching your documents…"}
              </p>
            ) : (
              <p className={cn("whitespace-pre-wrap rounded-lg border-l-4 bg-muted/40 px-4 py-3 text-sm leading-relaxed", view.grounded ? "border-success" : "border-warning")}>
                {view.text}
                {streaming && <span className="caret ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 bg-foreground" aria-hidden="true" />}
              </p>
            )}

            <Tabs defaultValue="sources">
              <TabsList>
                <TabsTrigger value="sources">
                  <FileSearch className="size-4" /> Sources
                  <Badge variant="secondary" className="px-1.5">
                    {view.sources.length}
                  </Badge>
                </TabsTrigger>
                <TabsTrigger value="trace">
                  <ListTree className="size-4" /> Reasoning
                  <Badge variant="secondary" className="px-1.5">
                    {view.steps.length}
                  </Badge>
                </TabsTrigger>
              </TabsList>

              <TabsContent value="sources" className="grid gap-3">
                {view.sources.length === 0 ? (
                  <p className="text-sm text-muted-foreground">{streaming ? "Looking for relevant passages…" : "No passage was relevant enough to cite."}</p>
                ) : (
                  view.sources.map((s, i) => (
                    <div key={i} className="grid gap-2 rounded-lg border p-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className="truncate text-sm font-medium">{s.source}</span>
                        <span className="shrink-0 text-xs tabular-nums text-muted-foreground">{(s.score * 100).toFixed(0)}% match</span>
                      </div>
                      <Progress value={s.score * 100} />
                      <blockquote className="max-h-40 overflow-auto whitespace-pre-wrap border-l-2 pl-3 text-[13px] leading-relaxed text-muted-foreground">{s.text}</blockquote>
                    </div>
                  ))
                )}
              </TabsContent>

              <TabsContent value="trace">
                <ol className="relative ml-2 grid gap-3 border-l pl-5">
                  {view.steps.map((s, i) => (
                    <li key={i} className="relative">
                      <span className="absolute -left-[26px] top-1.5 size-2 rounded-full bg-primary" />
                      <div className="flex flex-wrap items-baseline gap-x-2">
                        <Badge variant="outline" className="font-mono">
                          {s.name}
                        </Badge>
                        <span className="text-xs tabular-nums text-muted-foreground">{s.duration_ms} ms</span>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{s.detail}</p>
                    </li>
                  ))}
                </ol>
                {view.requestId && (
                  <p className="mt-4 flex items-center gap-1 text-xs text-muted-foreground">
                    Request ID <code className="rounded bg-muted px-1.5 py-0.5">{view.requestId}</code>
                    <CopyButton value={view.requestId} />
                    <span>(also on every API log line)</span>
                  </p>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
