import type { components } from "./schema";
export type Model<K extends keyof components["schemas"]> =
  components["schemas"][K];
export type Me = Model<"MeResponse">;
export type Session = Model<"SessionResponse">;
export type Overview = Model<"OverviewRead">;
export type Cup = Model<"CupDetail">;
