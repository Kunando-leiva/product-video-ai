import { NavLink } from "react-router-dom";

const linkBase =
  "block px-4 py-2 rounded-lg text-sm font-medium transition-colors";
const linkIdle = "text-white/60 hover:text-white hover:bg-white/5";
const linkActive = "text-white bg-accent/20 border border-accent/40";

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 border-r border-white/5 bg-panel flex flex-col">
      <div className="px-5 py-5 border-b border-white/5">
        <div className="text-lg font-bold leading-tight">Product Video AI</div>
        <div className="text-[11px] text-white/40 mt-0.5">LOCAL EDITION</div>
      </div>

      <nav className="p-3 space-y-1">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `${linkBase} ${isActive ? linkActive : linkIdle}`
          }
        >
          🏠 Dashboard
        </NavLink>
        <NavLink
          to="/new"
          className={({ isActive }) =>
            `${linkBase} ${isActive ? linkActive : linkIdle}`
          }
        >
          ➕ Nuevo proyecto
        </NavLink>
        <NavLink
          to="/projects"
          className={({ isActive }) =>
            `${linkBase} ${isActive ? linkActive : linkIdle}`
          }
        >
          📁 Proyectos
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `${linkBase} ${isActive ? linkActive : linkIdle}`
          }
        >
          ⚙️ Configuración
        </NavLink>
      </nav>

      <div className="mt-auto p-4 text-[11px] text-white/30">
        v0.1.0 · Módulo 2
      </div>
    </aside>
  );
}