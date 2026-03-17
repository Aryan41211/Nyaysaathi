import { useState } from "react";
import DashboardNavbar from "@/components/DashboardNavbar";
import SettingsPanel from "@/components/SettingsPanel";
import { Button } from "@/components/ui/button";
import { CheckCircle2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

const steps = [
  { step: 1, title: "Visit Labour Commissioner Office", desc: "Go to your nearest Labour Commissioner Office to initiate the process." },
  { step: 2, title: "Submit Written Complaint", desc: "File a formal written complaint detailing the salary issue." },
  { step: 3, title: "Attach Salary Proof Documents", desc: "Provide salary slips, bank statements, and employment proof." },
  { step: 4, title: "Attend Hearing if Scheduled", desc: "Be present at the hearing date as notified by the office." },
];

const Guidance = () => {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      <DashboardNavbar onSettingsClick={() => setSettingsOpen(true)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />

      <main className="w-full px-6 lg:px-12 py-12 max-w-3xl mx-auto">
        <div className="bg-accent/10 border border-accent/30 rounded-xl px-5 py-3 mb-8">
          <span className="text-sm font-medium text-foreground">Issue Identified: </span>
          <span className="text-sm font-semibold text-primary">Labour Complaint</span>
        </div>

        <h1 className="text-2xl font-bold text-foreground mb-8">Step-by-Step Guidance</h1>

        <div className="space-y-0">
          {steps.map((s, i) => (
            <div key={s.step} className="flex gap-4">
              {/* Timeline */}
              <div className="flex flex-col items-center">
                <div className="w-9 h-9 rounded-full bg-primary flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-5 h-5 text-primary-foreground" />
                </div>
                {i < steps.length - 1 && <div className="w-0.5 flex-1 bg-border" />}
              </div>
              {/* Content */}
              <div className="pb-8">
                <h3 className="font-semibold text-foreground">Step {s.step} – {s.title}</h3>
                <p className="text-sm text-muted-foreground mt-1">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-end mt-4">
          <Button size="lg" onClick={() => navigate("/documents")}>
            Next
          </Button>
        </div>
      </main>
    </div>
  );
};

export default Guidance;
