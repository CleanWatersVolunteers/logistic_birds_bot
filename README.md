# logistic_birds_bot
## Запуск бота
Для запуска бота неоходимо в корне проекта создать текстовый файл 'token' с токеном бота и файлы nextgis_login, nextgis_pass для авторизации на сервисе nextgis. Скрипт автоматически подтянет эти файлы.
Для запуска выполнить команду
```sh
python3 main.py
```
## Краткое описание
- main.py - точка входа
- nextgis_connector.py - модуль по работе с сервисом nextgis, тут прописаны используемые json поля
- registration_form.py - основное меню бота
- storage_users.py - модуль по работе с базой данных пользователей (использует файлы storage_users_file_0.json и storage_users_file_1.json). База заполняется автоматически на основе id с сервера nextgis
- tgm.py - вспомогательный модуль для telegram api
