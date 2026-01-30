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
    """Normalizes skills using a predefined dictionary of synonyms."""
    
    # This dictionary is the core of the normalization logic.
    # Keys are variations, values are the canonical names.
    SYNONYMS = {
        'go': 'Golang',
        'golang': 'Golang',
        'go lang': 'Golang',
        'postgresql': 'PostgreSQL',
        'postgres': 'PostgreSQL',
        'postgesql': 'PostgreSQL',
        'k8s': 'Kubernetes',
        'кубернетес': 'Kubernetes',
        'apache kafka': 'Kafka',
        'kafka': 'Kafka',
        'rest api': 'REST',
        'restful': 'REST',
        'rest': 'REST',
        'микросервисная архитектура': 'Microservices',
        'микросервисы': 'Microservices',
        'docker-compose': 'Docker',
        'докер': 'Docker',
        'git': 'Git',
        'github': 'Git',
        'gitlab': 'Git',
        'sql': 'SQL',
        'mysql': 'SQL',
        'ms sql': 'SQL',
        'linux': 'Linux/Unix',
        'unix': 'Linux/Unix',
        'ci/cd': 'CI/CD',
        'gitlab ci': 'CI/CD',
        'teamcity': 'CI/CD',
        'jenkins': 'CI/CD',
        'clickhouse': 'ClickHouse',
        'хайлоад': 'Highload',
        'высоконагруженные системы': 'Highload',
        'rabbitmq': 'RabbitMQ',
        'redis': 'Redis',
        'mongodb': 'MongoDB',
        'nosql': 'NoSQL',
        'nginx': 'Nginx',
        'c++': 'C/C++',
        'c/c++': 'C/C++',
        'c#': 'C#',
        'python': 'Python',
        'питон': 'Python',
        'java': 'Java',
        'javascript': 'JavaScript',
        'js': 'JavaScript',
        'typescript': 'TypeScript',
        'ts': 'TypeScript',
        'react': 'React',
        'react.js': 'React',
        'vue': 'Vue.js',
        'vue.js': 'Vue.js',
        'node.js': 'Node.js',
        'nodejs': 'Node.js',
    }

    def __init__(self):
        # Pre-process synonyms for efficient lookup
        self.mapping = {}
        for variant, canonical in self.SYNONYMS.items():
            # Handle cases like "C++" vs "c  "
            processed_variant = re.sub(r'[^a-z0-9]', '', variant.lower())
            self.mapping[processed_variant] = canonical

    def normalize(self, skill: str) -> str:
        """Finds the canonical form of a skill."""
        # Clean the skill name for lookup
        processed_skill = re.sub(r'[^a-z0-9]', '', skill.lower())
        
        # Direct match in the synonym map
        if processed_skill in self.mapping:
            return self.mapping[processed_skill]
            
        # If no synonym found, return the original skill, capitalized for consistency
        return skill.strip().title()


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


def get_stop_words():
    """Returns a set of common Russian and English stop words."""
    russian_stop_words = [
        'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты',
        'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'о', 'мой', 'из', 'для', 'мы', 'твой',
        'нам', 'ваш', 'их', 'еще', 'когда', 'где', 'кто', 'почему', 'чем', 'вас', 'ваша', 'наш', 'наша', 'свой', 'своя', 'сейчас',
        'работы', 'компании', 'команда', 'команду', 'разработка', 'разработки', 'задач', 'задачи', 'сервисов', 'сервиса',
        'продукта', 'продуктов', 'проекта', 'проектов', 'данных', 'условий', 'условия', 'требования', 'опыт', 'знание', 'умение',
        'работа', 'работать', 'развивать', 'создавать', 'ищем', 'требуется', 'обязанности', 'ожидания', 'плюсом', 'будет'
    ]
    english_stop_words = [
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
        'that', 'the', 'to', 'was', 'were', 'will', 'with', 'we', 'you', 'our', 'your'
    ]
    return set(russian_stop_words + english_stop_words)


def analyze_skills(vacancies: list) -> dict:
    """Categorizes skills first, then normalizes them."""
    
    raw_technical = []
    raw_soft = []
    raw_languages = []

    # 1. Categorize first
    for v in vacancies:
        for skill in v.get('skills', []):
            if is_language_level(skill):
                raw_languages.append(skill)
            elif is_soft_skill(skill):
                raw_soft.append(skill)
            else:
                raw_technical.append(skill)

    normalizer = SkillNormalizer()

    def _normalize_category(raw_skills: list) -> dict:
        """Helper to normalize a list of raw skills."""
        raw_counts = Counter(raw_skills)
        normalized_data = defaultdict(lambda: {'total_count': 0, 'variants': Counter()})
        for skill, count in raw_counts.items():
            canonical = normalizer.normalize(skill)
            normalized_data[canonical]['total_count'] += count
            normalized_data[canonical]['variants'][skill] = count
        
        # Sort variants inside each canonical skill
        for canonical in normalized_data:
            sorted_variants = sorted(normalized_data[canonical]['variants'].items(), key=lambda item: -item[1])
            normalized_data[canonical]['variants'] = sorted_variants
            
        # Sort the whole dictionary by total_count
        return dict(sorted(normalized_data.items(), key=lambda item: -item[1]['total_count']))

    technical = _normalize_category(raw_technical)
    soft = _normalize_category(raw_soft)
    languages = _normalize_category(raw_languages)

    # --- Co-occurrence Analysis (Combos) ---
    combos = Counter()
    for v in vacancies:
        # We only want technical skills for combos
        current_raw_tech = [s for s in v.get('skills', []) if not is_soft_skill(s) and not is_language_level(s)]
        normalized_tech_in_vacancy = {normalizer.normalize(s) for s in current_raw_tech}
        
        unique_list = list(normalized_tech_in_vacancy)
        for i, s1 in enumerate(unique_list):
            for s2 in unique_list[i+1:]:
                pair = tuple(sorted([s1, s2]))
                combos[pair] += 1
    
    return {
        'technical': technical,
        'soft': soft,
        'languages': languages,
        'total_mentions': len(raw_technical) + len(raw_soft) + len(raw_languages),
        'unique_raw': len(Counter(raw_technical + raw_soft + raw_languages)),
        'unique_normalized': len(technical) + len(soft) + len(languages),
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


def analyze_dynamic_keywords(vacancies: list, stop_words: set) -> dict:
    """Extracts frequent n-grams from descriptions to find emerging keywords."""
    bigram_counter = Counter()
    
    for v in vacancies:
        desc = (v.get('description') or '').lower()
        if not desc:
            continue
        
        clean_desc = re.sub(r'<[^>]+>', '', desc) # Strip HTML tags
        words = re.findall(r'\b[a-zа-яё-]{3,}\b', clean_desc) # Find words (at least 3 chars)
        
        filtered_words = [word for word in words if word not in stop_words and not is_soft_skill(word)]
        
        # Count bigrams (two-word phrases)
        for i in range(len(filtered_words) - 1):
            # We avoid bigrams where both words are the same, e.g. "go go"
            if filtered_words[i] != filtered_words[i+1]:
                bigram = f"{filtered_words[i]} {filtered_words[i+1]}"
                bigram_counter[bigram] += 1
            
    # Filter bigrams that occur in at least 3 vacancies to reduce noise
    meaningful_bigrams = {
        term: count for term, count in bigram_counter.most_common(50)
        if count >= 3
    }
    
    return {
        'top_bigrams': meaningful_bigrams
    }


def analyze_skill_context(vacancies: list, technical_skills: list) -> dict:
    """Analyzes the context of skills to determine if they are mandatory or preferred."""
    
    mandatory_markers = [r'требуется', r'обязательно', r'необходимо', r'требования', r'нужен', r'уверенн', r'ожидаем', r'важно']
    preferred_markers = [r'будет плюсом', r'желательно', r'преимуществом', r'как плюс', r'дополнительным', r'хорошо если', r'знакомство с']

    mandatory_skills = Counter()
    preferred_skills = Counter()

    skill_names = {skill.lower() for skill in technical_skills.keys()}
    # Add some common variations that might not be in the skills list
    skill_names.update(['rest', 'api', 'backend', 'frontend'])


    for v in vacancies:
        desc = (v.get('description') or '').lower()
        if not desc:
            continue
        
        # Using a window around the skill mention can be more robust than splitting by sentence
        for skill_name in skill_names:
            # Use word boundaries for more precise matching
            for match in re.finditer(r'\b' + re.escape(skill_name) + r'\b', desc):
                # Define a window of text around the match to check for markers
                start = max(0, match.start() - 80)
                end = min(len(desc), match.end() + 80)
                context_window = desc[start:end]

                # Check for markers in the context window
                if any(re.search(marker, context_window) for marker in mandatory_markers):
                    mandatory_skills[skill_name] += 1
                if any(re.search(marker, context_window) for marker in preferred_markers):
                    preferred_skills[skill_name] += 1

    return {
        'mandatory': [[skill, count] for skill, count in mandatory_skills.most_common(40)],
        'preferred': [[skill, count] for skill, count in preferred_skills.most_common(40)],
    }


def generate_insights(data: dict) -> list:
    """Generate actionable insights for resume building"""
    insights = []
    total_vacancies = data['meta']['total']

    # 1. Resume Keywords Insight
    # Check if 'descriptions' and 'keywords' exist before accessing
    top_desc_keywords = []
    if 'descriptions' in data and 'keywords' in data['descriptions']:
        top_desc_keywords = list(data['descriptions']['keywords'].keys())[:5]

    top_tech_skills = list(data['skills']['technical'].keys())[:12]
    resume_keywords = sorted(list(set(top_tech_skills + top_desc_keywords)), key=lambda x: x.lower())
    insights.append({
        'title': 'Ключевые слова для резюме',
        'text': 'Обязательно включите эти технологии и концепции в свое резюме, чтобы пройти HR-фильтры.',
        'items': resume_keywords
    })

    # 2. Skill Combinations Insight
    combos = data['skills']['combinations'][:5]
    if combos:
        insights.append({
            'title': 'Частые комбинации навыков',
            'text': 'Эти навыки часто требуются вместе. Знание этих связок — большой плюс.',
            'items': [f"{c[0][0]} + {c[0][1]}" for c in combos]
        })

    # 3. Experience Insight
    exp = data.get('experience', {})
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
    roles = data.get('titles', {}).get('roles', {})
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
    print(f"Analyzing {len(vacancies)} vacancies with new features...")

    # --- Existing Analysis ---
    skills = analyze_skills(vacancies)
    salaries = analyze_salaries(vacancies)
    experience = analyze_experience(vacancies)
    companies = analyze_companies(vacancies)
    titles = analyze_titles(vacancies)
    locations = analyze_locations(vacancies)
    descriptions = analyze_descriptions(vacancies)

    # --- New Analysis ---
    stop_words = get_stop_words()
    dynamic_keywords = analyze_dynamic_keywords(vacancies, stop_words)
    skill_context = analyze_skill_context(vacancies, skills.get('technical', []))

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
        'descriptions': descriptions,
        # --- Adding new data to the output ---
        'dynamic_keywords': dynamic_keywords,
        'skill_context': skill_context
    }

    data['insights'] = generate_insights(data)

    with open('analysis_results.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Done! Results saved to analysis_results.json with new analysis.")


if __name__ == '__main__':
    main()
