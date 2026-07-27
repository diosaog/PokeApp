import type { EconomyConfig } from "@/domain/economy/types";
import type { TimeConfig } from "@/domain/scheduling/types";

export type RuleStatus = "confirmed" | "unconfirmed" | "user_configurable";

export interface RuleNotice {
  id: string;
  label: string;
  status: RuleStatus;
  details: string;
}

export type PowerItemMode =
  | "guarantee_and_counted"
  | "guarantee_then_fill"
  | "unconfirmed";

export type NonInheritedIvMode = "uniform_0_31" | "unknown";

export interface InheritanceRules {
  defaultInheritedStats: number;
  destinyKnotInheritedStats: number;
  powerItemMode: PowerItemMode;
  nonInheritedIvMode: NonInheritedIvMode;
  allowTwoPowerItems: boolean;
  sameStatPowerConflict: "invalid" | "choose_random_parent" | "unconfirmed";
}

export interface OffspringRules {
  speciesFollows: "mother" | "non_ditto_parent";
  dittoCanBreedWithGenderless: boolean;
  dittoCanBreedWithDitto: boolean;
  forcedSexAvailable: boolean;
  forcedSexAllowedForGenderless: boolean;
}

export interface ServerProfile {
  id: string;
  name: string;
  description: string;
  economy: EconomyConfig;
  time: TimeConfig;
  inheritance: InheritanceRules;
  offspring: OffspringRules;
  notices: RuleNotice[];
}
