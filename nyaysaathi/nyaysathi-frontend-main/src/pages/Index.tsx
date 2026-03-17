import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { MessageSquare, ListChecks, MapPin } from "lucide-react";
import { Link } from "react-router-dom";

const features = [
  {
    icon: MessageSquare,
    title: "Describe Your Problem",
    desc: "Explain your legal issue in simple language and let our AI understand your situation.",
  },
  {
    icon: ListChecks,
    title: "Get Step-by-Step Guidance",
    desc: "Receive clear instructions on legal procedures, required documents, and next steps.",
  },
  {
    icon: MapPin,
    title: "Find Nearby Legal Offices",
    desc: "Locate the correct government offices to approach based on your location.",
  },
];

const Index = () => {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      {/* Hero */}
      <section className="w-full px-6 lg:px-12 py-16 lg:py-24">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div>
            <h1 className="text-3xl lg:text-5xl font-extrabold text-foreground leading-tight">
              NyaySaathi – Your Guide to Legal Procedures
            </h1>
            <p className="mt-4 text-lg font-medium text-accent">
              Helping citizens understand legal steps, required documents, and the correct offices to approach.
            </p>
            <p className="mt-4 text-muted-foreground leading-relaxed">
              NyaySaathi is an AI powered legal guidance system that helps citizens navigate legal procedures easily. Users describe their problem in simple language and the system provides step-by-step guidance, required documents, and nearby government offices.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <Button asChild size="lg">
                <Link to="/login">Get Started</Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <a href="#features">Learn More</a>
              </Button>
            </div>
          </div>

          <div className="flex justify-center">
            <div className="w-full max-w-md bg-card rounded-2xl shadow-lg p-10 flex flex-col items-center gap-4">
              <div className="w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center">
                <svg viewBox="0 0 64 64" className="w-14 h-14 text-primary" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M32 8 L8 24 L32 16 L56 24 Z" />
                  <rect x="14" y="24" width="4" height="24" rx="1" />
                  <rect x="30" y="24" width="4" height="24" rx="1" />
                  <rect x="46" y="24" width="4" height="24" rx="1" />
                  <rect x="8" y="48" width="48" height="4" rx="1" />
                  <circle cx="32" cy="12" r="2" fill="currentColor" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-foreground">Justice for Everyone</h3>
              <p className="text-sm text-muted-foreground text-center">
                Navigate India's legal system with confidence using AI-powered guidance.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="w-full px-6 lg:px-12 py-16 bg-card">
        <h2 className="text-2xl lg:text-3xl font-bold text-foreground text-center mb-12">
          How It Works
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          {features.map((f) => (
            <div
              key={f.title}
              className="bg-background rounded-xl p-8 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                <f.icon className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">{f.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full px-6 lg:px-12 py-8 text-center text-sm text-muted-foreground">
        © 2026 NyaySaathi. All rights reserved.
      </footer>
    </div>
  );
};

export default Index;
