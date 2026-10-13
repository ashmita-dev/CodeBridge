import { BridgeLogo, GithubIcon } from "./icons";

export type ApiHealth = "checking" | "online" | "offline";

const HEALTH_STYLES: Record<ApiHealth, { dot: string; text: string }> = {
  checking: { dot: "bg-fg-faint", text: "Connecting to compiler…" },
  online: { dot: "bg-ok", text: "Compiler online" },
  offline: { dot: "bg-err", text: "Compiler offline" },
};

export function Header({ health }: { health: ApiHealth }) {
  const style = HEALTH_STYLES[health];
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-ink-950/80 px-4 backdrop-blur">
      <BridgeLogo />
      <div className="flex min-w-0 items-baseline gap-3">
        <h1 className="text-[15px] font-semibold tracking-tight text-fg">CodeBridge</h1>
        <p className="hidden truncate text-xs text-fg-muted md:block">
          Pseudocode → C++ compiler · lexer, parser, semantic analysis, three-address code, optimizer and
          code generation, all visible
        </p>
      </div>
      <div className="ml-auto flex items-center gap-3">
        <span className="flex items-center gap-2 text-xs text-fg-muted" role="status" aria-live="polite">
          <span className={`h-2 w-2 rounded-full ${style.dot}`} />
          <span className="hidden sm:inline">{style.text}</span>
        </span>
        <a
          href="https://github.com/ashmita-dev/CodeBridge"
          target="_blank"
          rel="noreferrer"
          className="btn"
          aria-label="CodeBridge on GitHub"
        >
          <GithubIcon />
          <span className="hidden sm:inline">GitHub</span>
        </a>
      </div>
    </header>
  );
}
