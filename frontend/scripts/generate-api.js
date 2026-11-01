import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const venvWin = path.resolve(__dirname, '../../backend/.venv/Scripts/python.exe');
const venvUnix = path.resolve(__dirname, '../../backend/.venv/bin/python');
const scriptPath = path.resolve(__dirname, '../../backend/app/generate_client.py');

let pythonPath = 'python';
if (fs.existsSync(venvWin)) {
  pythonPath = venvWin;
} else if (fs.existsSync(venvUnix)) {
  pythonPath = venvUnix;
}

execSync(`"${pythonPath}" "${scriptPath}"`, { stdio: 'inherit' });

