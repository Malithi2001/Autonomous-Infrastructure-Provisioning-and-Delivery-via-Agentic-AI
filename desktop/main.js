const { app, BrowserWindow, dialog, shell } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");
const fs = require("fs");

let backendProcess = null;
let backendLogStream = null;

const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = process.env.SMART_DEVOPS_BACKEND_PORT || "8000";
const BACKEND_ORIGIN = `http://${BACKEND_HOST}:${BACKEND_PORT}`;

function desktopDataDir() {
  const dir = app.getPath("userData");
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function desktopDatabaseUrl() {
  const dbPath = path
    .join(desktopDataDir(), "devops_assistant.db")
    .replace(/\\/g, "/");
  return `sqlite+aiosqlite:///${dbPath}`;
}

function desktopLogStream() {
  if (backendLogStream) return backendLogStream;
  const logsDir = path.join(desktopDataDir(), "logs");
  fs.mkdirSync(logsDir, { recursive: true });
  backendLogStream = fs.createWriteStream(path.join(logsDir, "backend.log"), {
    flags: "a",
  });
  return backendLogStream;
}

function backendExecutablePath() {
  const executableName =
    process.platform === "win32"
      ? "smart-devops-backend.exe"
      : "smart-devops-backend";
  if (!app.isPackaged) {
    return path.join(__dirname, "..", "backend", "dist", executableName);
  }
  return path.join(process.resourcesPath, "backend", executableName);
}

function shouldStartBundledBackend() {
  if (process.env.SMART_DEVOPS_SKIP_BACKEND === "true") {
    return false;
  }

  if (process.env.ELECTRON_DEV_URL) {
    return false;
  }

  return true;
}

function startBundledBackend() {
  if (!shouldStartBundledBackend()) {
    return;
  }

  const exePath = backendExecutablePath();
  if (!fs.existsSync(exePath)) {
    return;
  }

  backendProcess = spawn(exePath, [], {
    env: {
      ...process.env,
      DESKTOP_MODE: "true",
      DISABLE_AUTH: "true",
      HOST: BACKEND_HOST,
      PORT: BACKEND_PORT,
      COOKIE_SECURE: "false",
      COOKIE_SAMESITE: "lax",
      DATABASE_URL: process.env.DATABASE_URL || desktopDatabaseUrl(),
      ALLOWED_ORIGINS: [
        "null",
        BACKEND_ORIGIN,
        `http://localhost:${BACKEND_PORT}`,
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "capacitor://localhost",
        "http://localhost",
      ].join(","),
    },
    cwd: desktopDataDir(),
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
  });

  const logStream = desktopLogStream();
  backendProcess.stdout?.pipe(logStream, { end: false });
  backendProcess.stderr?.pipe(logStream, { end: false });
  backendProcess.on("error", (error) => {
    logStream.write(`\n[backend process error] ${error.stack || error}\n`);
  });
  backendProcess.on("exit", (code, signal) => {
    logStream.write(
      `\n[backend exited] code=${code ?? "null"} signal=${signal ?? "null"}\n`,
    );
  });
}

function waitForBackend(timeoutMs = 12000) {
  const started = Date.now();
  return new Promise((resolve) => {
    function probe() {
      const req = http.get(`${BACKEND_ORIGIN}/health`, (res) => {
        res.resume();
        resolve(true);
      });
      req.on("error", () => {
        if (Date.now() - started >= timeoutMs) {
          resolve(false);
          return;
        }
        setTimeout(probe, 350);
      });
      req.setTimeout(800, () => {
        req.destroy();
      });
    }
    probe();
  });
}

async function createWindow() {
  const devUrl = process.env.ELECTRON_DEV_URL;
  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    title: "Smart DevOps Assistant",
    backgroundColor: "#0b111d",
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,
    },
  });

  win.once("ready-to-show", () => {
    win.show();
  });

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  win.webContents.on("will-navigate", (event, url) => {
    const isDevAppUrl = devUrl && url.startsWith(devUrl);
    const isLocalFile = url.startsWith("file://");
    const isBackendUrl = url.startsWith(BACKEND_ORIGIN);
    if (!isDevAppUrl && !isLocalFile && !isBackendUrl) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  if (devUrl) {
    win.loadURL(devUrl);
    return;
  }

  const indexPath = app.isPackaged
    ? path.join(process.resourcesPath, "frontend", "dist", "index.html")
    : path.join(__dirname, "..", "frontend", "dist", "index.html");
  win.loadFile(indexPath).catch((error) => {
    dialog.showErrorBox(
      "Frontend build missing",
      `Could not open ${indexPath}.\nRun make build-frontend first.\n\n${error}`,
    );
  });
}

app.whenReady().then(() => {
  if (process.platform === "win32") {
    app.setAppUserModelId("local.smart-devops-assistant.desktop");
  }

  startBundledBackend();
  waitForBackend().finally(createWindow);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
  if (backendLogStream) {
    backendLogStream.end();
    backendLogStream = null;
  }
});
