import { execSync } from 'child_process';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

// Get the directory where the script is located, which is /backend
const __filename = fileURLToPath(import.meta.url);
const backendDir = path.dirname(__filename);
const projectRoot = path.dirname(backendDir); // Assuming backend is a subdir of project root
const venvPath = path.join(backendDir, '.venv');
const requirementsPath = path.join(backendDir, 'requirements.txt');

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

console.log('Starting backend build process...');

// 1. Create a portable virtual environment in the script's directory
// Ensure the .venv directory is clean or doesn't exist to avoid issues with --relocatable
if (fs.existsSync(venvPath)) {
  console.log(`Removing existing virtual environment at ${venvPath}...`);
  fs.rmSync(venvPath, { recursive: true, force: true });
}
const venvCommand = `uv venv --relocatable ${venvPath}`;
runCommand(venvCommand, backendDir);

// 2. Use the created virtual environment to install requirements.txt
let pipInstallCommand;
const pythonExecutableName = process.platform === 'win32' ? 'python.exe' : 'python';
const pythonInVenvPath = process.platform === 'win32' ? path.join(venvPath, 'Scripts', pythonExecutableName) : path.join(venvPath, 'bin', pythonExecutableName);

if (!fs.existsSync(requirementsPath)) {
  console.warn(`Warning: ${requirementsPath} not found. Skipping pip install.`);
} else {
  // Using the Python from the created venv to ensure packages are installed in the correct environment
  // The command becomes `uv pip install -r requirements.txt --python path/to/.venv/bin/python`
  pipInstallCommand = `uv pip install -r ${requirementsPath} --python ${pythonInVenvPath}`;
  runCommand(pipInstallCommand, backendDir);
}

console.log('Backend build process completed.');
