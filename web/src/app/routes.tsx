import type { LucideIcon } from "lucide-react";
import { Boxes, ClipboardList, History, Settings2, Target } from "lucide-react";

import type { ActivePage } from "@/state/sessionStore";

export interface AppRoute {
  id: ActivePage;
  label: string;
  icon: LucideIcon;
}

export const routes: AppRoute[] = [
  { id: "setup", label: "Ajustes", icon: Settings2 },
  { id: "breeders", label: "Criadero", icon: Boxes },
  { id: "target", label: "Objetivo", icon: Target },
  { id: "optimize", label: "Optimizar", icon: ClipboardList },
  { id: "history", label: "Historial", icon: History },
];
