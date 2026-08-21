# Algoritm School Olimpiada

Bu loyiha 2-, 3- va 4-sinf o'quvchilarini Oltiariq tumanidagi olimpiadaga Telegram bot orqali ro'yxatdan o'tkazadi. Telegram Mini App, veb-sayt, admin panel yoki pullik servis kerak emas: bot Python, aiogram long polling va SQLite bilan ishlaydi.

## Imkoniyatlar

- bosqichma-bosqich ro'yxatdan o'tkazish;
- bitta Telegram ID orqali faqat bir marta ariza qabul qilish;
- `AS-0001` ko'rinishida yagona ishtirokchi kodi berish;
- deep-link manbasini saqlash: `?start=instagram`, `?start=3idum` va hokazo;
- takroriy telefon raqam aniqlansa administratorga ogohlantirish yuborish;
- admin statistikasi, qidiruv, CSV export, o'chirish, tahrirlash, keldi holati va broadcast;
- SQLite bazani oddiy skript orqali zaxiralash.

## 1. BotFather orqali bot yaratish

Telegramda `@BotFather` botini oching va:

```text
/newbot
```

buyrug'ini yuboring. Bot nomi va username tanlang. BotFather sizga token beradi.

## 2. Bot tokenini olish

BotFather bergan token quyidagiga o'xshaydi:

```text
123456789:AAExampleToken
```

Tokenni hech kimga yubormang va kod ichiga yozmang.

## 3. Telegram ID'ni aniqlash

Bot ishga tushgandan keyin unga `/myid` yuboring. Chiqqan raqamni `.env` faylidagi `ADMIN_IDS` ichiga yozasiz.

Admin ID'ni bot ishga tushirishdan oldin bilish kerak bo'lsa, Telegramdagi `@userinfobot` kabi bepul botlardan foydalanish mumkin.

## 4. `.env` faylini yaratish

```bash
cp .env.example .env
```

`.env` ichiga quyidagilarni kiriting:

```dotenv
BOT_TOKEN=BotFather_bergan_token
ADMIN_IDS=123456789
DATABASE_PATH=bot.db
```

Bir nechta admin bo'lsa, vergul bilan yozing:

```dotenv
ADMIN_IDS=123456789,987654321
```

`.env` Git'ga yuklanmaydi.

## 5. Python virtual muhit yaratish

MacBook terminalida loyiha papkasida:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 6. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

## 7. Botni MacBook'da ishga tushirish

```bash
python3 -m bot
```

Yoki:

```bash
bash run_bot.sh
```

Bot long polling orqali ishlaydi. Vaqtincha bepul ishlatish uchun MacBook internetga ulangan, ochiq va terminaldagi bot jarayoni ishlab turgan bo'lishi kerak.

## 8. Botni sinash

Telegramda botga `/start` yuboring. Deep-link manbani sinash uchun:

```text
https://t.me/BOT_USERNAME?start=instagram
https://t.me/BOT_USERNAME?start=telegram
https://t.me/BOT_USERNAME?start=3idum
https://t.me/BOT_USERNAME?start=13maktab
https://t.me/BOT_USERNAME?start=20maktab
https://t.me/BOT_USERNAME?start=6maktab
https://t.me/BOT_USERNAME?start=1maktab
```

`BOT_USERNAME` o'rniga bot username'ini yozing.

## 9. Admin buyruqlari

- `/stats` - umumiy statistika
- `/export` - barcha ro'yxatni Excel ochadigan UTF-8 CSV qilib yuboradi
- `/search <matn>` - telefon, ism yoki ishtirokchi kodi orqali qidiradi
- `/locations` - hududlar bo'yicha statistika
- `/grades` - sinflar bo'yicha statistika
- `/today` - bugungi arizalar
- `/recent` - oxirgi 10 ta ariza
- `/delete <AS-0001>` - arizani o'chirish
- `/attended <AS-0001>` - ishtirokchini “keldi” holatiga o'tkazish
- `/edit <AS-0001> <maydon> <yangi qiymat>` - arizani tahrirlash
- `/broadcast <xabar>` - ro'yxatdan o'tganlarga xabar yuborish
- `/cancel` - joriy jarayonni bekor qilish
- `/myid` - Telegram ID raqamini ko'rsatish
- `/help` - buyruqlar ro'yxati

Tahrirlash maydonlari:

```text
parent, phone, student, grade, school, neighborhood, location, source
```

Misollar:

```text
/search AS-0001
/attended AS-0001
/edit AS-0001 grade 3-sinf
/broadcast Assalomu alaykum! Olimpiada ertaga soat 09:00 da boshlanadi.
```

## 10. Bazani zaxiralash

```bash
python3 scripts/backup_db.py
```

Zaxira fayllar `backups/` papkasiga yoziladi.

## Bepul serverga joylash

SQLite bazasi saqlanib qolishi uchun eng yaxshi bepul variant kichik VM serverdir. Batafsil yo'riqnoma:

[deploy/DEPLOY_ORACLE_FREE.md](deploy/DEPLOY_ORACLE_FREE.md)

Serverda bot `systemd` orqali avtomatik ishga tushadi va server qayta yoqilganda ham tiklanadi.

## Tekshiruvlar

Syntax tekshiruv:

```bash
python3 -m compileall bot scripts tests
```

Testlar:

```bash
python3 -m unittest
```
