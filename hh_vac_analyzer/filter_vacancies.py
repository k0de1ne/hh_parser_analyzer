
import json

def filter_vacancies():
    try:
        with open('vacancies.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading vacancies.json: {e}")
        return

    all_vacancies = data.get('vacancies', [])
    golang_vacancies = []
    removed_vacancies = []

    for vacancy in all_vacancies:
        title = vacancy.get('title', '').lower()

        if 'go' in title or 'golang' in title:
            golang_vacancies.append(vacancy)
        else:
            removed_vacancies.append(vacancy)

    print("Удаленные вакансии:")
    for vacancy in removed_vacancies:
        print(f"- {vacancy.get('title')} (ID: {vacancy.get('id')})")

    data['vacancies'] = golang_vacancies
    
    try:
        with open('vacancies.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nСохранено {len(golang_vacancies)} вакансий golang.")
        print(f"Удалено {len(removed_vacancies)} вакансий.")
    except IOError as e:
        print(f"Error writing to vacancies.json: {e}")

if __name__ == "__main__":
    filter_vacancies()
