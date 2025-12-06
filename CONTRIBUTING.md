# Contributing to Doctalk-AI

## 🤝 First Time Contributing? Welcome!

**It's normal to feel intimidated** - we've all been there! This guide will walk you through the process step-by-step.

## 🚀 How to Find Something to Do

### Start Here:

1. **Look for [`good first issue`](https://github.com/doctalk-ai/doctalk-ai/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22)** - These are specially tagged for beginners
2. **Check the [Project Board](https://github.com/doctalk-ai/doctalk-ai/projects/1)** - See what's being worked on
3. **Found a bug?** Open an issue and fix it!
4. **Have an idea?** Start a discussion first

### Still Unsure?

- **Comment on an issue** "I'd like to work on this!"
- **Ask in Discussions** "What's a good starting point?"
- **We'll help you** find the perfect first contribution

## 📝 Branch Naming Convention

**Please use this format:** `type/description`

### Types:

- `feat/` - New features (e.g., `feat/add-dark-mode`)
- `fix/` - Bug fixes (e.g., `fix/upload-error-handling`)
- `docs/` - Documentation (e.g., `docs/update-readme`)
- `style/` - Code style/formatting
- `refactor/` - Code restructuring

### Examples:

```bash
git checkout -b feat/add-txt-file-support
git checkout -b fix/chat-endpoint-error
git checkout -b docs/improve-setup-guide
✅ Commit Message Convention
Use this format: type: description

Types:
feat: - New feature

fix: - Bug fix

docs: - Documentation

style: - Formatting, missing semi-colons

refactor: - Code restructuring

test: - Adding tests

Examples:
bash
git commit -m "feat: add support for .txt file uploads"
git commit -m "fix: handle empty PDF files gracefully"
git commit -m "docs: update API endpoint examples"
💡 Code Quality Tips
Variable Naming:
typescript
// 👍 Good
const uploadedDocuments = []
const handleFileUpload = () => {}

// 👎 Avoid
const docs = []
const upload = () => {}
Python Best Practices:
python
# 👍 Good
def process_document_chunks(document_text: str) -> List[str]:
    """Split document into chunks for processing."""
    pass

# 👎 Avoid
def chunk(doc):
    pass
🔄 Pull Request Process
Fork the repository

Create your feature branch (git checkout -b feat/amazing-feature)

Commit your changes (git commit -m 'feat: add amazing feature')

Push to the branch (git push origin feat/amazing-feature)

Open a Pull Request

PR Description Template:
markdown
## What does this PR do?
- [ ] Adds feature X
- [ ] Fixes bug Y

## How was it tested?
- [ ] Tested locally
- [ ] Added unit tests

## Screenshots (if UI changes):
🎥 Watch & Learn
Check out our video tutorial showing:

How to pick your first issue

The complete PR process from start to finish

What we look for in code reviews

🗂️ Project Board
We use a Kanban-style board to track progress:

Backlog - Ideas and future features

To Do - Ready for development

In Progress - Currently being worked on

Review - PRs waiting for review

Done - Completed and merged

🆘 Getting Help
Stuck? Don't suffer in silence!

💬 Comment on the issue - we'll help you through it

💬 Start a Discussion - ask general questions

🔔 Tag @admaloch - for direct assistance

🌟 Your First PR
We celebrate first-time contributors! Your PR will get:

⚡ Quick review and feedback

🎉 Welcome message and shout-out

📚 Gentle guidance if needed

```
