# REST API объявлений на Flask

Домашнее задание к лекции «Flask»: REST API для создания, чтения,
редактирования и удаления объявлений.

## Возможности

- создание объявления — `POST /advertisements`;
- получение списка — `GET /advertisements`;
- получение объявления — `GET /advertisements/<id>`;
- редактирование — `PATCH` или `PUT /advertisements/<id>`;
- удаление — `DELETE /advertisements/<id>`;
- автоматическое сохранение даты создания;
- валидация JSON и понятные ответы с кодами `400` и `404`.

Объявление содержит `title`, `description`, `created_at` и `owner`.

## Запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

После запуска API доступно по адресу <http://127.0.0.1:5000>.
По умолчанию используется база SQLite `advertisements.db`.

## Пример создания объявления

```bash
curl -i -X POST http://127.0.0.1:5000/advertisements \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Продам велосипед",
    "description": "Городской велосипед в хорошем состоянии",
    "owner": "alexander"
  }'
```

Остальные примеры находятся в файле `requests.http`.

## Тесты

```bash
pytest -q
```
