# PreTestOnline — Vercel + MySQL

Aplikasi Flask untuk pretest Ilmu Informatika UKDC.

## Deployment

Project ini menggunakan PyMySQL, bukan mysqlclient/Flask-MySQLdb, sehingga tidak membutuhkan library native MySQL saat build Vercel.

Set environment variables di Vercel: `SECRET_KEY`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`.

Jangan upload file `.env` ke repository.

Database tetap menggunakan MySQL dan dapat dibuat dari `schema.sql`, lalu contoh soal dari `seed.py`.
