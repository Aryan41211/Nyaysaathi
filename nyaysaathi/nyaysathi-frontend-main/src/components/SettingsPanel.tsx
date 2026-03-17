import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { clearSession } from "@/lib/auth";

interface Props {
  open: boolean;
  onClose: () => void;
}

const SettingsPanel = ({ open, onClose }: Props) => {
  const [language, setLanguage] = useState("English");
  const navigate = useNavigate();

  const languages = ["English", "Marathi", "Hindi"];

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-foreground/20 z-50" onClick={onClose} />
      <div className="fixed right-0 top-0 h-full w-80 bg-card shadow-xl z-50 p-6 flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Settings</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            <X size={20} />
          </button>
        </div>

        <div>
          <h3 className="text-sm font-medium text-foreground mb-3">Language Preference</h3>
          <div className="space-y-2">
            {languages.map((lang) => (
              <label key={lang} className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="language"
                  checked={language === lang}
                  onChange={() => setLanguage(lang)}
                  className="accent-primary w-4 h-4"
                />
                <span className="text-sm text-foreground">{lang}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="mt-auto">
          <Button
            variant="destructive"
            className="w-full"
            onClick={() => {
              clearSession();
              onClose();
              navigate("/login");
            }}
          >
            Sign Out
          </Button>
        </div>
      </div>
    </>
  );
};

export default SettingsPanel;
