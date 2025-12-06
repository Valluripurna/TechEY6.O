import { useState, useEffect } from "react";
import { Sidebar } from "@/components/Sidebar";
import { MobileHeader } from "@/components/MobileHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TrendingUp, Database, Activity, ArrowRight, Download, BookOpen } from "lucide-react";
import { agents as allAgents } from "./Agents";

const processSteps = [
  {
    step: 1,
    title: "Connect Data Sources",
    description: "Integrate your pharmaceutical databases and research platforms",
  },
  {
    step: 2,
    title: "AI Analysis",
    description: "Our agents analyze data using advanced machine learning models",
  },
  {
    step: 3,
    title: "Actionable Insights",
    description: "Receive comprehensive reports with strategic recommendations",
  },
];

export default function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userName, setUserName] = useState<string | null>(null);
  const [downloadsTotal, setDownloadsTotal] = useState<number>(0);

  useEffect(() => {
    try {
      const raw = localStorage.getItem('user');
      if (raw) {
        const u = JSON.parse(raw);
        setUserName(u?.name || null);
      }
    } catch (e) {
      setUserName(null);
    }
    // fetch reports metrics (downloads total)
    (async () => {
      try {
        const token = localStorage.getItem('token');
        const headers: any = {};
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const resp = await fetch('http://localhost:4000/api/reports', { headers });
        if (!resp.ok) return;
        const data = await resp.json();
        if (data && typeof data.downloads_total === 'number') setDownloadsTotal(data.downloads_total);
      } catch (e) {
        // ignore
      }
    })();
  }, []);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <MobileHeader onMenuClick={() => setSidebarOpen(true)} />
      
      <main className="flex-1 md:ml-64 pt-14 md:pt-0">
        <div className="container max-w-7xl py-4 md:py-8 px-4">
          {/* Hero Section */}
          <div className="mb-6 md:mb-8">
            <h1 className="mb-2 text-2xl md:text-3xl font-bold text-foreground">
              Welcome back{userName ? `, ${userName}` : ''}
            </h1>
            <p className="text-sm md:text-base text-muted-foreground">
              Your AI-powered pharmaceutical research dashboard
            </p>
          </div>

          {/* Summary Tiles */}
          <div className="mb-8 md:mb-12 grid gap-4 md:gap-6 sm:grid-cols-3">
            <Card className="card-elevated p-5 md:p-6 hover:shadow-lg transition-all duration-300">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <p className="text-sm font-medium text-muted-foreground mb-1">Worker Agents</p>
                  <h3 className="text-3xl md:text-4xl font-bold text-foreground mb-2">{allAgents.length}</h3>
                  <p className="text-xs text-muted-foreground">Active agents available</p>
                </div>
                <div className="flex-shrink-0 p-3 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10">
                  <TrendingUp className="h-6 w-6 md:h-7 md:w-7 text-primary" />
                </div>
              </div>
            </Card>

            <Card className="card-elevated p-5 md:p-6 hover:shadow-lg transition-all duration-300">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <p className="text-sm font-medium text-muted-foreground mb-1">Reports Downloaded</p>
                      <h3 className="text-3xl md:text-4xl font-bold text-foreground mb-2">{downloadsTotal}</h3>
                      <p className="text-xs text-muted-foreground">Total report downloads</p>
                </div>
                <div className="flex-shrink-0 p-3 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10">
                  <Download className="h-6 w-6 md:h-7 md:w-7 text-primary" />
                </div>
              </div>
            </Card>

            <Card className="card-elevated p-5 md:p-6 hover:shadow-lg transition-all duration-300">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <p className="text-sm font-medium text-muted-foreground mb-1">Knowledge Base</p>
                  <h3 className="text-3xl md:text-4xl font-bold text-foreground mb-2">Ready</h3>
                  <p className="text-xs text-muted-foreground">Upload & search docs</p>
                </div>
                <div className="flex-shrink-0 p-3 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10">
                  <BookOpen className="h-6 w-6 md:h-7 md:w-7 text-primary" />
                </div>
              </div>
            </Card>
          </div>

          {/* Available Agents List */}
          <div className="mb-8">
            <h2 className="mb-3 text-lg font-semibold">Available Agents</h2>
            <div className="grid gap-4 md:gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {allAgents.map((agent) => (
                <Card key={agent.name} className="card-elevated border-border/50 hover:border-primary/30 transition-all duration-300 group">
                  <CardHeader className="pb-3">
                    <div className="mb-2 md:mb-3 flex h-10 w-10 md:h-12 md:w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary/10 to-primary/5 transition-all duration-300">
                      <agent.icon className="h-5 w-5 md:h-6 md:w-6 text-primary" />
                    </div>
                    <CardTitle className="text-base md:text-lg">{agent.name}</CardTitle>
                    <CardDescription className="text-xs text-muted-foreground">{agent.source}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs md:text-sm text-muted-foreground leading-relaxed">{agent.description}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* How It Works */}
          <Card className="shadow-card border-border/50 bg-gradient-subtle">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg md:text-xl">How It Works</CardTitle>
              <CardDescription className="text-xs md:text-sm">
                Three simple steps to unlock powerful pharmaceutical insights
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:gap-8 sm:grid-cols-2 lg:grid-cols-3">
                {processSteps.map((step, index) => (
                  <div key={step.step} className="relative group">
                    <div className="mb-3 md:mb-4 flex items-center gap-3 md:gap-4">
                      <div className="flex h-10 w-10 md:h-12 md:w-12 shrink-0 items-center justify-center rounded-full bg-gradient-medical text-base md:text-lg font-bold text-primary-foreground shadow-md group-hover:shadow-lg transition-shadow">
                        {step.step}
                      </div>
                      {index < processSteps.length - 1 && (
                        <div className="hidden h-0.5 flex-1 bg-gradient-to-r from-primary/40 to-transparent lg:block" />
                      )}
                    </div>
                    <h3 className="mb-2 font-semibold text-sm md:text-base text-foreground group-hover:text-primary transition-colors">{step.title}</h3>
                    <p className="text-xs md:text-sm text-muted-foreground">{step.description}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
