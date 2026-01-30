import * as fs from 'fs';
import * as path from 'path';
import { SessionState } from './types';

const STATE_FILE = 'session_state.json';

export function loadState(outputDir: string): SessionState {
  const statePath = path.join(outputDir, STATE_FILE);
  if (fs.existsSync(statePath)) {
    try {
      const data = fs.readFileSync(statePath, 'utf-8');
      return JSON.parse(data) as SessionState;
    } catch (error) {
      console.error('Ошибка чтения файла состояния:', error);
      // Возвращаем состояние по умолчанию в случае ошибки
      return { appliedVacancyIds: [], ignoredVacancyIds: [] };
    }
  }
  // Возвращаем состояние по умолчанию, если файл не найден
  return { appliedVacancyIds: [], ignoredVacancyIds: [] };
}

export function saveState(outputDir: string, state: SessionState): void {
  const statePath = path.join(outputDir, STATE_FILE);
  try {
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    fs.writeFileSync(statePath, JSON.stringify(state, null, 2), 'utf-8');
  } catch (error) {
    console.error('Ошибка сохранения файла состояния:', error);
  }
}
