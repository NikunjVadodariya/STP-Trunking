# GitHub Setup Instructions

## After creating the repository on GitHub, run these commands:

```bash
# Add the remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/SIP-Trunking.git

# Push to GitHub
git push -u origin main
```

## Alternative: Using SSH (if you have SSH keys set up)

```bash
git remote add origin git@github.com:YOUR_USERNAME/SIP-Trunking.git
git push -u origin main
```

## If you need to authenticate:

- For HTTPS: GitHub will prompt for username and Personal Access Token (not password)
- Create a Personal Access Token: https://github.com/settings/tokens
- For SSH: Make sure your SSH key is added to GitHub

## Verify the push:

Visit: https://github.com/YOUR_USERNAME/SIP-Trunking

