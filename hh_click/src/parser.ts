import { chromium, Browser, Page, BrowserContext } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import {
  Vacancy,
  ParserConfig,
  Salary,
  Contacts,
  ParsingProgress,
  SessionState,
  IgnoredVacancy,
} from './types';
import { loadState, saveState } from './state';

export class HHParser {
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private config: ParserConfig;
  private vacancies: Vacancy[] = [];
  private ignoredVacancies: IgnoredVacancy[] = [];
  private responseLinks: string[] = [];
  private state: SessionState;

  constructor(config: Partial<ParserConfig> = {}) {
    this.config = {
      delayMin: 1000,
      delayMax: 3000,
      maxPages: null,
      outputDir: './output',
      ...config,
    };
    this.state = loadState(this.config.outputDir);
  }

  async init(): Promise<Page> {
    console.log('Запуск браузера с сохранением сессии...');
    const userDataDir = path.join(this.config.outputDir, 'user-data');
    
    this.context = await chromium.launchPersistentContext(userDataDir, {
      headless: false,
      args: ['--start-maximized'],
      viewport: null,
      locale: 'ru-RU',
    });

    this.page = this.context.pages().length > 0 ? this.context.pages()[0] : await this.context.newPage();
    
    // Если в контексте нет открытых страниц, или они все about:blank, откроем нужную
    const openPages = this.context.pages();
    if (openPages.length === 0 || openPages.every(p => p.url() === 'about:blank')) {
        if(openPages.length > 1) {
            // Закроем лишние пустые страницы, если они есть
            for(let i = 1; i < openPages.length; i++) {
                await openPages[i].close();
            }
        }
        this.page = openPages.length > 0 ? openPages[0] : await this.context.newPage();
        await this.page.goto('https://hh.ru');
    } else {
        // Если есть уже открытая страница (например, с прошлого запуска), используем ее
        this.page = openPages[0];
        console.log(`Используем существующую сессию. Текущая страница: ${this.page.url()}`);
    }

    console.log('Браузер готов к работе.');
    return this.page;
  }

  async close(): Promise<void> {
    if (this.context) {
      await this.context.close();
    }
  }

  private async delay(): Promise<void> {
    const ms = Math.random() * (this.config.delayMax - this.config.delayMin) + this.config.delayMin;
    await new Promise(resolve => setTimeout(resolve, ms));
  }

  async collectVacancyUrls(): Promise<string[]> {
    if (!this.page) throw new Error('Browser not initialized');

    const urls: string[] = [];
    let currentPage = 1;
    let hasNextPage = true;

    console.log('\nСбор ссылок на вакансии...');

    while (hasNextPage) {
      console.log(`Страница ${currentPage}...`);

      await this.page.waitForSelector('[data-qa="vacancy-serp__results"]', { timeout: 10000 }).catch(() => null);

      const responseLinksFromPage = await this.page.$$eval(
        'a[data-qa="vacancy-serp__vacancy_response"]',
        (links) => links.map((a) => (a as HTMLAnchorElement).href)
      );

      urls.push(...responseLinksFromPage);
      console.log(`  Найдено ${responseLinksFromPage.length} откликов на странице`);

      if (this.config.maxPages && currentPage >= this.config.maxPages) {
        console.log(`Достигнут лимит страниц (${this.config.maxPages})`);
        break;
      }

      const nextButton = await this.page.$('[data-qa="pager-next"]');
      if (nextButton) {
        await nextButton.click();
        await this.delay();
        await this.page.waitForSelector('[data-qa="vacancy-serp__results"]', { timeout: 15000 }).catch(() => null);
        currentPage++;
      } else {
        hasNextPage = false;
      }
    }

    const uniqueUrls = [...new Set(urls)];
    this.responseLinks = uniqueUrls.filter(url => {
        const id = this.getVacancyIdFromUrl(url);
        return id && !this.state.appliedVacancyIds.includes(id) && !this.state.ignoredVacancyIds.includes(id);
    });

    console.log(`\nВсего найдено уникальных откликов: ${uniqueUrls.length}`);
    console.log(`Из них новых для обработки: ${this.responseLinks.length}`);
    return this.responseLinks;
  }

  private getVacancyIdFromUrl(url: string): string | null {
    const idMatch = url.match(/vacancyId=(\d+)/);
    return idMatch ? idMatch[1] : null;
  }

  async startAutoApply(): Promise<void> {
    if (!this.page) throw new Error('Browser not initialized');
    if (this.responseLinks.length === 0) {
      console.log('Нет новых вакансий для отклика.');
      return;
    }

    console.log(`\n🚀 Начинаем автоматические отклики на ${this.responseLinks.length} вакансий...`);

    let appliedCount = 0;
    let ignoredCount = 0;

    for (let i = 0; i < this.responseLinks.length; i++) {
        const url = this.responseLinks[i];
        const id = this.getVacancyIdFromUrl(url);
        if (!id) continue;

        process.stdout.write(`\r[${i + 1}/${this.responseLinks.length}] Обработка отклика: ${url}`);

        await this.page.goto(url, { waitUntil: 'domcontentloaded' });
        await this.delay();

        // Проверка на уже откликнутую вакансию
        // This selector might indicate the response modal/page confirms an existing application.
        const alreadyApplied = await this.page.$('[data-qa="vacancy-response-link-view-topic"]');
        if (alreadyApplied) {
            process.stdout.write(`\r[${i + 1}/${this.responseLinks.length}] 🟡 Уже откликнулись: ID ${id}\n`);
            if (!this.state.appliedVacancyIds.includes(id)) {
                this.state.appliedVacancyIds.push(id);
            }
            continue;
        }
        
        // Проверка на обязательный опрос
        // This usually appears in a modal after initiating the response.
        if (await this.page.isVisible('iframe[src*="surveys.hh.ru"]')) {
            this.ignoredVacancies.push({ id, url, title: `Отклик ID ${id}`, reason: 'Требуется пройти опрос' });
            this.state.ignoredVacancyIds.push(id);
            ignoredCount++;
            process.stdout.write(`\r[${i + 1}/${this.responseLinks.length}] 🔴 Пропущено (опрос): ID ${id}\n`);
            // Закрываем модальное окно, если есть
            const closeButton = await this.page.$('.bloko-modal-close');
            if(closeButton) await closeButton.click();
            continue;
        }
        
        // Проверка на обязательное сопроводительное письмо
        // This also appears in the response modal/page.
        const isLetterRequired = await this.page.$('[data-qa="vacancy-response-letter-required"]');
        if (isLetterRequired) {
            this.ignoredVacancies.push({ id, url, title: `Отклик ID ${id}`, reason: 'Требуется сопроводительное письмо' });
            this.state.ignoredVacancyIds.push(id);
            ignoredCount++;
            process.stdout.write(`\r[${i + 1}/${this.responseLinks.length}] 🔴 Пропущено (письмо): ID ${id}\n`);
            const closeButton = await this.page.$('.bloko-modal-close');
            if(closeButton) await closeButton.click();
            continue;
        }

        // Если есть необязательное письмо, просто жмем "Откликнуться"
        const submitButton = await this.page.$('[data-qa="vacancy-response-submit-popup"]');
        if (submitButton) {
            await submitButton.click();
            process.stdout.write(`\r[${i + 1}/${this.responseLinks.length}] 🟢 Отклик отправлен: ID ${id}\n`);
            this.state.appliedVacancyIds.push(id);
            appliedCount++;
        } else {
            // Если что-то пошло не так и не нашли кнопку отправки
            this.ignoredVacancies.push({ id, url, title: `Отклик ID ${id}`, reason: 'Неожиданное окно отклика' });
            this.state.ignoredVacancyIds.push(id);
            ignoredCount++;
            process.stdout.write(`\r[${i + 1}/${this.responseLinks.length}] 🔴 Пропущено (неожиданное окно): ID ${id}\n`);
        }

        saveState(this.config.outputDir, this.state);
        this.saveIgnoredVacancies();
        await this.delay();
    }

    console.log(`\n\n🎉 Авто-отклики завершены!`);
    console.log(`   ✅ Отправлено откликов: ${appliedCount}`);
    console.log(`   🚫 Пропущено вакансий: ${ignoredCount}`);
  }

  saveIgnoredVacancies(): string {
    if (!fs.existsSync(this.config.outputDir)) {
      fs.mkdirSync(this.config.outputDir, { recursive: true });
    }

    const outputPath = path.join(this.config.outputDir, 'ignored_vacancies.json');

    const output = {
      meta: {
        totalIgnored: this.ignoredVacancies.length,
        parsedAt: new Date().toISOString(),
      },
      vacancies: this.ignoredVacancies,
    };

    fs.writeFileSync(outputPath, JSON.stringify(output, null, 2), 'utf-8');
    return outputPath;
  }
  
  getCurrentUrl(): string {
    return this.page?.url() || '';
  }
}
