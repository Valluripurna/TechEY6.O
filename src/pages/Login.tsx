import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Database, ArrowLeft, User } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function Login() {
  const navigate = useNavigate();
  const [isSignup, setIsSignup] = useState(false);
  const [isForgotPassword, setIsForgotPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [mode, setMode] = useState<"login" | "signup" | "forgot">("login");
  const [otp, setOtp] = useState("");
  const [signupSent, setSignupSent] = useState(false);
  const [forgotSent, setForgotSent] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const API = (import.meta.env && import.meta.env.VITE_API_URL) || 'http://localhost:4000';
  const { toast } = useToast();
  const api = async (path: string, body: any) => {
    setLoading(true);
    setMessage(null);
    try {
      const base = API?.trim() || "";
      const url = `${base}/api/${path}`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const contentType = res.headers.get("content-type") || "";
      let data: any = null;
      if (contentType.includes("application/json")) {
        try { data = await res.json(); } catch { data = null; }
      } else {
        const text = await res.text();
        try { data = JSON.parse(text); } catch { data = { message: text }; }
      }
      if (!res.ok) {
        const msg = (data && (data.error || data.message)) || `Request failed (${res.status})`;
        throw new Error(msg);
      }
      return data || {};
    } catch (e: any) {
      setMessage(e.message || "Network error");
      throw e;
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    try {
      const data = await api("auth/signin", { email, password });
      setMessage("Logged in");
      toast({ title: "Login successful", description: `Logged in as ${email}` });
      localStorage.setItem("token", data.token);
      // Navigate to dashboard after successful login
      navigate('/dashboard');
    } catch (e: any) {
      toast({ title: "Login failed", description: e?.message || "Unable to login", variant: "destructive" });
    }
  };

  const handleSignupSendOtp = async () => {
    try {
      await api("auth/signup", { email, password, name, role });
      setSignupSent(true);
      setMessage("OTP sent to your email");
      toast({ title: "OTP sent", description: `Check ${email} for the code` });
    } catch (e: any) {
      toast({ title: "Signup error", description: e?.message || "Failed to send OTP", variant: "destructive" });
    }
  };

  const handleSignupVerifyOtp = async () => {
    try {
      const data = await api("auth/verify-otp", { email, otp });
      setMessage("Signup verified");
      toast({ title: "Signup verified", description: "Your account is ready" });
      localStorage.setItem("token", data.token);
      setIsSignup(false);
      // Redirect to the main app URL after successful signup
      // Use full origin so the browser performs a hard redirect
      window.location.href = 'http://localhost:8080/';
    } catch (e: any) {
      toast({ title: "OTP verification failed", description: e?.message || "Invalid or expired OTP", variant: "destructive" });
    }
  };

  const handleForgotSendOtp = async () => {
    try {
      await api("auth/forgot-password", { email });
      setForgotSent(true);
      setMessage("Reset OTP sent to your email");
      toast({ title: "Reset OTP sent", description: `Check ${email} for the code` });
    } catch (e: any) {
      toast({ title: "Reset OTP error", description: e?.message || "Failed to send reset OTP", variant: "destructive" });
    }
  };

  const handleResetPassword = async () => {
    try {
      await api("auth/reset-password", { email, otp, password: newPassword });
      setMessage("Password reset successful");
      toast({ title: "Password reset", description: "You can log in now" });
      setIsForgotPassword(false);
      // Focus user back to login view
      setIsSignup(false);
      navigate('/login');
    } catch (e: any) {
      toast({ title: "Reset failed", description: e?.message || "Invalid OTP or server error", variant: "destructive" });
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
  };

  const handleToggleSignup = () => {
    setIsSignup(!isSignup);
  };

  if (isForgotPassword) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="w-full max-w-md">
          {/* Logo */}
          <div className="mb-6 md:mb-8 text-center">
            <div className="mx-auto mb-3 md:mb-4 flex h-12 w-12 md:h-16 md:w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary/80 shadow-lg transform transition-transform hover:scale-110">
              <Database className="h-6 w-6 md:h-8 md:w-8 text-primary-foreground" />
            </div>
            <h1 className="text-xl md:text-2xl font-bold text-foreground">Pharma Mind Nexus</h1>
            <p className="mt-1 text-xs md:text-sm text-muted-foreground">
              AI-Powered Pharmaceutical Analytics
            </p>
          </div>

          <Card className="shadow-card hover:shadow-elevated transition-all duration-300 border-border/50 glass-effect transform hover:-translate-y-1">
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-xl md:text-2xl font-semibold">
                Reset Password
              </CardTitle>
               <CardDescription className="text-xs md:text-sm">
                 Enter your email to receive an OTP, then reset.
               </CardDescription>
            </CardHeader>
            <CardContent>
                 <div className="space-y-3 md:space-y-4">
                   <div className="space-y-2">
                     <Label htmlFor="reset-email" className="text-xs md:text-sm">Email</Label>
                     <Input id="reset-email" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required className="bg-input text-sm border-border focus:ring-2 focus:ring-primary/30 transition-all" />
                   </div>
                   {!forgotSent ? (
                     <Button onClick={handleForgotSendOtp} className="w-full text-sm md:text-base bg-gradient-medical hover:opacity-90 transition-all duration-300 hover:shadow-lg transform hover:scale-105 font-medium" size="lg" disabled={loading}>
                       Send Reset OTP
                     </Button>
                   ) : (
                     <>
                       <div className="space-y-2">
                         <Label htmlFor="reset-otp" className="text-xs md:text-sm">OTP</Label>
                         <Input id="reset-otp" type="text" placeholder="6-digit code" value={otp} onChange={(e) => setOtp(e.target.value)} className="bg-input text-sm border-border focus:ring-2 focus:ring-primary/30 transition-all" />
                       </div>
                       <div className="space-y-2">
                         <Label htmlFor="new-pass" className="text-xs md:text-sm">New Password</Label>
                         <Input id="new-pass" type="password" placeholder="••••••••" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="bg-input text-sm border-border focus:ring-2 focus:ring-primary/30 transition-all" />
                       </div>
                       <div className="flex gap-2">
                         <Button onClick={handleResetPassword} className="flex-1 text-sm md:text-base bg-green-600 hover:opacity-90 transition-all duration-300 hover:shadow-lg transform hover:scale-105 font-medium" size="lg" disabled={loading}>
                           Reset Password
                         </Button>
                         <Button onClick={handleForgotSendOtp} className="flex-1 text-sm md:text-base bg-gradient-medical hover:opacity-90 transition-all duration-300 hover:shadow-lg transform hover:scale-105 font-medium" size="lg" disabled={loading}>
                           Resend OTP
                         </Button>
                       </div>
                     </>
                   )}
                 </div>

              <div className="mt-4 md:mt-6 text-center">
                <button
                  type="button"
                  onClick={() => setIsForgotPassword(false)}
                  className="text-xs md:text-sm text-muted-foreground hover:text-primary transition-colors inline-flex items-center gap-2 font-medium"
                >
                  <ArrowLeft className="h-3 w-3" />
                  Back to Login
                </button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-6 md:mb-8 text-center">
          <div className="mx-auto mb-3 md:mb-4 flex h-12 w-12 md:h-16 md:w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary/80 shadow-lg transform transition-transform hover:scale-110">
            <Database className="h-6 w-6 md:h-8 md:w-8 text-primary-foreground" />
          </div>
          <h1 className="text-xl md:text-2xl font-bold text-foreground">Pharma Mind Nexus</h1>
          <p className="mt-1 text-xs md:text-sm text-muted-foreground">
            AI-Powered Pharmaceutical Analytics
          </p>
        </div>

        <Card className="shadow-card hover:shadow-elevated transition-all duration-300 border-border/50 glass-effect transform hover:-translate-y-1">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-xl md:text-2xl font-semibold">
              {isSignup ? "Create Account" : "Welcome Back"}
            </CardTitle>
            <CardDescription className="text-xs md:text-sm">
              {isSignup
                ? "Enter your details to create your account"
                : "Enter your credentials to access your dashboard"}
            </CardDescription>
          </CardHeader>
          <CardContent>
             <form onSubmit={handleSubmit} className="space-y-3 md:space-y-4">
              {isSignup && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="name" className="text-xs md:text-sm">Full Name</Label>
                    <Input
                      id="name"
                      type="text"
                      placeholder="Dr. Sarah Chen"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      className="bg-input text-sm border-border focus:ring-2 focus:ring-primary/30 transition-all"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="signup-role" className="text-xs md:text-sm">Role</Label>
                    <Input
                      id="signup-role"
                      type="text"
                      placeholder="Lead Researcher"
                      value={role}
                      onChange={(e) => setRole(e.target.value)}
                      required
                      className="bg-input text-sm border-border focus:ring-2 focus:ring-primary/30 transition-all"
                    />
                  </div>
                </>
              )}
              <div className="space-y-2">
                <Label htmlFor="email" className="text-xs md:text-sm">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="sarah.chen@pharma.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="bg-input text-sm border-border focus:ring-2 focus:ring-primary/30 transition-all"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-xs md:text-sm">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="bg-input text-sm border-border focus:ring-2 focus:ring-primary/30 transition-all"
                />
              </div>
              {isSignup && (
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword" className="text-xs md:text-sm">Confirm Password</Label>
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="••••••••"
                    required
                    className="bg-input text-sm border-border focus:ring-2 focus:ring-primary/30 transition-all"
                  />
                </div>
              )}
               {!isSignup && (
                 <Button 
                   type="submit" 
                   className="w-full text-sm md:text-base bg-gradient-medical hover:opacity-90 transition-all duration-300 hover:shadow-lg transform hover:scale-105 font-medium"
                   size="lg"
                   onClick={(e) => { e.preventDefault(); handleLogin(); }}
                 >
                   Sign In
                 </Button>
               )}
               {isSignup && (
                 <div className="space-y-3">
                   {!signupSent ? (
                     <Button 
                       type="button" 
                       className="w-full text-sm md:text-base bg-gradient-medical hover:opacity-90 transition-all duration-300 hover:shadow-lg transform hover:scale-105 font-medium"
                       size="lg"
                       onClick={handleSignupSendOtp}
                       disabled={loading}
                     >
                       Send OTP
                     </Button>
                   ) : (
                     <>
                       <div className="space-y-2">
                         <Label htmlFor="signup-otp" className="text-xs md:text-sm">OTP</Label>
                         <Input id="signup-otp" type="text" placeholder="6-digit code" value={otp} onChange={(e) => setOtp(e.target.value)} className="bg-input text-sm border-border focus:ring-2 focus:ring-primary/30 transition-all" />
                       </div>
                       <div className="flex gap-2">
                         <Button 
                           type="button" 
                           className="flex-1 text-sm md:text-base bg-green-600 hover:opacity-90 transition-all duration-300 hover:shadow-lg transform hover:scale-105 font-medium"
                           size="lg"
                           onClick={handleSignupVerifyOtp}
                           disabled={loading}
                         >
                           Verify OTP
                         </Button>
                         <Button 
                           type="button" 
                           className="flex-1 text-sm md:text-base bg-gradient-medical hover:opacity-90 transition-all duration-300 hover:shadow-lg transform hover:scale-105 font-medium"
                           size="lg"
                           onClick={handleSignupSendOtp}
                           disabled={loading}
                         >
                           Resend OTP
                         </Button>
                       </div>
                     </>
                   )}
                 </div>
               )}
            </form>

            <div className="mt-4 md:mt-6 text-center">
              <span className="text-xs md:text-sm text-muted-foreground">
                {isSignup ? "Already have an account? " : "Don't have an account? "}
              </span>
              <button
                type="button"
                onClick={handleToggleSignup}
                className="text-xs md:text-sm text-primary hover:text-primary/80 transition-colors font-medium transform hover:scale-105 ml-1"
              >
                {isSignup ? "Sign in" : "Sign up"}
              </button>
              {!isSignup && (
                <div className="mt-3">
                  <button
                    type="button"
                    onClick={() => setIsForgotPassword(true)}
                    className="text-xs md:text-sm text-primary hover:text-primary/80 transition-colors font-medium transform hover:scale-105"
                  >
                    Forgot password?
                  </button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}