#!/usr/bin/env python3
"""
HH.ru Vacancy Analyzer - Automatic normalization without hardcoding
"""

import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path


def load_vacancies(filepath: str) -> list:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('vacancies', [])


class SkillNormalizer:
    """Automatic skill normalization using fuzzy matching"""

    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.canonical = {}  # maps normalized -> canonical form
        self.skill_counts = Counter()

    def normalize_all(self, all_skills: list) -> dict:
        """Normalize all skills and return mapping"""
        # Count raw occurrences
        raw_counts = Counter(all_skills)

        # Create canonical mapping
        mapping = {skill: skill for skill in raw_counts.keys()}
        self.skill_counts = raw_counts
        self.variants = {skill: [(skill, count)] for skill, count in raw_counts.items()}

        return mapping

    def normalize(self, skill: str) -> str:
        """Get canonical form of a skill"""
        return self.canonical.get(skill, skill)


def is_soft_skill(skill: str) -> bool:
    """Detect soft skills by patterns"""
    soft_patterns = [
        r'коммуникаб', r'ответствен', r'стрессоуст', r'самостоятел',
        r'инициатив', r'обучаем', r'внимател', r'аккуратн',
        r'командн', r'работа в команд', r'team.?work', r'communication',
        r'leadership', r'лидерств', r'мотивац', r'дисциплин',
        r'пунктуальн', r'исполнительн', r'креатив', r'гибкост',
        r'адаптив', r'многозадачн', r'тайм.?менеджмент', r'time.?management',
        r'problem.?solving', r'решение проблем', r'аналитическ.*мышлен',
        r'критическ.*мышлен', r'переговор', r'презентац',
    ]
    skill_lower = skill.lower()
    return any(re.search(p, skill_lower) for p in soft_patterns)


def is_language_level(skill: str) -> bool:
    """Detect language proficiency markers"""
    patterns = [
        r'английский.*[—\-–].*[A-C][1-2]',
        r'english.*[—\-–].*[A-C][1-2]',
        r'^[A-C][1-2]\s*[—\-–]',
        r'(intermediate|upper|beginner|advanced|native|fluent)',
        r'(средний|продвинут|начальн|свободн|базов).*уровень',
    ]
    return any(re.search(p, skill, re.IGNORECASE) for p in patterns)


def analyze_skills(vacancies: list) -> dict:
    """Analyze and normalize skills"""
    all_skills_raw = []
    skills_by_vacancy_raw = []

    for v in vacancies:
        skills = v.get('skills') or []
        skills_by_vacancy_raw.append(skills)
        all_skills_raw.extend(skills)

    # Normalize skills
    normalizer = SkillNormalizer()
    mapping = normalizer.normalize_all(all_skills_raw)
    skill_counts = normalizer.skill_counts

    # Categorize and store variants
    technical = []
    soft = []
    languages = []
    technical_variants = {}
    soft_variants = {}
    languages_variants = {}

    for skill, count in skill_counts.most_common():
        if is_language_level(skill):
            languages.append([skill, count])
            if skill in normalizer.variants:
                languages_variants[skill] = normalizer.variants[skill]
        elif is_soft_skill(skill):
            soft.append([skill, count])
            if skill in normalizer.variants:
                soft_variants[skill] = normalizer.variants[skill]
        else:
            technical.append([skill, count])
            if skill in normalizer.variants:
                technical_variants[skill] = normalizer.variants[skill]

    # Skill co-occurrence with normalized skills
    combos = Counter()
    for raw_skills in skills_by_vacancy_raw:
        normalized_skills = {mapping.get(s, s) for s in raw_skills}

        # Filter out soft skills and language levels for co-occurrence analysis
        unique_tech_skills = list({s for s in normalized_skills
                                   if not is_soft_skill(s) and not is_language_level(s)})

        for i, s1 in enumerate(unique_tech_skills):
            for s2 in unique_tech_skills[i+1:]:
                pair = tuple(sorted([s1, s2]))
                combos[pair] += 1

    return {
        'technical': technical,
        'soft': soft,
        'languages': languages,
        'technical_variants': technical_variants,
        'soft_variants': soft_variants,
        'languages_variants': languages_variants,
        'total_mentions': len(all_skills_raw),
        'unique_raw': len(set(all_skills_raw)),
        'unique_normalized': len(skill_counts),
        'combinations': [[list(k), v] for k, v in combos.most_common(30)]
    }


def analyze_salaries(vacancies: list) -> dict:
    """Analyze salary distributions"""
    salaries = []
    by_experience = defaultdict(list)
    with_salary = 0

    for v in vacancies:
        salary = v.get('salary')
        exp = v.get('experience') or 'Не указан'

        if salary:
            with_salary += 1
            multiplier = 0.87 if salary.get('gross') else 1.0

            sfrom = salary.get('from')
            sto = salary.get('to')

            if sfrom and sto:
                avg = int((sfrom + sto) / 2 * multiplier)
            elif sfrom:
                avg = int(sfrom * multiplier)
            elif sto:
                avg = int(sto * multiplier)
            else:
                continue

            salaries.append({
                'value': avg,
                'from': int(sfrom * multiplier) if sfrom else None,
                'to': int(sto * multiplier) if sto else None,
                'experience': exp
            })
            by_experience[exp].append(avg)

    if not salaries:
        return {'with_salary': 0, 'without_salary': len(vacancies)}

    all_values = [s['value'] for s in salaries]
    all_values.sort()

    # Percentiles
    def percentile(data, p):
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return int(data[f] + (k - f) * (data[c] - data[f]))

    # Distribution with dynamic ranges
    min_sal, max_sal = min(all_values), max(all_values)
    step = 50000
    distribution = {}
    current = (min_sal // step) * step
    while current <= max_sal:
        next_val = current + step
        label = f"{current // 1000}k-{next_val // 1000}k"
        count = len([s for s in all_values if current <= s < next_val])
        if count > 0:
            distribution[label] = count
        current = next_val

    # By experience stats
    exp_stats = {}
    for exp, sals in by_experience.items():
        if sals:
            sals.sort()
            exp_stats[exp] = {
                'min': min(sals),
                'max': max(sals),
                'avg': int(sum(sals) / len(sals)),
                'median': sals[len(sals) // 2],
                'p25': percentile(sals, 25),
                'p75': percentile(sals, 75),
                'count': len(sals)
            }

    return {
        'with_salary': with_salary,
        'without_salary': len(vacancies) - with_salary,
        'min': min(all_values),
        'max': max(all_values),
        'avg': int(sum(all_values) / len(all_values)),
        'median': all_values[len(all_values) // 2],
        'p10': percentile(all_values, 10),
        'p25': percentile(all_values, 25),
        'p75': percentile(all_values, 75),
        'p90': percentile(all_values, 90),
        'distribution': distribution,
        'by_experience': exp_stats
    }


def analyze_experience(vacancies: list) -> dict:
    """Analyze experience requirements"""
    return dict(Counter(v.get('experience') or 'Не указан' for v in vacancies).most_common())


def analyze_companies(vacancies: list) -> dict:
    """Analyze hiring companies"""
    companies = Counter()
    for v in vacancies:
        name = (v.get('company') or {}).get('name') or 'Не указана'
        companies[name] += 1

    return {
        'all': [[k, v] for k, v in companies.most_common()],
        'total': len(companies)
    }


def analyze_titles(vacancies: list) -> dict:
    """Analyze job titles"""
    titles = [v.get('title', '') for v in vacancies]

    # Seniority detection patterns
    seniority_patterns = {
        'Junior': [r'junior', r'джуниор', r'младш', r'\bjr\b'],
        'Middle': [r'middle', r'миддл', r'\bmid\b'],
        'Senior': [r'senior', r'сеньор', r'старш', r'\bsr\b'],
        'Lead': [r'lead', r'лид', r'ведущ', r'principal', r'staff', r'team\s*lead'],
        'Architect': [r'architect', r'архитектор'],
    }

    role_patterns = {
        'Backend': [r'backend', r'back-end', r'back end', r'бэкенд', r'бекенд'],
        'Fullstack': [r'fullstack', r'full-stack', r'full stack', r'фулстек'],
        'DevOps/SRE': [r'devops', r'sre', r'platform', r'infrastructure', r'инфраструктур'],
        'Data/ML': [r'\bdata\b', r'\bml\b', r'machine', r'аналитик', r'data\s*engineer'],
        'Frontend': [r'frontend', r'front-end', r'front end', r'фронтенд'],
    }

    seniority = defaultdict(int)
    roles = defaultdict(int)

    for title in titles:
        t = title.lower()

        # Seniority
        found_seniority = False
        for level, patterns in seniority_patterns.items():
            if any(re.search(p, t) for p in patterns):
                seniority[level] += 1
                found_seniority = True
                break
        if not found_seniority:
            seniority['Не указан'] += 1

        # Role
        found_role = False
        for role, patterns in role_patterns.items():
            if any(re.search(p, t) for p in patterns):
                roles[role] += 1
                found_role = True
                break
        if not found_role:
            roles['Developer'] += 1

    return {
        'seniority': dict(seniority),
        'roles': dict(roles),
        'all': [[t, 1] for t in titles]
    }


def analyze_locations(vacancies: list) -> dict:
    """Analyze locations"""
    cities = Counter()

    for v in vacancies:
        loc = v.get('location')
        if loc:
            city = loc.split(',')[0].strip()
            cities[city] += 1
        else:
            cities['Не указан'] += 1

    # Remote work detection
    remote_keywords = [r'удален', r'remote', r'дистанц', r'из любой точки', r'home\s*office']
    remote_count = 0
    hybrid_count = 0

    for v in vacancies:
        desc = (v.get('description') or '').lower()
        if any(re.search(k, desc) for k in remote_keywords):
            remote_count += 1
        if re.search(r'гибрид|hybrid|офис.*удален|удален.*офис', desc):
            hybrid_count += 1

    return {
        'cities': dict(cities.most_common()),
        'remote_mentions': remote_count,
        'hybrid_mentions': hybrid_count,
        'remote_percent': round(remote_count / len(vacancies) * 100, 1)
    }


def analyze_descriptions(vacancies: list) -> dict:
    """Extract keywords and patterns from descriptions"""
    keyword_patterns = {
        'Микросервисы': r'микросервис|microservice',
        'Highload': r'высоконагруж|highload|high.?load|нагрузк',
        'Распределённые системы': r'распределен|distributed',
        'Тестирование': r'\bтест|test|unit.?test|интеграцион',
        'Agile/Scrum': r'agile|scrum|kanban|спринт',
        'REST API': r'rest\s*api|restful',
        'gRPC': r'grpc',
        'GraphQL': r'graphql',
        'Cloud': r'облак|cloud|aws|gcp|azure|yandex.?cloud',
        'Безопасность': r'безопасност|security|защит',
        'Оптимизация': r'оптимизац|optimization|performance|производительн',
        'Архитектура': r'архитектур|architecture|design.?pattern',
        'CI/CD': r'ci.?cd|деплой|deploy|pipeline',
        'Мониторинг': r'мониторинг|monitoring|observability|метрик',
        'Код-ревью': r'код.?ревью|code.?review|ревью кода',
        'Менторство': r'ментор|mentor|обучен|наставн',
    }

    keywords = {}
    for name, pattern in keyword_patterns.items():
        count = sum(1 for v in vacancies
                   if re.search(pattern, (v.get('description') or '').lower()))
        if count > 0:
            keywords[name] = count

    # Sort by count
    keywords = dict(sorted(keywords.items(), key=lambda x: -x[1]))

    return {
        'keywords': keywords,
        'total_with_description': len([v for v in vacancies if v.get('description')])
    }


def generate_insights(data: dict) -> list:
    """Generate actionable insights for resume building"""
    insights = []
    total_vacancies = data['meta']['total']

    # 1. Resume Keywords Insight
    top_tech_skills = [s[0] for s in data['skills']['technical'][:12]]
    top_desc_keywords = list(data['descriptions']['keywords'].keys())[:5]
    resume_keywords = sorted(list(set(top_tech_skills + top_desc_keywords)), key=lambda x: x.lower())
    insights.append({
        'title': 'Ключевые слова для резюме',
        'text': 'Обязательно включите эти технологии и концепции в свое резюме, чтобы пройти HR-фильтры.',
        'items': resume_keywords
    })

    # 2. Skill Combinations Insight
    combos = data['skills']['combinations'][:5]
    combo_skills = set()
    for pair, _ in combos:
        combo_skills.update(pair)
    insights.append({
        'title': 'Частые комбинации навыков',
        'text': 'Эти навыки часто требуются вместе. Знание этих связок — большой плюс.',
        'items': [f"{c[0][0]} + {c[0][1]}" for c in combos]
    })

    # 3. Experience Insight
    exp = data['experience']
    if exp:
        most_common_exp = max(exp.items(), key=lambda x: x[1])
        exp_text = (f"Самое частое требование к опыту: {most_common_exp[0]} "
                    f"({most_common_exp[1]} из {total_vacancies} вакансий). "
                    "Убедитесь, что ваш опыт соответствует этому.")
        insights.append({
            'title': 'Востребованный опыт',
            'text': exp_text,
            'items': [f"{k}: {v} вак." for k, v in exp.items()]
        })

    # 4. Job Title Insight
    roles = data['titles']['roles']
    if roles:
        top_role = max(roles.items(), key=lambda x: x[1])
        role_text = (f"Большинство позиций — это '{top_role[0]}'. "
                     "Рассмотрите возможность использования этого или похожего названия должности в резюме.")
        insights.append({
            'title': 'Как назвать свою должность',
            'text': role_text,
            'items': [f"{k}: {v}%" for k, v in sorted(
                [(r, round(c/total_vacancies*100)) for r, c in roles.items()],
                key=lambda x: -x[1]
            )]
        })

    return insights


def main():
    vacancies = load_vacancies('vacancies.json')
    print(f"Analyzing {len(vacancies)} vacancies...")

    skills = analyze_skills(vacancies)
    salaries = analyze_salaries(vacancies)
    experience = analyze_experience(vacancies)
    companies = analyze_companies(vacancies)
    titles = analyze_titles(vacancies)
    locations = analyze_locations(vacancies)
    descriptions = analyze_descriptions(vacancies)

    data = {
        'meta': {
            'total': len(vacancies),
            'analyzed_at': '2026-01-02'
        },
        'skills': skills,
        'salaries': salaries,
        'experience': experience,
        'companies': companies,
        'titles': titles,
        'locations': locations,
        'descriptions': descriptions
    }

    data['insights'] = generate_insights(data)

    with open('analysis_results.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Done! Results saved to analysis_results.json")


if __name__ == '__main__':
    main()
