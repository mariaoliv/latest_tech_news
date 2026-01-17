import { useEffect, useMemo, useRef, useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { getNewsSummary } from "./api"

/* ---------- Types ---------- */

type DigestCard = {
  title: string
  body: string
  subcards: string[]
}

/* ---------- Helpers ---------- */

/**
 * Normalize markdown slightly so section-ish lines
 * become actual headers.
 */
function prettifyMarkdown(md: string) {
  if (!md) return md
  let s = md.trim()

  // "**Section:**" -> ### Section
  s = s.replace(/(^|\n)\*\*([^*\n]{3,60})\*\*:\s*/g, "$1### $2\n\n")

  // "Title Case Line:" -> ### Title Case Line
  s = s.replace(
    /(^|\n)([A-Z][A-Za-z0-9 &/'’\-]{4,80}):\s*\n/g,
    "$1### $2\n"
  )

  return s
}

/**
 * Split digest into:
 *  - top-level cards (one per story)
 *  - indented subcards for numbered sections (1., 2., 3.)
 */
function splitIntoDigest(md: string): DigestCard[] {
  const text = md.trim()
  if (!text) return []

  // Prefer real markdown headers
  const blocks = text
    .split(/\n(?=##?\s+)/g)
    .map((b) => b.trim())
    .filter(Boolean)

  const storyBlocks = blocks.length > 1 ? blocks : [text]
  const result: DigestCard[] = []

  for (const block of storyBlocks) {
    const lines = block.split("\n")
    const firstLine = lines[0]?.trim() ?? ""

    const title = firstLine.replace(/^##?\s+/, "").trim()
    const rest = lines.slice(1).join("\n").trim()

    // Split numbered sections INTO subcards
    const parts = rest
      ? rest.split(/\n(?=\d+\.\s+)/g)
      : []

    const body = parts.length ? parts[0].trim() : rest
    const subcards =
      parts.length > 1
        ? parts.slice(1).map((p) => p.trim()).filter(Boolean)
        : []

    result.push({
      title: title || "Top story",
      body,
      subcards,
    })
  }

  return result
}

/* ---------- Component ---------- */

export default function App() {
  const [summary, setSummary] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // StrictMode-safe "fetch once"
  const didFetchRef = useRef(false)

  useEffect(() => {
    if (didFetchRef.current) return
    if (summary !== "") return

    didFetchRef.current = true

    const run = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await getNewsSummary()
        setSummary(data)
      } catch {
        setError("Failed to load tech news summary.")
      } finally {
        setLoading(false)
      }
    }

    run()
  }, [summary])

  const normalized = useMemo(
    () => prettifyMarkdown(summary),
    [summary]
  )

  const digest = useMemo(
    () => splitIntoDigest(normalized),
    [normalized]
  )

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* animated backdrop */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(900px_circle_at_20%_-10%,rgba(99,102,241,0.35),transparent_60%),radial-gradient(900px_circle_at_100%_0%,rgba(236,72,153,0.25),transparent_55%),radial-gradient(900px_circle_at_30%_100%,rgba(34,197,94,0.18),transparent_55%)]" />
        <div className="absolute inset-0 bg-slate-950/70" />
      </div>

      {/* header */}
      <header className="border-b border-white/10 bg-slate-950/40 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-white/10 ring-1 ring-white/15">
              🧃
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold tracking-tight">
                Latest Tech News
              </div>
              <div className="text-xs text-white/60">
                Qclay-ish daily digest
              </div>
            </div>
          </div>

          <button
            onClick={() => window.location.reload()}
            className="rounded-xl bg-white/10 px-3.5 py-2 text-sm font-medium ring-1 ring-white/15 hover:bg-white/15"
          >
            Refresh
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-10">
        {/* hero */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Today’s digest <span className="opacity-90">✨</span>
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-white/70 sm:text-base">
            Skim the highlights. Tap citations when you want receipts.
          </p>
        </div>

        {/* loading */}
        {loading && (
          <div className="grid place-items-center rounded-3xl border border-white/10 bg-white/5 p-10 text-center">
            <div className="mb-3 inline-flex items-center gap-3">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-white/20 border-t-fuchsia-300" />
              <span className="text-lg font-semibold">
                Brewing your digest…
              </span>
            </div>
            <p className="text-sm text-white/70">
              Pulling headlines, summarizing key moves, and adding citations.
            </p>
          </div>
        )}

        {/* error */}
        {error && (
          <div className="rounded-3xl border border-rose-500/20 bg-rose-500/10 p-6 text-rose-100">
            {error}
          </div>
        )}

        {/* digest cards */}
        {!loading && !error && (
          <div className="grid gap-6">
            {digest.map((card, idx) => (
              <div
                key={idx}
                className="relative overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-6"
              >
                {/* accent rail */}
                <div className="absolute left-0 top-0 h-full w-1 bg-linear-to-b from-indigo-400 via-fuchsia-400 to-emerald-300" />

                <h2 className="mb-4 text-xl font-semibold tracking-tight">
                  {card.title}
                </h2>

                {card.body && (
                  <article
                    className="
                      prose prose-invert max-w-none
                      prose-p:leading-7 prose-p:text-white/85
                      prose-strong:text-white
                      prose-a:text-fuchsia-300 prose-a:underline prose-a:underline-offset-4
                      hover:prose-a:text-fuchsia-200
                    "
                  >
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        a: ({ node, ...props }) => (
                          <a
                            {...props}
                            target="_blank"
                            rel="noreferrer noopener"
                          />
                        ),
                      }}
                    >
                      {card.body}
                    </ReactMarkdown>
                  </article>
                )}

                {/* indented subcards */}
                {card.subcards.length > 0 && (
                  <div className="mt-6 space-y-4 pl-4">
                    {card.subcards.map((sub, sIdx) => (
                      <div
                        key={sIdx}
                        className="rounded-2xl border border-white/10 bg-white/5 p-4"
                      >
                        <article
                          className="
                            prose prose-invert max-w-none
                            prose-p:leading-7 prose-p:text-white/85
                            prose-strong:text-white
                            prose-a:text-fuchsia-300 prose-a:underline prose-a:underline-offset-4
                            hover:prose-a:text-fuchsia-200
                          "
                        >
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              a: ({ node, ...props }) => (
                                <a
                                  {...props}
                                  target="_blank"
                                  rel="noreferrer noopener"
                                />
                              ),
                            }}
                          >
                            {sub}
                          </ReactMarkdown>
                        </article>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <p className="mt-10 text-center text-xs text-white/50">
          Built with LangGraph + OpenAI. Summaries may be imperfect — always check sources.
        </p>
      </main>
    </div>
  )
}






