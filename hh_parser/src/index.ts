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
║                    HH.RU VACANCY PARSER                       ║
║                      Парсер вакансий                          ║
╚═══════════════════════════════════════════════════════════════╝
`);
}

function printInstructions(): void {
  console.log(`
📋 ИНСТРУКЦИЯ:
───────────────────────────────────────────────────────────────
1. В открывшемся браузере залогиньтесь на hh.ru (если нужно)
2. Перейдите на страницу поиска вакансий
3. Настройте все нужные фильтры (регион, зарплата, опыт и т.д.)
4. Убедитесь, что вы видите список вакансий
5. Вернитесь в эту консоль и нажмите Enter для старта парсинга
───────────────────────────────────────────────────────────────
`);
}

async function main(): Promise<void> {
  printBanner();

  const parser = new HHParser({
    delayMin: 1500,
    delayMax: 3500,
    outputDir: './output',
  });

  try {
    // Запускаем браузер
    await parser.init();
    printInstructions();

    // Ждем готовности пользователя
    await askQuestion('\n⏳ Нажмите Enter когда будете готовы начать парсинг...');

    // Проверяем, что мы на странице поиска
    const currentUrl = parser.getCurrentUrl();
    if (!currentUrl.includes('hh.ru') || !currentUrl.includes('search/vacancy')) {
      console.log('\n⚠️  Внимание: Вы не на странице поиска вакансий!');
      console.log(`   Текущий URL: ${currentUrl}`);
      const proceed = await askQuestion('   Продолжить всё равно? (y/n): ');
      if (proceed.toLowerCase() !== 'y') {
        console.log('Парсинг отменен.');
        await parser.close();
        rl.close();
        return;
      }
    }

    // Собираем ссылки на вакансии
    console.log('\n🔍 Начинаем сбор ссылок на вакансии...');
    const urls = await parser.collectVacancyUrls();

    if (urls.length === 0) {
      console.log('❌ Вакансии не найдены. Проверьте страницу поиска.');
      await parser.close();
      rl.close();
      return;
    }

    console.log(`\n📊 Найдено ${urls.length} вакансий для парсинга.`);
    const startParsing = await askQuestion('   Начать парсинг? (y/n): ');

    if (startParsing.toLowerCase() !== 'y') {
      console.log('Парсинг отменен.');
      await parser.close();
      rl.close();
      return;
    }

    // Парсим каждую вакансию
    console.log('\n🚀 Запуск парсинга вакансий...');
    const vacancies = await parser.parseAllVacancies((progress) => {
      const percent = Math.round((progress.parsedVacancies / progress.totalVacancies) * 100);
      process.stdout.write(`\r   Прогресс: ${percent}% (${progress.parsedVacancies}/${progress.totalVacancies})`);
    });

    // Сохраняем результаты
    const outputPath = parser.saveResults();

    console.log(`\n
╔═══════════════════════════════════════════════════════════════╗
║                      ПАРСИНГ ЗАВЕРШЕН                         ║
╚═══════════════════════════════════════════════════════════════╝

✅ Успешно собрано: ${vacancies.length} вакансий
📁 Результаты сохранены: ${outputPath}
`);

  } catch (error) {
    console.error('\n❌ Ошибка:', error);
  } finally {
    const closeNow = await askQuestion('\nЗакрыть браузер? (y/n): ');
    if (closeNow.toLowerCase() === 'y') {
      await parser.close();
    }
    rl.close();
  }
}

main();
