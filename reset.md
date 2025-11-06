rm -rf .git / Remove-Item -Recurse -Force .git
git init
git add .
git commit -m "Fresh start"
git branch -M main
git remote add origin https://github.com/your-username/your-repo.git
git push --force --set-upstream origin main