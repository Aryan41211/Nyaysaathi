import { useState } from "react";
import DashboardNavbar from "@/components/DashboardNavbar";
import SettingsPanel from "@/components/SettingsPanel";
import { Button } from "@/components/ui/button";
import { classifyIssue, type ClassifyResponse } from "@/lib/api";
import { getSession } from "@/lib/auth";

const AddCase = () => {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [problem, setProblem] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ClassifyResponse | null>(null);

  const handleAnalyze = async () => {
    if (!problem.trim()) {
      setError("Please describe your issue first.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const session = getSession();
      const response = await classifyIssue({
        user_input: problem,
        user_id: session?.user?.id,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to process your request.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <DashboardNavbar onSettingsClick={() => setSettingsOpen(true)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />

      <main className="w-full px-6 lg:px-12 py-12 max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-foreground mb-2">Describe Your Problem</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Explain your legal issue in simple language. Our AI will guide you through the process.
        </p>

        <textarea
          className="w-full h-48 rounded-xl border bg-card p-4 text-foreground text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="My employer has not paid my salary for two months."
          value={problem}
          onChange={(e) => setProblem(e.target.value)}
        />

        {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}

        <div className="mt-6 flex justify-end">
          <Button size="lg" onClick={handleAnalyze} disabled={loading}>
            {loading ? "Analyzing..." : "Analyze"}
          </Button>
        </div>

        {result ? (
          <section className="mt-8 rounded-xl border bg-card p-6 space-y-5">
            <div>
              <h2 className="text-lg font-semibold">Classification</h2>
              <p className="text-sm text-muted-foreground">
                {result.category} / {result.subcategory}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                confidence: {result.final_confidence.toFixed(2)} | embedding: {result.embedding_score.toFixed(2)}
              </p>
            </div>

            {result.needs_clarification ? (
              <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-900">
                {result.clarification_question}
              </div>
            ) : (
              <>
                {result.final_confidence < 0.55 ? (
                  <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-900">
                    Can you describe your problem in a bit more detail?
                  </div>
                ) : null}

                <div>
                  <h3 className="font-semibold">What is your problem</h3>
                  <p className="text-sm text-muted-foreground mt-1">{result.intent_summary}</p>
                </div>

                <div>
                  <h3 className="font-semibold">What you should do</h3>
                  <ol className="list-decimal pl-5 mt-2 space-y-1 text-sm text-muted-foreground">
                    {result.workflow_steps.map((step, idx) => (
                      <li key={`${idx}-${step}`}>{step}</li>
                    ))}
                  </ol>
                </div>

                <div>
                  <h3 className="font-semibold">Documents needed</h3>
                  <ul className="list-disc pl-5 mt-2 space-y-1 text-sm text-muted-foreground">
                    {result.required_documents.map((doc, idx) => (
                      <li key={`${idx}-${doc}`}>{doc}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h3 className="font-semibold">Who to contact</h3>
                  <ul className="list-disc pl-5 mt-2 space-y-1 text-sm text-muted-foreground">
                    {result.authorities.map((authority, idx) => {
                      if (typeof authority === "string") {
                        return <li key={`${idx}-${authority}`}>{authority}</li>;
                      }
                      return <li key={`${idx}-${String(authority.name || "authority")}`}>{String(authority.name || "Authority")}</li>;
                    })}
                  </ul>
                </div>

                <div>
                  <h3 className="font-semibold">Relevant laws</h3>
                  <ul className="list-disc pl-5 mt-2 space-y-1 text-sm text-muted-foreground">
                    {result.relevant_laws.length > 0 ? result.relevant_laws.map((law, idx) => <li key={`${idx}-${law}`}>{law}</li>) : <li>No specific laws listed for this workflow.</li>}
                  </ul>
                </div>
              </>
            )}
          </section>
        ) : null}
      </main>
    </div>
  );
};

export default AddCase;
