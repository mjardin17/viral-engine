import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  BookOpen,
  BookPlus,
  FileDown,
  TrendingUp,
  Users,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  PenLine,
  Package,
  Send,
  Terminal
} from "lucide-react";

const STORYFORGE_BASE_URL =
  (import.meta.env.VITE_STORYFORGE_BASE_URL as string | undefined) ?? "http://localhost:8001";

type HealthStatus = "checking" | "online" | "offline";

interface StoryForgeBook {
  id: string;
  title: string;
  status?: string;
  genre?: string;
  word_count?: number;
}

interface QuickAction {
  title: string;
  description: string;
  method: string;
  endpoint: string;
  icon: typeof BookPlus;
}

interface PipelineStat {
  label: string;
  value: number;
  icon: typeof PenLine;
}

const PIPELINE_STATS: PipelineStat[] = [
  { label: "Books Written", value: 0, icon: PenLine },
  { label: "EPUBs Packaged", value: 0, icon: Package },
  { label: "Distributed", value: 0, icon: Send }
];

interface PipelineCommand {
  command: string;
  description: string;
}

const PIPELINE_COMMANDS: PipelineCommand[] = [
  {
    command: "python book_pipeline.py research",
    description: "Scan 8 profitable niches via Google Books API and find topic gaps"
  },
  {
    command: 'python book_pipeline.py generate --niche "personal finance" --title "..."',
    description: "Write a full 10-chapter book with Gemini (gemini-1.5-pro)"
  },
  {
    command: 'python book_pipeline.py package --title "..."',
    description: "Build an EPUB into renders/books/ with ebooklib"
  },
  {
    command: 'python book_pipeline.py distribute --title "..."',
    description: "Submit to Draft2Digital (40+ stores) + Amazon KDP instructions"
  }
];

const QUICK_ACTIONS: QuickAction[] = [
  {
    title: "New Book",
    description: "Create a new world + book project in StoryForge",
    method: "POST",
    endpoint: "/worlds",
    icon: BookPlus
  },
  {
    title: "Export EPUB",
    description: "Package the active manuscript as an EPUB file",
    method: "POST",
    endpoint: "/book/export/epub",
    icon: FileDown
  },
  {
    title: "Market Research",
    description: "Analyze market fit before publishing",
    method: "POST",
    endpoint: "/publishing/research/analyze",
    icon: TrendingUp
  },
  {
    title: "Council Review",
    description: "Send manuscript to the 14-specialist Creative Council",
    method: "POST",
    endpoint: "/council/review",
    icon: Users
  }
];

function parseBooks(data: unknown): StoryForgeBook[] {
  const list = Array.isArray(data)
    ? data
    : data && typeof data === "object" && Array.isArray((data as { books?: unknown[] }).books)
      ? (data as { books: unknown[] }).books
      : [];
  return list.filter(
    (b): b is StoryForgeBook =>
      !!b && typeof b === "object" && "id" in b && "title" in b
  );
}

export default function BooksPage() {
  const { toast } = useToast();
  const [health, setHealth] = useState<HealthStatus>("checking");
  const [books, setBooks] = useState<StoryForgeBook[]>([]);

  const checkStoryForge = useCallback(async (signal?: AbortSignal) => {
    setHealth("checking");
    try {
      const res = await fetch(`${STORYFORGE_BASE_URL}/empire/health`, { signal });
      if (!res.ok) throw new Error(`Health check returned ${res.status}`);
      setHealth("online");
      try {
        const booksRes = await fetch(`${STORYFORGE_BASE_URL}/books`, { signal });
        if (booksRes.ok) {
          setBooks(parseBooks(await booksRes.json()));
        }
      } catch {
        setBooks([]);
      }
    } catch (error: unknown) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setHealth("offline");
      setBooks([]);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    checkStoryForge(controller.signal);
    return () => controller.abort();
  }, [checkStoryForge]);

  const handleAction = (action: QuickAction) => {
    if (health !== "online") {
      toast({
        title: "StoryForge offline",
        description: `Cannot reach ${STORYFORGE_BASE_URL} — start the Python service first.`,
        variant: "destructive"
      });
      return;
    }
    toast({
      title: action.title,
      description: `Would call ${action.method} ${STORYFORGE_BASE_URL}${action.endpoint}`
    });
  };

  const HealthBadge = () => {
    if (health === "online") {
      return (
        <Badge variant="outline" className="gap-1.5 border-emerald-500/50 text-emerald-400">
          <CheckCircle2 size={12} /> StoryForge Online
        </Badge>
      );
    }
    if (health === "offline") {
      return (
        <Badge variant="outline" className="gap-1.5 border-rose-500/50 text-rose-500">
          <XCircle size={12} /> StoryForge Offline
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="gap-1.5 text-muted-foreground">
        <Clock size={12} /> Checking…
      </Badge>
    );
  };

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center gap-3">
          <BookOpen size={24} className="text-primary" />
          <h1 className="text-2xl font-bold tracking-tight">Books</h1>
          <HealthBadge />
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground font-mono hidden sm:inline">
            {STORYFORGE_BASE_URL}
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => checkStoryForge()}
            data-testid="books-refresh-btn"
          >
            <RefreshCw size={14} className={`mr-2 ${health === "checking" ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Pipeline Status Panel — book_pipeline.py */}
      <div className="rounded-xl border border-border/50 overflow-hidden bg-card/30 backdrop-blur-sm">
        <div className="px-4 py-3 border-b border-border/50 bg-card flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal size={16} className="text-primary" />
            <h2 className="font-semibold text-sm">Pipeline Status</h2>
          </div>
          <span className="text-[10px] text-muted-foreground font-mono">
            book_pipeline.py
          </span>
        </div>

        <div className="p-4 space-y-4">
          {/* Stat cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {PIPELINE_STATS.map(stat => {
              const Icon = stat.icon;
              return (
                <div
                  key={stat.label}
                  className="bg-card/50 border border-border/50 rounded-xl p-4 flex items-center gap-3 hover:bg-card/70 transition-colors"
                  data-testid={`books-pipeline-stat-${stat.label.toLowerCase().replace(/\s+/g, "-")}`}
                >
                  <div className="rounded-lg bg-background border border-border/50 p-2">
                    <Icon size={18} className="text-primary" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-2xl font-bold leading-none">{stat.value}</span>
                    <span className="text-xs text-muted-foreground mt-1">{stat.label}</span>
                  </div>
                </div>
              );
            })}
          </div>
          <p className="text-xs text-muted-foreground">
            Run <span className="font-mono text-foreground">book_pipeline.py status</span> to update
            — or launch <span className="font-mono text-foreground">RUN_BOOK_PIPELINE.bat</span> at the
            repo root for the interactive menu.
          </p>

          {/* Quick Start */}
          <div className="rounded-xl border border-border/50 bg-card/50 p-4 space-y-3">
            <h3 className="font-semibold text-sm">Quick Start</h3>
            <div className="space-y-2">
              {PIPELINE_COMMANDS.map((cmd, index) => (
                <div key={cmd.command} className="flex flex-col gap-1">
                  <div className="font-mono text-[11px] text-foreground bg-background border border-border/50 rounded-md px-2 py-1.5 truncate">
                    {index + 1}. {cmd.command}
                  </div>
                  <span className="text-xs text-muted-foreground pl-1">{cmd.description}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {QUICK_ACTIONS.map(action => {
          const Icon = action.icon;
          return (
            <div
              key={action.endpoint}
              className="bg-card/50 border border-border/50 rounded-xl p-4 flex flex-col gap-3 hover:bg-card/70 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Icon size={18} className="text-primary" />
                <h3 className="font-semibold text-sm">{action.title}</h3>
              </div>
              <p className="text-xs text-muted-foreground flex-1">{action.description}</p>
              <div className="font-mono text-[10px] text-muted-foreground bg-background border border-border/50 rounded-md px-2 py-1.5 truncate">
                {action.method} {action.endpoint}
              </div>
              <Button
                size="sm"
                variant="secondary"
                className="w-full"
                onClick={() => handleAction(action)}
                data-testid={`books-action-${action.title.toLowerCase().replace(/\s+/g, "-")}`}
              >
                Run
              </Button>
            </div>
          );
        })}
      </div>

      {/* Book Projects */}
      <div className="rounded-xl border border-border/50 overflow-hidden bg-card/30 backdrop-blur-sm">
        <div className="px-4 py-3 border-b border-border/50 bg-card">
          <h2 className="font-semibold text-sm">Book Projects ({books.length})</h2>
        </div>

        {books.length > 0 ? (
          <div className="divide-y divide-border/50">
            {books.map(book => (
              <div
                key={book.id}
                className="flex items-center justify-between px-4 py-3 hover:bg-card/50 transition-colors"
              >
                <div className="flex flex-col gap-1 min-w-0">
                  <span className="font-semibold text-sm truncate">{book.title}</span>
                  <span className="font-mono text-xs text-muted-foreground">{book.id}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
                  {book.genre && <span>{book.genre}</span>}
                  {typeof book.word_count === "number" && (
                    <span>{book.word_count.toLocaleString()} words</span>
                  )}
                  <Badge variant="outline" className="text-[10px] uppercase">
                    {book.status ?? "draft"}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="h-32 flex flex-col items-center justify-center gap-2 text-center text-muted-foreground text-sm">
            {health === "offline" ? (
              <>
                <XCircle size={20} className="text-rose-500" />
                <span>StoryForge offline — start the Python service at {STORYFORGE_BASE_URL}</span>
              </>
            ) : health === "checking" ? (
              <>
                <RefreshCw size={20} className="animate-spin" />
                <span>Connecting to StoryForge…</span>
              </>
            ) : (
              <>
                <BookOpen size={20} />
                <span>No book projects yet — hit "New Book" to start one.</span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
