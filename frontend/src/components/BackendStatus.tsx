import { useEffect, useState } from "react";
import { fetchHealth } from "../services/api";

type Status = "checking" | "online" | "offline";

export default function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [version, setVersion] = useState<string>("—");

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const data = await fetchHealth();
        if (cancelled) return;
        setStatus(data.status === "ok" ? "online" : "offline");
        setVersion(data.version);
      } catch {
        if (!cancelled) setStatus("offline");
      }
    };
    check();
    const id = setInterval(check, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const dot =
    status === "online"
      ? "bg-green-500"
      : status === "checking"
      ? "bg-yellow-500"
      : "bg-red-500";

  const label =
    status === "online"
      ? `Backend ONLINE · v${version}`
      : status === "checking"
      ? "Backend CHECKING…"
      : "Backend OFFLINE";

  return (
    <div className="flex items-center gap-2 text-xs text-white/60">
      <span className={`w-2 h-2 rounded-full ${dot}`} />
      <span>{label}</span>
    </div>
  );
}