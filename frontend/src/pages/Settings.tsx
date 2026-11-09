import { useState } from "react";
import AIPanel from "../components/AIPanel";

type Section =
  | "General"
  | "IA"
  | "Modelos"
  | "Voz"
  | "Subtítulos"
  | "Video"
  | "Exportación"
  | "Integraciones"
  | "Logs";

const SECTIONS: Section[] = [
  "General",
  "IA",
  "Modelos",
  "Voz",
  "Subtítulos",
  "Video",
  "Exportación",
  "Integraciones",
  "Logs",
];

export default function Settings() {
  const [current, setCurrent] = useState<Section>("IA");

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">Configuración</h1>
      <p className="text-white/50 text-sm mb-8">
        Ajustes de la aplicación. Algunas secciones se habilitan en módulos
        posteriores.
      </p>

      <div className="grid grid-cols-3 gap-6">
        <nav className="space-y-1">
          {SECTIONS.map((s) => (
            <button
              key={s}
              onClick={() => setCurrent(s)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                current === s
                  ? "bg-accent/20 border border-accent/40 text-white"
                  : "text-white/60 hover:bg-white/5"
              }`}
            >
              {s}
            </button>
          ))}
        </nav>

        <div className="col-span-2">
          {current === "IA" ? (
            <AIPanel />
          ) : (
            <div className="border border-white/5 rounded-xl bg-panel/60 p-8 text-center text-white/40 text-sm">
              La sección “{current}” estará disponible en un módulo posterior.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}