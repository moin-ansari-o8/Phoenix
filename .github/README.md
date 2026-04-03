# GitHub Configuration

This folder contains configuration files for GitHub Copilot and project automation.

## 📄 Files

### `AGENT.md`
**Full detailed instructions** for AI agents (GitHub Copilot, CLI agents, etc.)
- Complete folder structure guidelines
- File placement rules and decision trees
- Code examples and anti-patterns
- Pre-commit checklist

**Use this for:** Comprehensive reference, onboarding new AI agents

### `copilot-instructions.md`
**Quick reference** for GitHub Copilot (VS Code)
- Quick folder lookup table
- Essential rules
- Fast decision tree
- Common examples

**Use this for:** Quick lookups while coding

---

## 🎯 Purpose

These instructions ensure:
- ✅ Organized folder structure maintained
- ✅ Files don't scatter in root directory
- ✅ Consistent file placement across team/agents
- ✅ Easy navigation and maintenance

---

## 🤖 How GitHub Copilot Uses These

**Standard behavior:**
- Copilot reads `.github/copilot-instructions.md` automatically
- Applied to all code suggestions and chat responses
- Helps maintain project structure consistency

**Custom agents:**
- Can reference `AGENT.md` for detailed guidelines
- Used for complex refactoring and file organization
- Provides comprehensive context

---

## 🔄 Updating Instructions

**When to update:**
- New folder categories added
- File organization patterns change
- New file types introduced
- Team conventions evolve

**How to update:**
1. Edit `AGENT.md` (comprehensive) and/or `copilot-instructions.md` (quick ref)
2. Test with Copilot to ensure it follows new rules
3. Commit changes
4. Notify team

---

## 📚 Related Documentation

- `../REORGANIZATION_PLAN.md` - Folder reorganization plan
- `../REORGANIZATION_QUICKSTART.md` - Quick start guide
- `../docs/analysis/PHOENIX_COMPREHENSIVE_ANALYSIS.md` - Project architecture

---

**Maintain these instructions to keep Phoenix organized! 🚀**
