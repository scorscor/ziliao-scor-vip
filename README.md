# Synthetic Frontier

Flask + SQLite personal site with a stitched sci-fi frontend, admin login, resource management, and Docker deployment.

## Admin Account

- Username: `admin`
- Password: `19911017`

## Local Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app wsgi:app run --debug --port 5002
```

Open:

- Public site: `http://127.0.0.1:5002/`
- Admin login: `http://127.0.0.1:5002/admin/login`

## Docker Run

```powershell
docker compose up --build -d
```

Open:

- Public site: `http://127.0.0.1:5002/`
- Admin login: `http://127.0.0.1:5002/admin/login`

Data created on first boot:

- SQLite DB: `./data/site.db`
- Uploads: `./data/uploads`

## Production Deploy

For a server deployment on `ziliao.scor.vip`, the repo now includes:

- production env template: [.env.production.example](E:/projects/ziliao-scor-vip/.env.production.example)
- production compose file: [docker-compose.prod.yml](E:/projects/ziliao-scor-vip/docker-compose.prod.yml)
- nginx config: [deploy/nginx/ziliao.scor.vip.conf](E:/projects/ziliao-scor-vip/deploy/nginx/ziliao.scor.vip.conf)

Recommended server flow on Ubuntu:

1. Point the DNS record of `ziliao.scor.vip` to your server IP.
2. Install Docker, Docker Compose plugin, Nginx, and Certbot.
3. Upload this project to the server, then create the production env file:

```bash
cp .env.production.example .env.production
```

4. Edit `.env.production` and replace `SECRET_KEY`.
5. Start the Flask app with Docker:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

6. Copy the nginx config into place:

```bash
sudo cp deploy/nginx/ziliao.scor.vip.conf /etc/nginx/sites-available/ziliao.scor.vip.conf
sudo ln -s /etc/nginx/sites-available/ziliao.scor.vip.conf /etc/nginx/sites-enabled/ziliao.scor.vip.conf
sudo nginx -t
sudo systemctl reload nginx
```

7. Issue the HTTPS certificate:

```bash
sudo certbot --nginx -d ziliao.scor.vip
```

The production container only binds to `127.0.0.1:5002`, so it is intended to be exposed through Nginx instead of being opened directly to the internet.

## GitHub Auto Deploy

This repo now includes a GitHub Actions workflow:

- workflow file: [.github/workflows/deploy.yml](E:/projects/ziliao-scor-vip/.github/workflows/deploy.yml)

Behavior:

- every push to `main` triggers deployment
- you can also trigger it manually from GitHub Actions
- the workflow SSHes into your server, pulls the latest code, and rebuilds the production container

### 1. Prepare the server once

Clone the repo on the server, for example:

```bash
sudo mkdir -p /srv/ziliao-scor-vip
sudo chown -R $USER:$USER /srv/ziliao-scor-vip
git clone <your-github-repo-url> /srv/ziliao-scor-vip
cd /srv/ziliao-scor-vip
cp .env.production.example .env.production
docker compose -f docker-compose.prod.yml up --build -d
```

If the repo is private, the server also needs permission to pull from GitHub. The simplest way is to add a deploy key or use SSH for the clone.

### 2. Add GitHub repository secrets

In `GitHub -> Settings -> Secrets and variables -> Actions`, add:

- `DEPLOY_HOST`
  Your server IP or domain.
- `DEPLOY_PORT`
  Usually `22`.
- `DEPLOY_USER`
  The Linux user used for deployment.
- `DEPLOY_PATH`
  Example: `/srv/ziliao-scor-vip`
- `DEPLOY_SSH_KEY`
  The private SSH key that can log in to your server.

### 3. Ensure the deploy user can run Docker

On the server:

```bash
sudo usermod -aG docker <your-user>
newgrp docker
```

### 4. Push to GitHub

After that, every time you push to `main`:

```bash
git add .
git commit -m "update"
git push origin main
```

GitHub Actions will automatically:

1. connect to your server by SSH
2. `git pull` the latest code
3. run `docker compose -f docker-compose.prod.yml up -d --build`

If your default branch is not `main`, change `branches` and `DEPLOY_BRANCH` in [.github/workflows/deploy.yml](E:/projects/ziliao-scor-vip/.github/workflows/deploy.yml).
