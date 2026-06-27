import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Servers from "./pages/Servers";
import Proxies from "./pages/Proxies";
import ProxyDetail from "./pages/ProxyDetail";
import Tools from "./pages/Tools";
import ToolDetail from "./pages/ToolDetail";
import Glossary from "./pages/Glossary";
import Analytics from "./pages/Analytics";
import Graph from "./pages/Graph";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/servers" element={<Servers />} />
        <Route path="/proxies" element={<Proxies />} />
        <Route path="/proxies/:id" element={<ProxyDetail />} />
        <Route path="/tools" element={<Tools />} />
        <Route path="/tools/:id" element={<ToolDetail />} />
        <Route path="/glossary" element={<Glossary />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/graph" element={<Graph />} />
      </Route>
    </Routes>
  );
}
