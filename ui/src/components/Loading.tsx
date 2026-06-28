import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="flex items-center justify-center py-16">
      <Loader2 size={28} className="animate-spin text-slate-400" />
    </div>
  );
}
