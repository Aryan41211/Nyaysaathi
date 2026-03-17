import { useState } from "react";
import DashboardNavbar from "@/components/DashboardNavbar";
import SettingsPanel from "@/components/SettingsPanel";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";
import { useNavigate } from "react-router-dom";

const docs = [
  "ID Proof",
  "Employment Letter",
  "Salary Slips",
  "Bank Statement",
  "Complaint Application",
];

const Documents = () => {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [checked, setChecked] = useState<string[]>([]);
  const navigate = useNavigate();

  const toggle = (doc: string) => {
    setChecked((prev) => prev.includes(doc) ? prev.filter((d) => d !== doc) : [...prev, doc]);
  };

  return (
    <div className="min-h-screen bg-background">
      <DashboardNavbar onSettingsClick={() => setSettingsOpen(true)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />

      <main className="w-full px-6 lg:px-12 py-12 max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-foreground mb-2">Required Documents</h1>
        <p className="text-sm text-muted-foreground mb-8">Gather the following documents before visiting the office.</p>

        <div className="space-y-3">
          {docs.map((doc) => (
            <button
              key={doc}
              onClick={() => toggle(doc)}
              className="w-full flex items-center gap-4 bg-card rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow text-left"
            >
              <div
                className={`w-6 h-6 rounded-md border-2 flex items-center justify-center shrink-0 transition-colors ${
                  checked.includes(doc)
                    ? "bg-primary border-primary"
                    : "border-border"
                }`}
              >
                {checked.includes(doc) && <Check className="w-4 h-4 text-primary-foreground" />}
              </div>
              <span className="text-sm font-medium text-foreground">{doc}</span>
            </button>
          ))}
        </div>

        <div className="flex justify-end mt-8">
          <Button size="lg" onClick={() => navigate("/location")}>
            Next
          </Button>
        </div>
      </main>
    </div>
  );
};

export default Documents;
