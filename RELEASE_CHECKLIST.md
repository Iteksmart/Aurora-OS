# Release Checklist v0.3.1

**Purpose:** Ensure every release maintains credibility and quality  
**For:** Aurora OS maintainers  
**Status:** TEMPLATE for future releases

---

## Pre-Release Checklist

### 🔧 Build Verification

- [ ] **ISO builds successfully**
  - [ ] Build completes without errors
  - [ ] Build time recorded
  - [ ] Build logs saved

- [ ] **ISO size is reasonable**
  - [ ] Size matches expected range
  - [ ] Size difference from previous release explained
  - [ ] No unexpected bloat

- [ ] **All editions built**
  - [ ] Complete Edition
  - [ ] Framework Lite
  - [ ] Kernel binary extracted

### 🧪 Quality Checks

- [ ] **Boot testing**
  - [ ] QEMU boot successful
  - [ ] VirtualBox boot successful  
  - [ ] No kernel panics
  - [ ] systemd starts correctly

- [ ] **Basic functionality**
  - [ ] `uname -a` shows correct kernel version
  - [ ] `ls /usr/lib/systemd` shows systemd files
  - [ ] `ls /usr/bin/aurora-*` shows Aurora commands
  - [ ] Python interpreter works

- [ ] **Checksums generated**
  - [ ] SHA256 for all ISOs
  - [ ] MD5 for all ISOs
  - [ ] Checksums verified locally

### 📝 Documentation

- [ ] **Release notes accurate**
  - [ ] Date is correct (not future)
  - [ ] Version number correct
  - [ ] Edition names consistent
  - [ ] Sizes match actual files
  - [ ] No contradictory claims

- [ ] **Technical details honest**
  - [ ] Init system clearly explained (systemd PID 1)
  - [ ] Offline capabilities accurately described
  - [ ] Dependencies listed
  - [ ] Known limitations included

- [ ] **Links functional**
  - [ ] All download links work
  - [ ] Checksum links work
  - [ ] Documentation links work
  - [ ] External links valid

### 🔐 Security

- [ ] **No sensitive data in ISO**
  - [ ] No hardcoded passwords
  - [ ] No API keys
  - [ ] No private keys

- [ ] **Checksums match**
  - [ ] SHA256 verified
  - [ ] MD5 verified
  - [ ] No corruption

---

## Release Process

### 1️⃣ Create Release Tag

```bash
# Create annotated tag
git tag -a v0.3.1 -m "Aurora OS v0.3.1 - [Brief description]"

# Push tag
git push origin v0.3.1
```

### 2️⃣ Build All Artifacts

```bash
# Build Complete Edition
sudo ./tools/build_ultimate_complete.sh

# Build Framework Lite
sudo ./tools/build_ultimate.sh

# Extract kernel
cp build/kernel/vmlinuz ./

# Generate checksums
for iso in *.iso; do
  sha256sum "$iso" > "$iso.sha256"
  md5sum "$iso" > "$iso.md5"
done
```

### 3️⃣ Verify Artifacts

```bash
# Verify ISO structure
file aurora-os-ultimate-complete.iso

# Verify bootability
xorriso -indev aurora-os-ultimate-complete.iso -report_el_torito as_mkisofs

# Boot test
qemu-system-x86_64 -cdrom aurora-os-ultimate-complete.iso -m 4096 -smp 2
```

### 4️⃣ Create GitHub Release

```bash
# Create release with all artifacts
gh release create v0.3.1 \
  --title "Aurora OS v0.3.1 - [Title]" \
  --notes-file RELEASE_v0.3.1.md \
  --prerelease \
  aurora-os-ultimate-complete.iso \
  aurora-os-ultimate-complete.iso.sha256 \
  aurora-os-ultimate-complete.iso.md5 \
  aurora-os-ultimate.iso \
  aurora-os-ultimate.iso.sha256 \
  aurora-os-ultimate.iso.md5 \
  vmlinuz
```

### 5️⃣ Verify Release

```bash
# Check release exists
gh release view v0.3.1

# Verify all assets attached
gh release view v0.3.1 --json assets --jq '.assets[].name'

# Download and verify
wget https://github.com/Iteksmart/Aurora-OS/releases/download/v0.3.1/aurora-os-ultimate-complete.iso
sha256sum -c aurora-os-ultimate-complete.iso.sha256
```

---

## Post-Release Checklist

### 📢 Announcements

- [ ] **Update README.md**
  - [ ] Version number updated
  - [ ] Download links updated
  - [ ] Checksums updated

- [ ] **Update documentation**
  - [ ] VERIFICATION_COMPLETE.md
  - [ ] PUBLIC_VERIFICATION.md
  - [ ] VERIFY_IN_5_MINUTES.md

- [ ] **Commit and push changes**
  ```bash
  git add README.md [other files]
  git commit -m "docs: Update for v0.3.1 release"
  git push origin main
  ```

### 🔍 Verification

- [ ] **Run 5-minute verification**
  - [ ] Release exists via API
  - [ ] ISO downloads
  - [ ] Checksum matches
  - [ ] ISO structure valid
  - [ ] Bootability confirmed

- [ ] **CI/CD status**
  - [ ] All workflows passing
  - [ ] No build failures

### 📊 Monitoring

- [ ] **Track issues**
  - [ ] Watch for new issues
  - [ ] Respond to bug reports
  - [ ] Address critical bugs quickly

- [ ] **Gather feedback**
  - [ ] User testing reports
  - [ ] Technical reviews
  - [ ] Performance metrics

---

## Common Mistakes to Avoid

### ❌ Date Issues
- Setting release date in the future
- Inconsistent dates across documentation

### ❌ Size Confusion
- Multiple editions with same size but different names
- Not explaining why sizes are identical

### ❌ Contradictory Claims
- "100% offline" but "requires download"
- "Production ready" but "Alpha release"

### ❌ Missing Artifacts
- Release created but ISOs not attached
- Checksums not uploaded
- Kernel binary missing

### ❌ Broken Links
- Download links point to wrong version
- Documentation links 404
- External references broken

---

## Emergency Fixes

If a critical issue is found post-release:

### For Documentation Errors
```bash
# Edit release notes
gh release edit v0.3.1 --notes-file RELEASE_v0.3.1_FIXED.md

# Update docs
git add [files]
git commit -m "fix: Critical documentation error in v0.3.1"
git push origin main
```

### For ISO Issues
```bash
# Delete release
gh release delete v0.3.1 --yes

# Fix build
sudo ./tools/build_ultimate_complete.sh

# Recreate release
gh release create v0.3.1 [with new ISOs]
```

---

## Quality Standards

### Minimum Requirements
- ✅ ISO boots in QEMU
- ✅ Kernel version matches docs
- ✅ systemd starts
- ✅ No critical errors in boot log

### Credibility Requirements
- ✅ Accurate technical claims
- ✅ Honest about limitations
- ✅ Consistent naming
- ✅ Correct dates
- ✅ Working download links

### Excellence Standards
- ✅ Comprehensive release notes
- ✅ Clear verification instructions
- ✅ Known issues documented
- ✅ Roadmap for next version
- ✅ Professional presentation

---

## Version Numbering

**Format:** `vMAJOR.MINOR.PATCH-STAGE`

**Examples:**
- `v0.3.1-alpha` - Alpha release, patch 1
- `v0.4.0-beta` - Beta release, new features
- `v1.0.0` - First stable release

**Stages:**
- `alpha` - Early testing, features incomplete
- `beta` - Feature complete, stabilizing
- `rc1, rc2` - Release candidate, final testing
- (none) - Stable release

---

## Success Metrics

### Technical
- [ ] ISO boots on target hardware
- [ ] No critical bugs reported in first 48h
- [ ] All verification steps pass

### Community
- [ ] Positive feedback from testers
- [ ] Technical reviews completed
- [ ] Issues addressed promptly

### Credibility
- [ ] No accuracy corrections needed
- [ ] Reviewers confirm claims
- [ ] Documentation praised for clarity

---

## Template: Release Notes Structure

```markdown
# Aurora OS vX.Y.Z-stage - [Brief Title]

## 🎯 What is Aurora OS?
[Clear, honest description]

**Release Date:** [Correct date]
**Status:** [Alpha/Beta/Stable]
**License:** GPL v2

## 📦 Available Editions
[Clear edition names and purposes]

## 🚀 Key Features
[Accurate, honest feature list]

## 📥 Downloads
[Working links, correct checksums]

## 🧪 Quick Test
[Copy-paste verification commands]

## 🔧 What's Included
[Technical breakdown]

## ⚠️ Known Limitations
[Honest about what doesn't work]

## 📋 Verification Checklist
[Step-by-step verification]

## 🔜 Roadmap
[What's coming next]
```

---

**Remember:** Credibility > Features. An honest alpha is better than an overhyped beta.

---

**Last Updated:** December 13, 2025  
**For Release:** v0.3.1+  
**Maintainers:** Aurora OS Team
