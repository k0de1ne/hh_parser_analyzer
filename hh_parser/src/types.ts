export interface Salary {
  from: number | null;
  to: number | null;
  currency: string | null;
  gross: boolean | null;
}

export interface Company {
  name: string;
  url: string | null;
}

export interface Contacts {
  name: string | null;
  email: string | null;
  phones: string[];
}

export interface Vacancy {
  id: string;
  title: string;
  url: string;
  company: Company;
  salary: Salary | null;
  experience: string | null;
  employment: string | null;
  schedule: string | null;
  location: string | null;
  description: string;
  skills: string[];
  contacts: Contacts | null;
  publishedAt: string | null;
  parsedAt: string;
}

export interface ParserConfig {
  delayMin: number;
  delayMax: number;
  maxPages: number | null;
  outputDir: string;
}

export interface ParsingProgress {
  totalVacancies: number;
  parsedVacancies: number;
  currentPage: number;
  totalPages: number | null;
}
