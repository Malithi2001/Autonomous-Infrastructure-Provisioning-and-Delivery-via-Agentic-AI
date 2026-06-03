import type { User } from "@/types";

export const IS_DESKTOP_MODE =
  String(import.meta.env.VITE_DESKTOP_MODE || "false").toLowerCase() === "true";
export const IS_MOBILE_MODE =
  String(import.meta.env.VITE_MOBILE_MODE || "false").toLowerCase() === "true";
export const IS_AUTH_DISABLED =
  IS_DESKTOP_MODE ||
  String(import.meta.env.VITE_DISABLE_AUTH || "false").toLowerCase() === "true";

export const DESKTOP_HOME_PATH = "/dashboard";

export const LOCAL_USER: User = {
  id: IS_DESKTOP_MODE ? "desktop_user" : "mobile_user",
  email: IS_DESKTOP_MODE ? "desktop@local.app" : "mobile@local.app",
  username: IS_DESKTOP_MODE ? "Desktop User" : "Mobile User",
  role: "admin",
  is_active: true,
};
