import { chromium, Browser, Page, BrowserContext } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import { Vacancy, ParserConfig, Salary, Contacts, ParsingProgress } from './types';

export class HHParser {
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private config: ParserConfig;
  private vacancies: Vacancy[] = [];
  private vacancyUrls: string[] = [];

  constructor(config: Partial<ParserConfig> = {}) {
    this.config = {
      delayMin: 1000,
      delayMax: 3000,
      maxPages: null,
      outputDir: './output',
      ...config,
    };
  }

  async init(): Promise<Page> {
    console.log('Запуск браузера...');
    this.browser = await chromium.launch({
      headless: false,
      args: ['--start-maximized'],
    });

    this.context = await this.browser.newContext({
      viewport: null,
      locale: 'ru-RU',
    });

    this.page = await this.context.newPage();
    await this.page.goto('https://hh.ru');
    console.log('Браузер запущен. Откройте hh.ru');
    return this.page;
  }

  async close(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
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

      // Ждем загрузки списка вакансий
      await this.page.waitForSelector('[data-qa="vacancy-serp__results"]', { timeout: 10000 }).catch(() => null);

      // Собираем ссылки на вакансии
      const vacancyLinks = await this.page.$$eval(
        'a[data-qa="serp-item__title"]',
        (links) => links.map((a) => (a as HTMLAnchorElement).href)
      );

      urls.push(...vacancyLinks);
      console.log(`  Найдено ${vacancyLinks.length} вакансий на странице`);

      // Проверяем ограничение по страницам
      if (this.config.maxPages && currentPage >= this.config.maxPages) {
        console.log(`Достигнут лимит страниц (${this.config.maxPages})`);
        break;
      }

      // Ищем кнопку "Следующая" или следующую страницу в пагинаторе
      const nextButton = await this.page.$('[data-qa="pager-next"]');
      if (nextButton) {
        await nextButton.click();
        await this.delay();
        await this.page.waitForSelector('[data-qa="vacancy-serp__results"]', { timeout: 15000 }).catch(() => null);
        currentPage++;
      } else {
        // Альтернативный метод: ищем ссылку на следующую страницу по номеру
        const nextPageLink = await this.page.$(`a[data-qa="pager-page"][href*="page=${currentPage}"]`);
        if (nextPageLink) {
          await nextPageLink.click();
          await this.delay();
          await this.page.waitForSelector('[data-qa="vacancy-serp__results"]', { timeout: 15000 }).catch(() => null);
          currentPage++;
        } else {
          hasNextPage = false;
        }
      }
    }

    this.vacancyUrls = [...new Set(urls)]; // Убираем дубликаты
    console.log(`\nВсего найдено уникальных вакансий: ${this.vacancyUrls.length}`);
    return this.vacancyUrls;
  }

  private parseSalary(salaryText: string | null): Salary | null {
    if (!salaryText) return null;

    const salary: Salary = {
      from: null,
      to: null,
      currency: null,
      gross: null,
    };

    // Определяем валюту
    if (salaryText.includes('₽') || salaryText.includes('руб')) {
      salary.currency = 'RUB';
    } else if (salaryText.includes('$') || salaryText.includes('USD')) {
      salary.currency = 'USD';
    } else if (salaryText.includes('€') || salaryText.includes('EUR')) {
      salary.currency = 'EUR';
    }

    // Определяем gross/net
    salary.gross = salaryText.toLowerCase().includes('до вычета') || salaryText.toLowerCase().includes('gross');

    // Извлекаем числа
    const numbers = salaryText.replace(/\s/g, '').match(/\d+/g);
    if (numbers) {
      if (salaryText.includes('от') && salaryText.includes('до')) {
        salary.from = parseInt(numbers[0]);
        salary.to = parseInt(numbers[1]);
      } else if (salaryText.includes('от')) {
        salary.from = parseInt(numbers[0]);
      } else if (salaryText.includes('до')) {
        salary.to = parseInt(numbers[0]);
      } else if (numbers.length === 1) {
        salary.from = parseInt(numbers[0]);
        salary.to = parseInt(numbers[0]);
      }
    }

    return salary;
  }

  async parseVacancyPage(url: string): Promise<Vacancy | null> {
    if (!this.page) throw new Error('Browser not initialized');

    try {
      await this.page.goto(url, { waitUntil: 'domcontentloaded' });
      await this.page.waitForSelector('[data-qa="vacancy-title"]', { timeout: 10000 });

      // Извлекаем ID из URL
      const idMatch = url.match(/vacancy\/(\d+)/);
      const id = idMatch ? idMatch[1] : url;

      // Название
      const title = await this.page.$eval('[data-qa="vacancy-title"]', (el) => el.textContent?.trim() || '').catch(() => '');

      // Компания
      const companyName = await this.page.$eval(
        '[data-qa="vacancy-company-name"]',
        (el) => el.textContent?.trim() || ''
      ).catch(() => '');

      const companyUrl = await this.page.$eval(
        '[data-qa="vacancy-company-name"]',
        (el) => {
          const link = el.closest('a') || el.querySelector('a');
          return link ? (link as HTMLAnchorElement).href : null;
        }
      ).catch(() => null);

      // Зарплата
      const salaryText = await this.page.$eval(
        '[data-qa="vacancy-salary"]',
        (el) => el.textContent?.trim() || null
      ).catch(() => null);

      // Опыт
      const experience = await this.page.$eval(
        '[data-qa="vacancy-experience"]',
        (el) => el.textContent?.trim() || null
      ).catch(() => null);

      // Тип занятости
      const employment = await this.page.$eval(
        '[data-qa="vacancy-view-employment-mode"]',
        (el) => el.textContent?.trim() || null
      ).catch(() => null);

      // График
      const schedule = await this.page.$eval(
        '[data-qa="vacancy-view-work-schedule"]',
        (el) => el.textContent?.trim() || null
      ).catch(() => null);

      // Локация
      const location = await this.page.$eval(
        '[data-qa="vacancy-view-raw-address"]',
        (el) => el.textContent?.trim() || null
      ).catch(async () => {
        // Альтернативный селектор для локации
        return await this.page!.$eval(
          '[data-qa="vacancy-view-location"]',
          (el) => el.textContent?.trim() || null
        ).catch(() => null);
      });

      // Описание
      const description = await this.page.$eval(
        '[data-qa="vacancy-description"]',
        (el) => el.textContent?.trim() || ''
      ).catch(() => '');

      // Навыки
      const skills = await this.page.$$eval(
        '[data-qa="skills-element"], [data-qa="bloko-tag bloko-tag_inline"]',
        (elements) => elements.map((el) => el.textContent?.trim() || '').filter(Boolean)
      ).catch(() => []);

      // Контакты (могут быть скрыты)
      let contacts: Contacts | null = null;
      try {
        const contactName = await this.page.$eval(
          '[data-qa="vacancy-contacts__fio"]',
          (el) => el.textContent?.trim() || null
        ).catch(() => null);

        const contactEmail = await this.page.$eval(
          '[data-qa="vacancy-contacts__email"]',
          (el) => el.textContent?.trim() || null
        ).catch(() => null);

        const contactPhones = await this.page.$$eval(
          '[data-qa="vacancy-contacts__phone"]',
          (elements) => elements.map((el) => el.textContent?.trim() || '').filter(Boolean)
        ).catch(() => []);

        if (contactName || contactEmail || contactPhones.length > 0) {
          contacts = {
            name: contactName,
            email: contactEmail,
            phones: contactPhones,
          };
        }
      } catch {
        // Контакты не доступны
      }

      // Дата публикации
      const publishedAt = await this.page.$eval(
        '[data-qa="vacancy-view-dates"]',
        (el) => el.textContent?.trim() || null
      ).catch(() => null);

      const vacancy: Vacancy = {
        id,
        title,
        url,
        company: {
          name: companyName,
          url: companyUrl,
        },
        salary: this.parseSalary(salaryText),
        experience,
        employment,
        schedule,
        location,
        description,
        skills,
        contacts,
        publishedAt,
        parsedAt: new Date().toISOString(),
      };

      return vacancy;
    } catch (error) {
      console.error(`Ошибка при парсинге ${url}:`, error);
      return null;
    }
  }

  async parseAllVacancies(
    onProgress?: (progress: ParsingProgress) => void
  ): Promise<Vacancy[]> {
    if (this.vacancyUrls.length === 0) {
      console.log('Сначала соберите ссылки на вакансии');
      return [];
    }

    console.log(`\nНачинаем парсинг ${this.vacancyUrls.length} вакансий...`);
    this.vacancies = [];

    for (let i = 0; i < this.vacancyUrls.length; i++) {
      const url = this.vacancyUrls[i];
      const progress: ParsingProgress = {
        totalVacancies: this.vacancyUrls.length,
        parsedVacancies: i,
        currentPage: i + 1,
        totalPages: this.vacancyUrls.length,
      };

      if (onProgress) {
        onProgress(progress);
      }

      console.log(`[${i + 1}/${this.vacancyUrls.length}] Парсинг: ${url}`);

      const vacancy = await this.parseVacancyPage(url);
      if (vacancy) {
        this.vacancies.push(vacancy);
        // Сохраняем промежуточный результат
        this.saveResults();
      }

      await this.delay();
    }

    console.log(`\nПарсинг завершен. Успешно собрано ${this.vacancies.length} вакансий.`);
    return this.vacancies;
  }

  saveResults(filename?: string): string {
    // Создаем папку output если её нет
    if (!fs.existsSync(this.config.outputDir)) {
      fs.mkdirSync(this.config.outputDir, { recursive: true });
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const outputFilename = filename || `vacancies_${timestamp}.json`;
    const outputPath = path.join(this.config.outputDir, outputFilename);

    const output = {
      meta: {
        totalVacancies: this.vacancies.length,
        parsedAt: new Date().toISOString(),
        sourceUrls: this.vacancyUrls.length,
      },
      vacancies: this.vacancies,
    };

    fs.writeFileSync(outputPath, JSON.stringify(output, null, 2), 'utf-8');
    return outputPath;
  }

  getVacancies(): Vacancy[] {
    return this.vacancies;
  }

  getCurrentUrl(): string {
    return this.page?.url() || '';
  }
}
