# Bepul Serverga Joylash: Oracle Cloud Always Free

SQLite bazasi yo'qolmasligi uchun botni bepul VM serverga qo'yish eng to'g'ri yo'l. Oracle Cloud Always Free kichik Linux VM va disk beradi; bot long polling bilan doimiy ishlab turadi.

## 1. Oracle Cloud'da VM ochish

1. Oracle Cloud Free Tier akkaunt yarating.
2. `Compute > Instances > Create instance` bo'limiga kiring.
3. Ubuntu 22.04 yoki 24.04 tanlang.
4. Always Free shaklini tanlang.
5. SSH key yarating yoki mavjud public key'ni kiriting.
6. Instance public IP manzilini saqlab qo'ying.

## 2. Serverga ulanish

```bash
ssh ubuntu@SERVER_IP
```

`SERVER_IP` o'rniga Oracle bergan IP'ni yozing.

## 3. Kodni serverga ko'chirish

GitHub repo tayyor bo'lsa:

```bash
sudo git clone REPO_URL /opt/algoritm-olimpiada
sudo chown -R ubuntu:ubuntu /opt/algoritm-olimpiada
cd /opt/algoritm-olimpiada
```

`REPO_URL` o'rniga bot repo manzilini yozing.

## 4. `.env` yaratish

Serverda:

```bash
cd /opt/algoritm-olimpiada
nano .env
```

Ichiga:

```dotenv
BOT_TOKEN=BotFather_bergan_token
ADMIN_IDS=2041008827
DATABASE_PATH=/opt/algoritm-olimpiada/bot.db
```

Saqlash: `Ctrl+O`, `Enter`, chiqish: `Ctrl+X`.

## 5. Botni service qilib ishga tushirish

```bash
chmod +x deploy/install_on_ubuntu.sh
bash deploy/install_on_ubuntu.sh
```

## 6. Holatini tekshirish

```bash
sudo systemctl status algoritm-olimpiada --no-pager
```

Loglarni ko'rish:

```bash
sudo journalctl -u algoritm-olimpiada -f
```

Qayta ishga tushirish:

```bash
sudo systemctl restart algoritm-olimpiada
```

## 7. Bazani zaxiralash

```bash
cd /opt/algoritm-olimpiada
.venv/bin/python scripts/backup_db.py
```

Zaxira `backups/` papkasiga yoziladi.

## 8. Yangilash

Kod GitHub'ga yangilangandan keyin serverda:

```bash
cd /opt/algoritm-olimpiada
git pull
.venv/bin/pip install -r requirements.txt
sudo systemctl restart algoritm-olimpiada
```
