import { execSync } from 'child_process';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

// Get the directory where the script is located, which is /backend
const __filename = fileURLToPath(import.meta.url);
const backendDir = path.dirname(__filename);
const venvPath = path.join(backendDir, '.venv');
const mainPyPath = path.join(backendDir, 'main.py');

// Function to execute shell commands
function runCommand(command, cwd) {
  console.log(`Executing: ${command} in ${cwd}`);
  try {
    execSync(command, { stdio: 'inherit', cwd });
    console.log(`Successfully executed: ${command}`);
  } catch (error) {
    console.error(`Error executing command: ${command}`);
    console.error(error);
    process.exit(1);
  }
}

console.log('Starting backend run process...');

// 1. Check if the virtual environment exists
if (!fs.existsSync(venvPath)) {
  console.error(`Error: Virtual environment not found at ${venvPath}.`);
  console.error('Please run the build script (build.js) first to create the virtual environment and install dependencies.');
  process.exit(1);
}

// 2. Check if main.py exists
if (!fs.existsSync(mainPyPath)) {
  console.error(`Error: ${mainPyPath} not found.`);
  process.exit(1);
}

// 3. Use the Python from the created venv to run main.py
const pythonExecutableName = process.platform === 'win32' ? 'python.exe' : 'python';
const pythonInVenvPath = process.platform === 'win32' ? path.join(venvPath, 'Scripts', pythonExecutableName) : path.join(venvPath, 'bin', pythonExecutableName);

if (!fs.existsSync(pythonInVenvPath)) {
  console.error(`Error: Python executable not found in virtual environment at ${pythonInVenvPath}.`);
  console.error('The virtual environment might be corrupted. Try running the build script (build.js) again.');
  process.exit(1);
}

const runPythonCommand = `${pythonInVenvPath} ${mainPyPath}`;
runCommand(runPythonCommand, backendDir);

console.log('Backend run process completed.');

