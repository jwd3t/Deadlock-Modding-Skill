# Deadlock Modding Skill for AI Agents 🎮⚡

[![Source 2](https://img.shields.io/badge/Engine-Source%202-orange.svg)](https://developer.valvesoftware.com/wiki/Source_2)
[![Game](https://img.shields.io/badge/Game-Deadlock-blue.svg)](https://store.steampowered.com/app/1422450/Deadlock/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An expert, battle-tested agent skill for reverse engineering, developing, debugging, and packaging mods for Valve's **Deadlock** (Source 2 engine).

Equips AI coding assistants (Google Antigravity, Claude Code, Cursor, Codex, OpenDevin) with deep domain knowledge of Source 2 binary formats, particle systems, sound event coordination, hardware texture compression, and VAC-compliant client-side modding.

---

## 📦 What's Inside?

* **`SKILL.md`**: The complete reverse-engineering and modding runbook:
  * **Audio Modding (`.vsnd_c` & `.vsndevts_c`)**: 48,000 Hz MPEG frames, LZ4 control block structure, `vsnd_duration` cut-off fix, in-engine decibel gain mixing (`volume_offset_player`, `volume_enemy_targeting_boost`).
  * **Texture Modding (`.vtex_c`)**: Hardware DXT5 (BC3) compression requirements, GPU sampler fallback rules (avoiding error "X" sprites), UV roll compensation (pre-rotating 90° CCW).
  * **Particle Systems (`.vpcf_c`)**: `KVFlag.Resource` requirements, preserving vanilla children (`outer`, `bits`, `model`, `tube`) for multi-mod compatibility, screen-facing billboards.
  * **Proximity & Distance Culling**:
    * Reverse-engineered disassembly of Valve's early-exit bug in `C_OP_DistanceCull` (`ja 0x18018805f`).
    * Proven Self-Immunity formula with `C_OP_DistanceCull` ($80.0$ unit threshold).
    * Dynamic distance cut-off using `C_OP_DistanceToTransform` with `PARTICLE_SET_SCALE_CURRENT_VALUE`.
    * Critical operator execution order to prevent ghost pop-ins.
  * **Defensive Telegraph Architecture**: Step-by-step design for personal alert systems (e.g. Sekiro Perilous Attack indicators).
* **`scripts/pack_vpk.py`**: Lightweight, standalone Python VPK v1 packager with zero third-party dependencies (no `vpk.exe` or .NET SDK required to pack).

---

## 🚀 Installation

### 1. Global Installation (Antigravity / Gemini CLI)
Clone directly into your global skills directory:

```bash
git clone https://github.com/jwd3t/Deadlock-Modding-Skill.git ~/.gemini/config/skills/deadlock-modding
```

Or on Windows PowerShell:
```powershell
git clone https://github.com/jwd3t/Deadlock-Modding-Skill.git "$HOME\.gemini\config\skills\deadlock-modding"
```

### 2. Workspace / Project Installation
To equip an agent specifically when working inside a modding repository:

```bash
mkdir -p .agents/skills
git clone https://github.com/jwd3t/Deadlock-Modding-Skill.git .agents/skills/deadlock-modding
```

### 3. Usage with Other Agents (Claude Code, Cursor, OpenDevin)
Copy or symlink `SKILL.md` into your agent's knowledge or prompt directory (e.g. `.cursorrules`, `CLAUDE.md`, or system instructions).

---

## 🛠️ Standalone VPK Packager Usage

You can use the included `scripts/pack_vpk.py` to package any Deadlock mod directory directly:

```bash
# Package into pak01_dir.vpk
python scripts/pack_vpk.py ./extracted -o pak01_dir.vpk

# Package and create a ZIP ready for Deadlock Mod Manager
python scripts/pack_vpk.py ./extracted -o pak01_dir.vpk -z My_Deadlock_Mod.zip
```

---

## 🛡️ Anti-Cheat & Safety Compliance

* **100% Client-Side**: All techniques in this skill exclusively modify client-side visual, audio, and particle representations.
* **No Memory Injection / Overlays**: Strictly avoids DLL injection or process hooking, keeping users safe from VAC bans.
* **Non-Destructive**: Never writes directly into Steam directories; outputs are generated locally for safe manual loading or use with [Deadlock Mod Manager](https://github.com/deadlock-mod-manager).

---

## 📄 License

Distributed under the [MIT License](LICENSE).
