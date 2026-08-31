# Push this replacement to GitHub

> Run these commands from the project root after replacing your local folder with this folder.

```bash
git status
git add -A
git commit -m "feat: add automated payment provider and harden VPN engine"
git push origin main
```

If Git says the branch has no upstream:

```bash
git push -u origin main
```

Before pushing, verify that `.env` is not tracked:

```bash
git status --short
git ls-files .env
```

`git ls-files .env` must print nothing.

After pulling on the server:

```bash
alembic upgrade head
```

Then restart the bot.
