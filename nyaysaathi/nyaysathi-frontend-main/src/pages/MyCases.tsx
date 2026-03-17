import { useState } from "react";
import DashboardNavbar from "@/components/DashboardNavbar";
import SettingsPanel from "@/components/SettingsPanel";
import { Button } from "@/components/ui/button";
import { FolderOpen } from "lucide-react";

const cases = [
  { id: 1, type: "Labour Complaint", date: "2026-03-05", status: "In Progress" },
  { id: 2, type: "Property Dispute", date: "2026-02-20", status: "Resolved" },
  { id: 3, type: "Consumer Complaint", date: "2026-01-15", status: "Pending" },
];

const statusColor: Record<string, string> = {
  "In Progress": "bg-accent/20 text-accent-foreground",
  Resolved: "bg-primary/10 text-primary",
  Pending: "bg-muted text-muted-foreground",
};

const MyCases = () => {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <DashboardNavbar onSettingsClick={() => setSettingsOpen(true)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />

      <main className="w-full px-6 lg:px-12 py-12">
        <h1 className="text-2xl font-bold text-foreground mb-8">My Cases</h1>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {cases.map((c) => (
            <div key={c.id} className="bg-card rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <FolderOpen className="w-5 h-5 text-primary" />
                </div>
                <h3 className="font-semibold text-foreground">{c.type}</h3>
              </div>
              <p className="text-sm text-muted-foreground mb-1">Submitted: {c.date}</p>
              <span className={`inline-block text-xs font-medium px-3 py-1 rounded-full mt-2 ${statusColor[c.status]}`}>
                {c.status}
              </span>
              <div className="mt-4">
                <Button variant="outline" size="sm">View Details</Button>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
};

export default MyCases;
