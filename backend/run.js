import { execSync } from 'child_process';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

// Get the directory where the script is located, which is /backend
const __filename = fileURLToPath(import.meta.url);
const backendDir = path.dirname(__filename);
const projectRoot = path.dirname(backendDir); // Assuming backend is a subdir of project root
const mainPyPath = path.join(backendDir, 'main.py');
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

console.log('Starting backend run process...');

// 1. Check if main.py exists
if (!fs.existsSync(mainPyPath)) {
  console.error(`Error: ${mainPyPath} not found.`);
  process.exit(1);
}

// 2. Check if requirements.txt exists
if (!fs.existsSync(requirementsPath)) {
  console.error(`Error: ${requirementsPath} not found.`);
  process.exit(1);
}

// 3. Use uv run to execute main.py directly
const runPythonCommand = 'uv run -p 3.12 --with-requirements backend/requirements.txt backend/main.py';
runCommand(runPythonCommand, projectRoot);

console.log('Backend run process completed.');

