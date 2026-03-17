import { useState } from "react";
import DashboardNavbar from "@/components/DashboardNavbar";
import SettingsPanel from "@/components/SettingsPanel";
import { Button } from "@/components/ui/button";
import { MapPin, Phone, Navigation } from "lucide-react";

const Location = () => {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [state, setState] = useState("");
  const [district, setDistrict] = useState("");
  const [taluka, setTaluka] = useState("");
  const [showResults, setShowResults] = useState(false);

  const selectClass = "w-full h-10 rounded-lg border bg-card px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring";

  return (
    <div className="min-h-screen bg-background">
      <DashboardNavbar onSettingsClick={() => setSettingsOpen(true)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />

      <main className="w-full px-6 lg:px-12 py-12">
        <h1 className="text-2xl font-bold text-foreground mb-8">Find Nearby Office</h1>

        <div className="grid sm:grid-cols-3 gap-4 max-w-3xl mb-8">
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">State</label>
            <select className={selectClass} value={state} onChange={(e) => setState(e.target.value)}>
              <option value="">Select State</option>
              <option value="Maharashtra">Maharashtra</option>
              <option value="Karnataka">Karnataka</option>
              <option value="Delhi">Delhi</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">District</label>
            <select className={selectClass} value={district} onChange={(e) => setDistrict(e.target.value)}>
              <option value="">Select District</option>
              <option value="Pune">Pune</option>
              <option value="Mumbai">Mumbai</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">Taluka</label>
            <select className={selectClass} value={taluka} onChange={(e) => setTaluka(e.target.value)}>
              <option value="">Select Taluka</option>
              <option value="Haveli">Haveli</option>
              <option value="Mulshi">Mulshi</option>
            </select>
          </div>
        </div>

        {!showResults && (
          <Button onClick={() => setShowResults(true)}>Search</Button>
        )}

        {showResults && (
          <div className="mt-8 space-y-6">
            {/* Map placeholder */}
            <div className="w-full h-64 md:h-96 bg-card rounded-xl shadow-sm flex items-center justify-center border">
              <div className="text-center text-muted-foreground">
                <MapPin className="w-10 h-10 mx-auto mb-2" />
                <p className="text-sm">Map view – integrate with Google Maps API</p>
              </div>
            </div>

            {/* Office card */}
            <div className="bg-card rounded-xl p-6 shadow-sm max-w-xl">
              <h3 className="font-semibold text-foreground text-lg mb-3">Labour Office</h3>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p className="flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-primary shrink-0" />
                  Shivajinagar, Pune, Maharashtra 411005
                </p>
                <p className="flex items-center gap-2">
                  <Phone className="w-4 h-4 text-primary shrink-0" />
                  020-25501234
                </p>
              </div>
              <Button className="mt-4 gap-2" variant="outline">
                <Navigation className="w-4 h-4" />
                Get Directions
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Location;
