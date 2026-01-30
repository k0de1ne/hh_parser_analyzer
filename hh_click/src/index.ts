import * as readline from 'readline';
import { HHParser } from './parser';

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function askQuestion(question: string): Promise<string> {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer);
    });
  });
}

function printBanner(): void {
  console.log(`
╔═══════════════════════════════════════════════════════════════╗
║                  HH.RU AUTO APPLIER                           ║
║                 Авто-отклик на вакансии                       ║
╚═══════════════════════════════════════════════════════════════╝
`);
}

function printInstructions(): void {
  console.log(`
📋 ИНСТРУКЦИЯ:
───────────────────────────────────────────────────────────────
1. В открывшемся браузере залогиньтесь на hh.ru (ОБЯЗАТЕЛЬНО!)
2. Перейдите на страницу поиска вакансий
3. Настройте все нужные фильтры (регион, зарплата, опыт и т.д.)
4. Убедитесь, что вы видите список вакансий
5. Вернитесь в эту консоль и следуйте дальнейшим инструкциям
───────────────────────────────────────────────────────────────
`);
}

async function main(): Promise<void> {
  printBanner();

  const parser = new HHParser({
    delayMin: 1500,
    delayMax: 4500,
    outputDir: './output',
  });

  try {
    await parser.init();
    printInstructions();

    await askQuestion('\n⏳ Нажмите Enter когда будете готовы...');

    const currentUrl = parser.getCurrentUrl();
    if (!currentUrl.includes('hh.ru') || !currentUrl.includes('search/vacancy')) {
      console.log('\n⚠️  Внимание: Вы не на странице поиска вакансий!');
      console.log(`   Текущий URL: ${currentUrl}`);
      const proceed = await askQuestion('   Продолжить всё равно? (y/n): ');
      if (proceed.toLowerCase() !== 'y') {
        console.log('Отменено пользователем.');
        await parser.close();
        rl.close();
        return;
      }
    }

    console.log('\n🔍 Начинаем сбор ссылок на вакансии со всех страниц...');
    const urls = await parser.collectVacancyUrls();

    if (urls.length === 0) {
      console.log('✅ Новых вакансий для отклика не найдено. Все уже обработаны ранее.');
      await parser.close();
      rl.close();
      return;
    }

    console.log(`\n📊 Найдено ${urls.length} новых вакансий для обработки.`);
    const startApplying = await askQuestion('   Начать автоматические отклики? (y/n): ');

    if (startApplying.toLowerCase() !== 'y') {
      console.log('Отменено пользователем.');
      await parser.close();
      rl.close();
      return;
    }

    await parser.startAutoApply();

    const ignoredPath = parser.saveIgnoredVacancies();

    console.log(`\n
╔═══════════════════════════════════════════════════════════════╗
║                      РАБОТА ЗАВЕРШЕНА                         ║
╚═══════════════════════════════════════════════════════════════╝

✅ Процесс авто-откликов завершен.
📁 Список проигнорированных вакансий сохранен: ${ignoredPath}
`);

  } catch (error) {
    console.error('\n❌ Критическая ошибка:', error);
  } finally {
    const closeNow = await askQuestion('\nЗакрыть браузер? (y/n): ');
    if (closeNow.toLowerCase() === 'y') {
      await parser.close();
    }
    rl.close();
  }
}

main();
