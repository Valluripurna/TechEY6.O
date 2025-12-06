import { useState, useRef, useEffect } from "react";
import { Sidebar } from "@/components/Sidebar";
import { MobileHeader } from "@/components/MobileHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Bot, User, Send, Mic, MicOff, Download } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string | Record<string, any>;
  timestamp: Date;
}

export default function Chat() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      const saved = sessionStorage.getItem('chatMessages');
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        }));
      }
    } catch {}
    return [
      {
        id: "1",
        role: "assistant",
        content: "Hello! I'm your AI assistant. Ask me about pharmaceutical research, market data, or clinical trials.",
        timestamp: new Date(),
      },
    ];
  });
  const [input, setInput] = useState(() => {
    try {
      return sessionStorage.getItem('chatInput') || "";
    } catch {
      return "";
    }
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  const API = (import.meta.env && import.meta.env.VITE_API_URL) || 'http://localhost:4000';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    try {
      sessionStorage.setItem('chatMessages', JSON.stringify(messages));
    } catch {}
  }, [messages]);

  useEffect(() => {
    try {
      sessionStorage.setItem('chatInput', input);
    } catch {}
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    const currentInput = input;

    try {
      // Define endpoints with their specific parameters
      const endpoints = [
        { 
          name: 'exim', 
          params: (query: string) => `hs_code=3004&top_n=10` // Default HS code for pharmaceutical products
        },
        { 
          name: 'trials', 
          params: (query: string) => `condition=${encodeURIComponent(query)}&top_n=10`
        },
        { 
          name: 'patents', 
          params: (query: string) => `query=${encodeURIComponent(query)}&top_n=10`
        },
        { 
          name: 'web-intel', 
          params: (query: string) => `query=${encodeURIComponent(query)}&num_results=5`
        },
        { 
          name: 'internal-docs', 
          params: (query: string) => `query=${encodeURIComponent(query)}&top_n=5`
        },
        { 
          name: 'iqvia', 
          params: (query: string) => `therapy_area=${encodeURIComponent(query)}` // Or empty for general market
        }
      ];
      
      const promises = endpoints.map(endpoint =>
        fetch(`${API}/api/${endpoint.name}?${endpoint.params(currentInput)}`)
          .then(res => {
            if (!res.ok) {
              return res.json().then(err => { throw new Error(err.error || `API Error on ${endpoint.name}`) });
            }
            return res.json();
          })
      );
      
      const responses = await Promise.allSettled(promises);
      const newResults = {};
      let hasResults = false;

      responses.forEach((result, i) => {
        const endpointName = endpoints[i].name;
        // Format endpoint name for display
        const key = endpointName
          .replace(/-/g, ' ')
          .replace(/\b\w/g, l => l.toUpperCase());
          
        if (result.status === 'fulfilled' && result.value) {
          newResults[key] = result.value;
          hasResults = true;
        } else if (result.status === 'rejected') {
          newResults[key] = { error: 'Failed to fetch data' };
          console.error(`Failed to fetch from ${endpointName}:`, result.reason);
        }
      });

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: hasResults ? newResults : "No relevant data found for your query.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);

    } catch (error) {
      console.error("Error fetching search results:", error);
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "An error occurred while processing your request. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateReport = async (reportType: 'pdf' | 'excel' | 'text' = 'excel') => {
    const lastMessage = messages[messages.length - 1];
    if (!lastMessage || lastMessage.role !== 'assistant' || typeof lastMessage.content === 'string') {
      toast({ title: "No results to generate a report from.", variant: "destructive" });
      return;
    }
    // Determine query text from last user message for better report context
    let queryText = input;
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === 'user' && typeof m.content === 'string' && m.content.trim()) {
        queryText = m.content as string;
        break;
      }
    }

    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers: any = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${API}/api/generate-report`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ 
          query: queryText, 
          results: lastMessage.content,
          type: reportType
        })
      });
      if (!res.ok) {
        // Try parse error JSON
        let errMsg = 'Failed to generate report';
        try {
          const err = await res.json();
          errMsg = err.error || err.msg || errMsg;
        } catch {}
        throw new Error(errMsg);
      }

      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const data = await res.json();
        // Expecting { report_id, download_url }
        if (data && data.download_url && data.report_id) {
          const token = localStorage.getItem('token');
          const dlHeaders: any = {};
          if (token) dlHeaders['Authorization'] = `Bearer ${token}`;
          const dlResp = await fetch(`${API}${data.download_url}`, { headers: dlHeaders });
          if (!dlResp.ok) {
            const txt = await dlResp.text().catch(() => '');
            throw new Error(txt || 'Failed to download generated report');
          }
          const blob = await dlResp.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `pharma-report-${new Date().toISOString().slice(0, 10)}.${reportType === 'pdf' ? 'pdf' : 'xlsx'}`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
        } else {
          throw new Error('Report generated but download URL missing');
        }
      } else {
        // Fallback for raw file response
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `pharma-report-${new Date().toISOString().slice(0, 10)}.${reportType === 'pdf' ? 'pdf' : 'xlsx'}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      }

    } catch (error) {
      console.error("Error generating report:", error);
      toast({ title: "Error generating report: " + (error.message || "Unknown error"), variant: "destructive" });
    } finally {
      setIsLoading(false);
    }
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
    toast({
      title: isRecording ? "Recording Stopped" : "Recording Started",
      description: isRecording
        ? "Processing your audio message..."
        : "Speak now to send an audio message",
    });
  };

  // Function to render structured data in a more readable format
  const renderStructuredData = (data: any) => {
    if (!data) return <p>No data available</p>;
    
    // Handle empty data
    if (Array.isArray(data) && data.length === 0) {
      return <p>No data available</p>;
    }
    
    if (typeof data === 'object' && Object.keys(data).length === 0) {
      return <p>No data available</p>;
    }
    
    // Handle error cases
    if (data.error) {
      return <p className="text-red-500">Error: {data.error}</p>;
    }
    
    // Handle data wrapped in {data: [...]} format (most common from our API)
    const actualData = data.data || data;
    
    // Handle Clinical Trials data
    if (Array.isArray(actualData) && actualData.some(item => item.nct_id || item.title)) {
      if (actualData.length === 0) {
        return <p>No clinical trials found</p>;
      }
      
      return (
        <div className="space-y-4">
          <p className="font-semibold">Found {actualData.length} clinical trials</p>
          <div className="grid gap-3">
            {actualData.map((study: any, idx: number) => (
              <div key={idx} className="border rounded p-3">
                <h4 className="font-medium">{study.title}</h4>
                <div className="text-sm text-muted-foreground mt-1">
                  {study.nct_id && <p>ID: {study.nct_id || study.nctId}</p>}
                  {study.status && <p>Status: {study.status}</p>}
                  {study.phase && <p>Phase: {study.phase}</p>}
                  {study.sponsor && <p>Sponsor: {study.sponsor}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }
    
    // Handle Patent data
    if (Array.isArray(actualData) && actualData.some(item => item.patent_id || item.assignee)) {
      if (actualData.length === 0) {
        return <p>No patents found</p>;
      }
      
      return (
        <div className="space-y-4">
          <p className="font-semibold">Found {actualData.length} patents</p>
          <div className="grid gap-3">
            {actualData.map((patent: any, idx: number) => (
              <div key={idx} className="border rounded p-3">
                <h4 className="font-medium">{patent.title}</h4>
                <div className="text-sm text-muted-foreground mt-1">
                  {patent.patent_id && <p>Patent ID: {patent.patent_id || patent.id}</p>}
                  {patent.assignee && <p>Assignee: {patent.assignee}</p>}
                  {patent.filing_date && <p>Filing Date: {patent.filing_date || patent.filingDate}</p>}
                  {patent.grant_date && <p>Grant Date: {patent.grant_date || patent.grantDate}</p>}
                  {patent.expiry_date && <p>Expiry Date: {patent.expiry_date}</p>}
                  {patent.ipc_codes && <p>IPC Codes: {patent.ipc_codes.join(', ')}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }
    
    // Handle EXIM/Trade data
    if (Array.isArray(actualData) && actualData.some(item => item.partner || item.value)) {
      if (actualData.length === 0) {
        return <p>No trade data found</p>;
      }
      
      return (
        <div className="space-y-4">
          <p className="font-semibold">Found {actualData.length} trade partners</p>
          <div className="grid gap-3">
            {actualData.map((item: any, idx: number) => (
              <div key={idx} className="border rounded p-3">
                <h4 className="font-medium">{item.partner || item.country}</h4>
                <div className="text-sm text-muted-foreground mt-1">
                  {item.value && <p>Value: ${Number(item.value || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>}
                  {item.quantity && <p>Quantity: {Number(item.quantity).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>}
                  {item.product_description && <p>Product: {item.product_description}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }
    
    // Handle IQVIA data
    if (actualData.market_stats || actualData.competitors || actualData.trends) {
      const iqviaData = actualData;
      
      return (
        <div className="space-y-4">
          {iqviaData.market_stats && (
            <div className="border rounded p-3">
              <h4 className="font-medium">Market Statistics</h4>
              <div className="text-sm text-muted-foreground mt-1">
                <p>Therapy Area: {iqviaData.market_stats.therapy_area}</p>
                <p>Current Value: {iqviaData.market_stats.current_value}</p>
                <p>Projected Value: {iqviaData.market_stats.projected_value}</p>
                <p>CAGR: {iqviaData.market_stats.cagr}%</p>
              </div>
            </div>
          )}
          
          {iqviaData.competitors && iqviaData.competitors.length > 0 && (
            <div className="border rounded p-3">
              <h4 className="font-medium">Top Competitors</h4>
              <div className="grid gap-2 mt-2">
                {iqviaData.competitors.map((competitor: any, idx: number) => (
                  <div key={idx} className="flex justify-between">
                    <span>{competitor.name}</span>
                    <span>{competitor.market_share} ({competitor.revenue})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {iqviaData.trends && iqviaData.trends.length > 0 && (
            <div className="border rounded p-3">
              <h4 className="font-medium">Market Trends</h4>
              <div className="grid gap-2 mt-2">
                {iqviaData.trends.map((trend: any, idx: number) => (
                  <div key={idx} className="flex justify-between">
                    <span>#{trend.rank} {trend.trend}</span>
                    <span>Impact Score: {trend.impact_score}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }
    
    // Handle Web Intel data
    if (Array.isArray(actualData) && actualData.some(item => item.title || item.url)) {
      if (actualData.length === 0) {
        return <p>No web intelligence data found</p>;
      }
      
      return (
        <div className="space-y-4">
          <p className="font-semibold">Found {actualData.length} web search results</p>
          <div className="grid gap-3">
            {actualData.map((item: any, idx: number) => (
              <div key={idx} className="border rounded p-3">
                <h4 className="font-medium">{item.title}</h4>
                <div className="text-sm text-muted-foreground mt-1">
                  {item.snippet && <p className="mt-2">{item.snippet}</p>}
                  {item.link && <p className="mt-2">Source: <a href={item.link} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">{item.source || item.link}</a></p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }
    
    // Handle Internal Docs data
    if (Array.isArray(actualData) && actualData.some(item => item.title || item.doc_id)) {
      if (actualData.length === 0) {
        return <p>No internal documents found</p>;
      }
      
      return (
        <div className="space-y-4">
          <p className="font-semibold">Found {actualData.length} documents</p>
          <div className="grid gap-3">
            {actualData.map((item: any, idx: number) => (
              <div key={idx} className="border rounded p-3">
                <h4 className="font-medium">{item.title}</h4>
                <div className="text-sm text-muted-foreground mt-1">
                  {item.text_excerpt && <p className="mt-2">{item.text_excerpt}</p>}
                  {item.uploaded_by && <p className="mt-2">Author: {item.uploaded_by}</p>}
                  {item.uploaded_at && <p className="mt-1">Date: {new Date(item.uploaded_at).toLocaleDateString()}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      );
    }
    
    // Generic object display for any other structured data
    if (typeof actualData === 'object' && !Array.isArray(actualData)) {
      // Check if it's a simple object with key-value pairs
      const keys = Object.keys(actualData);
      if (keys.length > 0 && keys.every(key => typeof actualData[key] !== 'object')) {
        return (
          <div className="border rounded p-3">
            <div className="grid gap-2">
              {keys.map((key, idx) => (
                <div key={idx} className="flex justify-between">
                  <span className="font-medium">{key}:</span>
                  <span>{String(actualData[key])}</span>
                </div>
              ))}
            </div>
          </div>
        );
      }
      
      // For complex objects, show JSON
      return (
        <div className="border rounded p-3">
          <pre className="text-xs overflow-auto">
            {JSON.stringify(actualData, null, 2)}
          </pre>
        </div>
      );
    }
    
    // Handle arrays of simple data
    if (Array.isArray(actualData)) {
      if (actualData.length === 0) {
        return <p>No data available</p>;
      }
      
      return (
        <div className="border rounded p-3">
          <ul className="list-disc pl-5 space-y-1">
            {actualData.map((item: any, idx: number) => (
              <li key={idx}>{typeof item === 'object' ? JSON.stringify(item) : String(item)}</li>
            ))}
          </ul>
        </div>
      );
    }
    
    // Fallback for any other data
    return <p>{String(actualData)}</p>;
  };

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <MobileHeader onMenuClick={() => setSidebarOpen(true)} />
      
      <main className="flex flex-1 flex-col md:ml-64 pt-14 md:pt-0">
        <div className="border-b border-border bg-card/50 backdrop-blur-sm px-4 md:px-6 py-3 md:py-4 shadow-sm">
          <h1 className="text-xl md:text-2xl font-bold text-foreground">AI Chat Assistant</h1>
          <p className="text-xs md:text-sm text-muted-foreground">
            Ask questions about pharmaceutical data, market insights, and research
          </p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-3 md:p-6">
          <div className="mx-auto max-w-3xl space-y-4 md:space-y-6">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-2 md:gap-4 ${
                  message.role === "user" ? "flex-row-reverse" : ""
                }`}
              >
                <div
                  className={`flex h-8 w-8 md:h-10 md:w-10 shrink-0 items-center justify-center rounded-full ${
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {message.role === "user" ? <User size={20} /> : <Bot size={20} />}
                </div>
                <Card
                  className={`max-w-[85%] rounded-2xl ${
                    message.role === "user"
                      ? "rounded-br-none bg-primary text-primary-foreground"
                      : "rounded-bl-none"
                  }`}
                >
                  <CardContent className="p-3 md:p-4 text-sm md:text-base">
                    {typeof message.content === 'string' ? (
                      <p style={{ whiteSpace: 'pre-wrap' }}>{message.content}</p>
                    ) : (
                      <div>
                        <div className="flex justify-between items-center mb-3">
                          <h3 className="font-bold">Agentic Search Results:</h3>
                          <div className="flex gap-2">
                            <Button size="sm" onClick={() => handleGenerateReport('excel')} disabled={isLoading}>
                              <Download className="h-4 w-4 mr-2" />
                              Excel Report
                            </Button>
                            <Button size="sm" onClick={() => handleGenerateReport('pdf')} disabled={isLoading}>
                              <Download className="h-4 w-4 mr-2" />
                              PDF
                            </Button>
                          </div>
                        </div>
                        <div className="space-y-4">
                          {Object.entries(message.content).map(([key, value]) => (
                            <div key={key} className="border rounded-lg p-3">
                              <details className="group">
                                <summary className="font-semibold cursor-pointer list-none flex justify-between items-center">
                                  <span>{key}</span>
                                  <span className="text-xs group-open:rotate-180 transition-transform">▼</span>
                                </summary>
                                <div className="mt-3 pl-2">
                                  {renderStructuredData(value)}
                                </div>
                              </details>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    <p className="mt-2 text-xs text-right opacity-70">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </CardContent>
                </Card>
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-2 md:gap-4">
                <div className="flex h-8 w-8 md:h-10 md:w-10 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                  <Bot size={20} />
                </div>
                <Card className="max-w-[85%] rounded-2xl rounded-bl-none">
                  <CardContent className="p-3 md:p-4 text-sm md:text-base">
                    <p>Searching and analyzing data...</p>
                    <div className="mt-2 flex space-x-2">
                      <div className="w-2 h-2 rounded-full bg-primary animate-bounce"></div>
                      <div className="w-2 h-2 rounded-full bg-primary animate-bounce delay-75"></div>
                      <div className="w-2 h-2 rounded-full bg-primary animate-bounce delay-150"></div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="border-t border-border bg-card/70 p-3 md:p-4">
          <div className="mx-auto max-w-3xl">
            <div className="relative">
              <Input
                placeholder="Ask about a molecule, disease, or patent..."
                className="pr-24 md:pr-28"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                disabled={isLoading}
              />
              <div className="absolute inset-y-0 right-2 flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleRecording}
                  className="text-muted-foreground"
                  disabled={isLoading}
                >
                  {isRecording ? (
                    <MicOff className="h-5 w-5" />
                  ) : (
                    <Mic className="h-5 w-5" />
                  )}
                </Button>
                <Button size="icon" onClick={handleSend} disabled={isLoading}>
                  <Send className="h-5 w-5" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}