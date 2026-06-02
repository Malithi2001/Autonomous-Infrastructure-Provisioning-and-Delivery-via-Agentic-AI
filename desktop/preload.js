const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("smartDevopsDesktop", {
  shell: "electron",
  platform: process.platform,
});

window.addEventListener("DOMContentLoaded", () => {
  document.documentElement.dataset.desktopShell = "electron";
});
