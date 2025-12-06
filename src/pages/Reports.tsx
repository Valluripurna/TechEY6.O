import React, { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { MobileHeader } from "@/components/MobileHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FileText, Search, Download, Calendar, Filter } from "lucide-react";
import { agents } from "./Agents";

interface Report {
  id: string;
  title: string;
  agent: string;
  date: string;
  size: string;
}

export default function Reports() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("date");
  
  // Empty reports array - will be populated when agents generate reports
  const [reports, setReports] = useState<Report[]>([]);
  const [counts, setCounts] = useState<{ total: number; pdf: number; excel: number; text: number }>({ total: 0, pdf: 0, excel: 0, text: 0 });

  // Fetch reports history from backend
  const fetchReports = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers: any = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const resp = await fetch('http://localhost:4000/api/reports', { headers });
      if (!resp.ok) throw new Error('Failed to load reports');
      const data = await resp.json();
      // Normalize data into UI Report shape
      const items: Report[] = (data.reports || []).map((r: any) => ({
        id: r.report_id,
        title: r.query,
        agent: r.report_type.toUpperCase(),
        date: r.generated_at,
        size: (r.metadata?.data_points ?? 0) + ' items'
      }));
      setReports(items);
      if (data.counts) {
        setCounts({
          total: data.counts.total ?? items.length,
          pdf: data.counts.pdf ?? 0,
          excel: data.counts.excel ?? 0,
          text: data.counts.text ?? 0
        });
      } else {
        // Fallback compute
        setCounts({
          total: items.length,
          pdf: items.filter(i => i.agent === 'PDF').length,
          excel: items.filter(i => i.agent === 'EXCEL').length,
          text: items.filter(i => i.agent === 'TEXT').length,
        });
      }
    } catch (e) {
      console.error(e);
    }
  };

  React.useEffect(() => {
    fetchReports();
  }, []);

  const downloadGeneratedReport = async (type: 'pdf' | 'excel', query: string, results?: any) => {
    try {
      const token = localStorage.getItem('token');
      const headers: any = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const resp = await fetch('http://localhost:4000/api/generate-report', {
        method: 'POST',
        headers,
        body: JSON.stringify({ query, type, results })
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || 'Failed to generate report');
      }
      const contentType = resp.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const json = await resp.json();
        if (json && json.download_url) {
          const dlResp = await fetch(`http://localhost:4000${json.download_url}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
          if (!dlResp.ok) throw new Error('Failed to download generated report');
          const blob = await dlResp.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `report_${Date.now()}.${type === 'pdf' ? 'pdf' : 'xlsx'}`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
          // After download the backend deletes the stored report; refresh list
          await fetchReports();
          return;
        }
      }
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${Date.now()}.${type === 'pdf' ? 'pdf' : 'xlsx'}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
      alert((e as Error).message);
    }
  };

  const downloadStoredReport = async (reportId: string, typeHint?: 'pdf'|'excel') => {
    try {
      const token = localStorage.getItem('token');
      const headers: any = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const resp = await fetch(`http://localhost:4000/api/reports/${reportId}/download`, { headers });
      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(errText || 'Failed to download report');
      }
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${Date.now()}.${typeHint === 'excel' ? 'xlsx' : 'pdf'}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      // After server-side download endpoint deletes the report, refresh list
      await fetchReports();
    } catch (e) {
      console.error(e);
      alert((e as Error).message);
    }
  };

  const deleteStoredReport = async (reportId: string) => {
    try {
      const token = localStorage.getItem('token');
      const headers: any = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const resp = await fetch(`http://localhost:4000/api/reports/${reportId}`, { method: 'DELETE', headers });
      if (!resp.ok) {
        const txt = await resp.text().catch(() => '');
        throw new Error(txt || 'Failed to delete report');
      }
      await fetchReports();
    } catch (e) {
      console.error(e);
      alert((e as Error).message);
    }
  };

  // Get all agent names from the agents array
  const agentNames = agents.map((agent) => agent.name).sort();

  // Filter and sort reports
  const filteredReports = reports
    .filter((report) => {
      const matchesSearch = report.title.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesAgent = selectedAgent === "all" || report.agent === selectedAgent;
      return matchesSearch && matchesAgent;
    })
    .sort((a, b) => {
      if (sortBy === "date") {
        return new Date(b.date).getTime() - new Date(a.date).getTime();
      } else if (sortBy === "name") {
        return a.title.localeCompare(b.title);
      }
      return 0;
    });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <MobileHeader onMenuClick={() => setSidebarOpen(true)} />
      
      <main className="flex-1 md:ml-64 pt-14 md:pt-0">
        <div className="container max-w-7xl py-4 md:py-8 px-4">
          <div className="mb-6 md:mb-8">
            <h1 className="mb-2 text-2xl md:text-3xl font-bold text-foreground">Reports</h1>
            <p className="text-sm md:text-base text-muted-foreground">
              Access and download your pharmaceutical research reports
            </p>
            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
              <Card className="p-3">
                <div className="text-xs text-muted-foreground">Total</div>
                <div className="text-lg font-semibold">{counts.total}</div>
              </Card>
              <Card className="p-3">
                <div className="text-xs text-muted-foreground">PDF</div>
                <div className="text-lg font-semibold">{counts.pdf}</div>
              </Card>
              <Card className="p-3">
                <div className="text-xs text-muted-foreground">Excel</div>
                <div className="text-lg font-semibold">{counts.excel}</div>
              </Card>
              <Card className="p-3">
                <div className="text-xs text-muted-foreground">Text</div>
                <div className="text-lg font-semibold">{counts.text}</div>
              </Card>
            </div>
          </div>

          {/* Search and Filters */}
          <div className="mb-6 space-y-3">
            <div className="grid gap-3 md:grid-cols-3">
              {/* Search by Name */}
              <div className="relative md:col-span-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="Search by report name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-input text-sm"
                />
              </div>

              {/* Filter by Agent */}
              <div className="relative">
                <Select value={selectedAgent} onValueChange={setSelectedAgent}>
                  <SelectTrigger className="bg-input text-sm">
                    <div className="flex items-center gap-2">
                      <Filter className="h-4 w-4 text-muted-foreground" />
                      <SelectValue placeholder="Filter by agent" />
                    </div>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Agents</SelectItem>
                    {agentNames.map((agentName) => (
                      <SelectItem key={agentName} value={agentName}>
                        {agentName}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Sort By */}
              <div className="relative">
                <Select value={sortBy} onValueChange={setSortBy}>
                  <SelectTrigger className="bg-input text-sm">
                    <SelectValue placeholder="Sort by" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="date">Sort by Date (Newest)</SelectItem>
                    <SelectItem value="name">Sort by Name (A-Z)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Active Filters Display */}
            {(selectedAgent !== "all" || searchQuery) && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>Active filters:</span>
                {searchQuery && (
                  <span className="bg-primary/10 text-primary px-2 py-1 rounded">
                    Name: "{searchQuery}"
                  </span>
                )}
                {selectedAgent !== "all" && (
                  <span className="bg-primary/10 text-primary px-2 py-1 rounded">
                    Agent: {selectedAgent}
                  </span>
                )}
                <button
                  onClick={() => {
                    setSearchQuery("");
                    setSelectedAgent("all");
                  }}
                  className="text-primary hover:underline ml-2"
                >
                  Clear all
                </button>
              </div>
            )}
          </div>

          {/* Reports List */}
          {filteredReports.length > 0 ? (
            <div className="grid gap-4 md:gap-5">
              {filteredReports.map((report) => (
                <Card key={report.id} className="shadow-card border-border/50 hover:shadow-lg transition-all duration-300 group">
                  <CardContent className="p-4 md:p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 md:gap-4 flex-1 min-w-0">
                        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 flex-shrink-0">
                          <FileText className="h-6 w-6 text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-base md:text-lg font-semibold text-foreground mb-1 truncate">
                            {report.title}
                          </h3>
                          <div className="flex flex-wrap items-center gap-3 text-xs md:text-sm text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3.5 w-3.5" />
                              {formatDate(report.date)}
                            </span>
                            <span>•</span>
                            <span>{report.agent}</span>
                            <span>•</span>
                            <span>{report.size}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => downloadStoredReport(report.id, 'pdf')}
                          className="flex-shrink-0 bg-gradient-medical hover:opacity-90 transition-all group-hover:scale-105"
                        >
                          <Download className="h-4 w-4 mr-2" />
                          PDF
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => downloadStoredReport(report.id, 'excel')}
                          className="flex-shrink-0 bg-gradient-medical hover:opacity-90 transition-all group-hover:scale-105"
                        >
                          <Download className="h-4 w-4 mr-2" />
                          Excel
                        </Button>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => deleteStoredReport(report.id)}
                                  className="flex-shrink-0 ml-2 bg-red-600 hover:opacity-90 transition-all group-hover:scale-105"
                                >
                                  Delete
                                </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="shadow-card border-border/50">
              <CardHeader className="text-center py-12 md:py-16">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5">
                  <FileText className="h-8 w-8 text-primary" />
                </div>
                <CardTitle className="text-xl md:text-2xl">No Reports Found</CardTitle>
                <CardDescription className="text-sm md:text-base mt-2">
                  {searchQuery ? `No reports match "${searchQuery}"` : "Your generated reports will appear here once you run analyses with the AI agents"}
                </CardDescription>
              </CardHeader>
            </Card>
          )}
        </div>
      </main>
    </div>
  );
}
