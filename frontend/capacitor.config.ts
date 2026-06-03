import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.smartdevops.assistant",
  appName: "Smart DevOps Assistant",
  webDir: "dist",
  backgroundColor: "#0b111d",
  server: {
    androidScheme: "http",
    cleartext: true,
  },
};

export default config;
