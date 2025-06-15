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

// Function to execute shell commands with environment variables
function runCommand(command, cwd, env = {}) {
  console.log(`Executing: ${command} in ${cwd}`);
  try {
    execSync(command, {
      stdio: 'inherit',
      cwd,
      env: { ...process.env, ...env }
    });
    console.log(`Successfully executed: ${command}`);
    return true;
  } catch (error) {
    console.error(`Error executing command: ${command}`);
    console.error(error);
    return false;
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

// 3. Determine Python executable path for virtual environment
const venvDir = path.join(backendDir, '.venv');
const venvPython = process.platform === 'win32'
  ? path.join(venvDir, 'Scripts', 'python.exe')
  : path.join(venvDir, 'bin', 'python3');

// 4. Create virtual environment if it doesn't exist
if (!fs.existsSync(venvDir)) {
  console.log('Creating Python virtual environment...');
  const pythonPath = process.platform === 'win32'
  ? 'python'
  : 'python3';
  const createVenvCommand = `${pythonPath} -m venv "${venvDir}"`;
  
  if (!runCommand(createVenvCommand, backendDir)) {
    console.error('Failed to create virtual environment');
    console.error('Please ensure Python 3.12 is installed and available in PATH');
    console.error('You can also set PYTHON_PATH environment variable to point to Python executable');
    process.exit(1);
  }
}

// 5. Check if virtual environment is valid
if (!fs.existsSync(venvPython)) {
  console.error(`Python executable not found in virtual environment: ${venvPython}`);
  console.error('This usually means the virtual environment was not created correctly.');
  console.error('Try deleting the .venv directory and running again:');
  console.error(`rmdir /s /q "${venvDir}"`);
  process.exit(1);
}

// 6. Install dependencies if not already installed
const checkDependenciesCommand = `"${venvPython}" -c "import pkg_resources; pkg_resources.require(open('requirements.txt', 'r'))"`;
try {
  execSync(checkDependenciesCommand, { stdio: 'ignore', cwd: backendDir });
  console.log('Python dependencies are already installed');
} catch (error) {
  console.log('Installing Python dependencies...');
  const installCommand = `"${venvPython}" -m pip install -r "${requirementsPath}"`;
  if (!runCommand(installCommand, backendDir)) {
    console.error('Failed to install dependencies');
    console.error('You can try manually running:');
    console.error(`cd backend && "${venvPython}" -m pip install -r requirements.txt`);
    process.exit(1);
  }
  console.log('\n==============================================');
  console.log('\n首次安装依赖成功！请重新运行 npm run dev');
  console.log('\nFIRST-TIME SETUP COMPLETE!');
  console.log('Please restart the development server:');
  console.log('  npm run dev');
  console.log('\n==============================================');
  process.exit(0);
}

// 7. Run the Python backend service
console.log(`Running backend service with: ${venvPython} ${mainPyPath}`);
runCommand(`"${venvPython}" "${mainPyPath}"`, projectRoot, {
  PYTHONPATH: backendDir
});

console.log('Backend run process completed.');
