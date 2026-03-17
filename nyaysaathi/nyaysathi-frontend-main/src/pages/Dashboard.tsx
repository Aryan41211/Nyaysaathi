import { useState } from "react";
import DashboardNavbar from "@/components/DashboardNavbar";
import SettingsPanel from "@/components/SettingsPanel";
import { PlusCircle, FolderOpen, Bell, HelpCircle } from "lucide-react";
import { Link } from "react-router-dom";

const cards = [
  { icon: PlusCircle, title: "Add New Case", desc: "Describe your legal problem and get guidance.", to: "/add-case" },
  { icon: FolderOpen, title: "My Cases", desc: "View and track your submitted cases.", to: "/my-cases" },
  { icon: Bell, title: "Notifications", desc: "Check updates on your cases.", to: "/dashboard" },
  { icon: HelpCircle, title: "Help", desc: "Get assistance using the platform.", to: "/dashboard" },
];

const Dashboard = () => {
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <DashboardNavbar onSettingsClick={() => setSettingsOpen(true)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />

      <main className="w-full px-6 lg:px-12 py-12">
        <h1 className="text-2xl font-bold text-foreground mb-8">Dashboard</h1>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {cards.map((c) => (
            <Link
              key={c.title}
              to={c.to}
              className="bg-card rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col items-center text-center gap-3"
            >
              <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center">
                <c.icon className="w-7 h-7 text-primary" />
              </div>
              <h3 className="font-semibold text-foreground">{c.title}</h3>
              <p className="text-sm text-muted-foreground">{c.desc}</p>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
