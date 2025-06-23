import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import CreateVideo from "./pages/CreateVideo";
import Processing from "./pages/Processing";
import Preview from "./pages/Preview";
import NotFound from "./pages/NotFound";
import Record from "./pages/Record";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/create" element={<CreateVideo />} />
          <Route path="/processing" element={<Processing />} />
          <Route path="/preview" element={<Preview />} />
          <Route path="/preview/:videoId" element={<Preview />} />
          <Route path="/record" element={<Record />} />

          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
