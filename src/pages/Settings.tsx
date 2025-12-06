import { useState, useEffect } from "react";
import { Sidebar } from "@/components/Sidebar";
import { MobileHeader } from "@/components/MobileHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { User, Bell, Moon, Palette } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useTheme } from "@/contexts/ThemeContext";

export default function Settings() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { toast } = useToast();
  const { theme, toggleTheme } = useTheme();
  const API = (import.meta.env && import.meta.env.VITE_API_URL) || 'http://localhost:4000';

  const [fullName, setFullName] = useState('');
  const [emailValue, setEmailValue] = useState('');
  const [roleValue, setRoleValue] = useState('');
  const [emailNotifications, setEmailNotifications] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;
    fetch(`${API}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.msg || 'Failed to fetch profile');
        const u = data.user;
        setFullName(u.name || '');
        setEmailValue(u.email || '');
        setRoleValue(u.role || '');
        setEmailNotifications(u.email_notifications !== false);
      })
      .catch(() => {
        // ignore failures silently
      });
  }, []);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <MobileHeader onMenuClick={() => setSidebarOpen(true)} />
      
      <main className="flex-1 md:ml-64 pt-14 md:pt-0">
        <div className="container max-w-4xl py-4 md:py-8 px-4">
          <div className="mb-6 md:mb-8">
            <h1 className="mb-2 text-2xl md:text-3xl font-bold text-foreground">Settings</h1>
            <p className="text-sm md:text-base text-muted-foreground">
              Manage your account and API integrations
            </p>
          </div>

          <div className="space-y-4 md:space-y-6">
            {/* Profile Settings */}
            <Card className="shadow-card hover:shadow-elevated transition-all duration-300 transform hover:-translate-y-1 border-border/50 glass-effect">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <User className="h-5 w-5 md:h-6 md:w-6 text-primary flex-shrink-0" />
                  </div>
                  <CardTitle className="text-lg md:text-xl">Profile Settings</CardTitle>
                </div>
                <CardDescription className="text-xs md:text-sm">Update your personal information</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 md:space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-xs md:text-sm">Full Name</Label>
                  <Input
                    id="name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Full name"
                    className="bg-input text-sm border-border focus:ring-2 focus:ring-primary/30 transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-xs md:text-sm">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={emailValue}
                    onChange={(e) => setEmailValue(e.target.value)}
                    placeholder="email@company.com"
                    className="bg-input text-sm border-border focus:ring-2 focus:ring-primary/30 transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role" className="text-xs md:text-sm">Role</Label>
                  <Input
                    id="role"
                    value={roleValue}
                    onChange={(e) => setRoleValue(e.target.value)}
                    placeholder="Role"
                    className="bg-input text-sm border-border focus:ring-2 focus:ring-primary/30 transition-all"
                  />
                </div>
                <Button onClick={async () => {
                  const token = localStorage.getItem('token');
                  if (!token) { toast({ title: 'Not signed in', description: 'Please sign in to update profile' }); return; }
                  try {
                    const res = await fetch(`${API}/api/auth/me`, {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                      body: JSON.stringify({ name: fullName, email: emailValue, role: roleValue, email_notifications: emailNotifications })
                    });
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.msg || 'Failed to update');
                    localStorage.setItem('user', JSON.stringify(data.user));
                    toast({ title: 'Profile Saved', description: 'Your profile has been updated' });
                  } catch (err: any) {
                    toast({ title: 'Update Failed', description: err.message || 'Could not update profile' });
                  }
                }} className="w-full sm:w-auto text-sm bg-gradient-medical hover:opacity-90 transition-all duration-300 transform hover:scale-105 hover:shadow-lg">
                  Save Profile
                </Button>
              </CardContent>
            </Card>

            {/* Preferences */}
            <Card className="shadow-card hover:shadow-elevated transition-all duration-300 transform hover:-translate-y-1 border-border/50 glass-effect">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <Palette className="h-5 w-5 md:h-6 md:w-6 text-primary flex-shrink-0" />
                  </div>
                  <CardTitle className="text-lg md:text-xl">Preferences</CardTitle>
                </div>
                <CardDescription className="text-xs md:text-sm">Configure your notification and display preferences</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 md:space-y-4">
                <div className="flex items-center justify-between gap-3 p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors">
                  <div className="space-y-0.5 min-w-0 flex-1">
                    <Label className="text-xs md:text-sm flex items-center gap-2">
                      <Moon className="h-4 w-4 text-primary" />
                      Dark Mode
                    </Label>
                    <p className="text-[10px] md:text-xs text-muted-foreground">
                      Switch between light and dark theme
                    </p>
                  </div>
                  <Switch 
                    checked={theme === "dark"} 
                    onCheckedChange={toggleTheme}
                    className="flex-shrink-0 data-[state=checked]:bg-primary data-[state=unchecked]:bg-muted" 
                  />
                </div>
                <div className="flex items-center justify-between gap-3 p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors">
                  <div className="space-y-0.5 min-w-0 flex-1">
                    <Label className="text-xs md:text-sm">Email Notifications</Label>
                    <p className="text-[10px] md:text-xs text-muted-foreground">
                      Receive email updates about your reports
                    </p>
                  </div>
                  <Switch checked={emailNotifications} onCheckedChange={(v: boolean) => setEmailNotifications(Boolean(v))} className="flex-shrink-0 data-[state=checked]:bg-primary data-[state=unchecked]:bg-muted" />
                </div>
                <div className="flex items-center justify-between gap-3 p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors">
                  <div className="space-y-0.5 min-w-0 flex-1">
                    <Label className="text-xs md:text-sm">Agent Alerts</Label>
                    <p className="text-[10px] md:text-xs text-muted-foreground">
                      Get notified when agents complete analysis
                    </p>
                  </div>
                  <Switch defaultChecked className="flex-shrink-0 data-[state=checked]:bg-primary data-[state=unchecked]:bg-muted" />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}