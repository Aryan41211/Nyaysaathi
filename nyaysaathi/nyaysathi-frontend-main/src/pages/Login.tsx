import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Scale } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { login, signup } from "@/lib/api";
import { setSession, type UserRole } from "@/lib/auth";

const Login = () => {
  const [isSignup, setIsSignup] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("user");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      if (isSignup) {
        const result = await signup({ name, email, password });
        setSession(result);
        navigate("/dashboard");
        return;
      }

      const result = await login({ email, password, login_as: role });
      setSession(result);
      if (result.user.role === "admin") {
        navigate("/admin-dashboard");
      } else {
        navigate("/dashboard");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-card rounded-2xl shadow-lg p-8">
        <div className="flex items-center justify-center gap-2 mb-8">
          <Scale className="h-8 w-8 text-primary" />
          <span className="text-2xl font-bold text-primary">NyaySaathi</span>
        </div>

        <h1 className="text-xl font-semibold text-foreground text-center mb-4">
          {isSignup ? "Create your account" : "Login to NyaySaathi"}
        </h1>

        <div className="text-sm text-center mb-6">
          <button className="text-primary font-medium" onClick={() => setIsSignup((v) => !v)}>
            {isSignup ? "Already have an account? Login" : "Need an account? Sign up"}
          </button>
        </div>

        <div className="space-y-4">
          {isSignup ? (
            <div>
              <label className="text-sm font-medium text-foreground mb-1.5 block">Full Name</label>
              <Input
                type="text"
                placeholder="Enter your full name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
          ) : null}

          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">Email</label>
            <Input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">Password</label>
            <Input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {!isSignup ? (
            <div>
              <label className="text-sm font-medium text-foreground mb-1.5 block">Login As</label>
              <select
                className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          ) : null}

          {error ? <p className="text-sm text-red-600">{error}</p> : null}

          <Button className="w-full" onClick={handleSubmit} disabled={loading}>
            {loading ? "Please wait..." : isSignup ? "Sign Up" : "Login"}
          </Button>

          {!isSignup ? (
            <button
              className="w-full text-sm text-primary"
              onClick={() => {
                setRole("admin");
              }}
            >
              Login as Admin
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default Login;
