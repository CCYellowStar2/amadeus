const { app, BrowserWindow, ipcMain } = require('electron');
const { join, resolve } = require('path');
const { spawn } = require('child_process');
const { existsSync } = require('fs');
const { platform } = require('os');

let mainWindow;
let serverProcess;
let serverPort;
let serverStarted = false;

// 默认服务器配置
const defaultServerConfig = {
  // 相对于安装路径的执行路径
  execPath: 'backend',
  // 启动命令和参数
  nt_command: 'backend.exe',
  posix_command: './backend',
  args: [],
  // 环境变量
  env: {
    ELECTRON: 'true',
    FORCE_COLOR: '1'
  },
  // 端口匹配正则表达式
  portRegex: /https?:\/\/(?:localhost|127\.0\.0\.1):(\d+)/i,
  // 启动超时时间（毫秒）
  timeout: 10000
};

/**
 * 启动后端服务
 * @param {Object} config - 服务器配置
 * @param {string} config.execPath - 相对于安装路径的执行路径
 * @param {string} config.command - 启动命令
 * @param {string[]} config.args - 命令参数
 * @param {Object} config.env - 环境变量
 * @param {RegExp} config.portRegex - 端口匹配正则表达式
 * @param {number} config.timeout - 启动超时时间（毫秒）
 * @returns {Promise<number>} - 返回服务器端口
 */
async function startServer(config = defaultServerConfig) {
  // 如果服务器已经启动，直接返回端口
  if (serverStarted && serverPort) {
    return serverPort;
  }

  // 合并配置
  const serverConfig = { ...defaultServerConfig, ...config };
  
  // 根据平台调整命令（Windows 需要添加 .cmd 或 .exe 后缀）
  let command = serverConfig.posix_command;
  if (platform() === 'win32') {
    command = serverConfig.nt_command;
  }
  
  // 解析服务器脚本路径
  const basePath = app.isPackaged
    ? join(process.resourcesPath, serverConfig.execPath)
    : join(__dirname, '..', 'dist', serverConfig.execPath);
  
  // 解析完整的参数路径
  const fullArgs = serverConfig.args.map(arg => {
    // 如果参数是一个文件路径（不包含空格和特殊字符），则解析为完整路径
    if (/^[^/\\]*\.[^/\\]+$/.test(arg)) {
      return join(basePath, arg);
    }
    return arg;
  });
  
  // 检查主要脚本文件是否存在
  const mainScript = fullArgs.find(arg => /\.(js|ts|py|rb|php|exe)$/i.test(arg));
  if (mainScript && !existsSync(mainScript)) {
    console.error('Server script not found:', mainScript);
    throw new Error(`Server script not found: ${mainScript}`);
  }

  return new Promise((resolve, reject) => {
    console.log(`[Server] Starting with command: ${command} ${fullArgs.join(' ')}`);
    console.log(`[Server] Working directory: ${basePath}`);
    
    serverProcess = spawn(command, fullArgs, {
      stdio: ['pipe', 'pipe', 'pipe', 'ipc'],
      env: {
        ...process.env,
        ...serverConfig.env
      },
      cwd: basePath
    });

    let buffer = '';
    let portResolved = false; // 添加标志位防止重复匹配
    
    const checkPortInBuffer = (data) => {
      if (portResolved) return; // 如果已经匹配成功，直接返回
      
      buffer += data.toString();
      
      // 从累积的缓冲区中查找端口
      const portMatch = buffer.match(serverConfig.portRegex);
      if (portMatch && !portResolved) {
        portResolved = true; // 设置标志位，防止重复匹配
        serverPort = parseInt(portMatch[1], 10);
        serverStarted = true;
        resolve(serverPort);
        buffer = ''; // 找到端口后清除缓冲区
      }
    };

    serverProcess.stdout.on('data', (data) => {
      console.log('[Server]', data.toString().trim());
      checkPortInBuffer(data);
    });

    serverProcess.stderr.on('data', (data) => {
      console.error('[Server Error]', data.toString().trim());
      checkPortInBuffer(data);
    });

    serverProcess.on('error', (error) => {
      console.error('[Server] Failed to start process:', error);
      reject(error);
    });

    serverProcess.on('close', (code) => {
      console.log('[Server] Process exited with code', code);
      if (code !== 0 && !app.isQuitting) {
        console.log('[Server] Restarting server...');
        serverStarted = false;
        startServer(serverConfig).then(resolve).catch(reject);
      }
    });

    // 超时
    setTimeout(() => {
      if (!serverStarted) {
        reject(new Error(`Server startup timeout after ${serverConfig.timeout}ms`));
      }
    }, serverConfig.timeout);
  });
}

// 注册IPC处理程序，只需注册一次
function registerIPCHandlers() {
  if (!ipcMain.listenerCount('get-api-port')) {
    ipcMain.handle('get-api-port', () => serverPort);
  }
}

async function createWindow() {
  // 启动服务器（如果尚未启动）并获取端口
  try {
    serverPort = await startServer();
    serverStarted = true;
  } catch (error) {
    console.error('Failed to start server:', error);
    app.quit();
    return;
  }

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173/');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  registerIPCHandlers();
  createWindow();
});

app.on('activate', function () {
  // 在 macOS 上，当点击 dock 图标并且没有其他窗口打开时，
  // 通常在应用程序中重新创建一个窗口。
  if (BrowserWindow.getAllWindows().length === 0) {
    // 服务器已经启动，只需创建新窗口
    createWindow();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
  if (serverProcess) {
    serverProcess.kill();
  }
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') {
    app.isQuitting = true;
    app.quit();
  }
});
