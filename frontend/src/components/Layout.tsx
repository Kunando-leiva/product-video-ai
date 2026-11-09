import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import BackendStatus from "./BackendStatus";

export default function Layout() {
  return (
    <div className="flex h-screen w-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-12 flex items-center justify-end px-4 border-b border-white/5 bg-panel/60 backdrop-blur">
          <BackendStatus />
        </header>
        <main className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}