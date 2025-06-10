const { app } = require('electron');

/**
 * Gracefully starts and stops a child process.
 */
class GracefulKiller {
  constructor() {
    this.serverProcess = null;
    this.isQuitting = false;
    this.gracefulKillTimeout = 5000; // 5 seconds
    
    app.on('before-quit', (event) => {
      if (this.isQuitting) {
        return;
      }
      this.isQuitting = true;
      if (this.serverProcess && !this.serverProcess.killed) {
        event.preventDefault(); // Prevent app from quitting immediately
        this.kill(this.serverProcess).then(() => {
          this.isQuitting = true;
          app.quit();
        });
      }
    });
  }

  setServerProcess(proc) {
    this.serverProcess = proc;
  }
  
  /**
   * Kills the process, first with SIGTERM, then with SIGKILL after a timeout.
   * @param {ChildProcess} processToKill - The process to kill.
   * @returns {Promise<void>}
   */
  kill(processToKill) {
    return new Promise((resolve) => {
      if (!processToKill || processToKill.killed) {
        resolve();
        return;
      }
      
      const timeout = setTimeout(() => {
        console.log('[GracefulKiller] Process did not exit gracefully, forcing kill.');
        processToKill.kill('SIGKILL');
      }, this.gracefulKillTimeout);
      
      processToKill.on('exit', () => {
        clearTimeout(timeout);
        console.log('[GracefulKiller] Process exited gracefully.');
        resolve();
      });
      
      console.log('[GracefulKiller] Attempting to kill process gracefully...');
      processToKill.kill('SIGTERM');
    });
  }
}

module.exports = { GracefulKiller }; 