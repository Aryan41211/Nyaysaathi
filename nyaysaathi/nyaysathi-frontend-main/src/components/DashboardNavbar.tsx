import { Scale, Settings } from "lucide-react";
import { Link } from "react-router-dom";

interface Props {
  onSettingsClick: () => void;
}

const DashboardNavbar = ({ onSettingsClick }: Props) => {
  return (
    <nav className="w-full bg-card shadow-sm sticky top-0 z-50">
      <div className="w-full px-6 lg:px-12 flex items-center justify-between h-16">
        <Link to="/dashboard" className="flex items-center gap-2">
          <Scale className="h-7 w-7 text-primary" />
          <span className="text-xl font-bold text-primary">NyaySaathi</span>
        </Link>
        <button onClick={onSettingsClick} className="text-foreground hover:text-primary transition-colors">
          <Settings size={22} />
        </button>
      </div>
    </nav>
  );
};

export default DashboardNavbar;
