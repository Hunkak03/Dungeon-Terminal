# 🎮 Epic Terminal Roguelike

<p align="center">
  <strong>A comprehensive, feature-rich roguelike dungeon crawler built entirely in Python</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/Version-3.0_Ultimate-green.svg" alt="Version 3.0">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/License-MIT-orange.svg" alt="License MIT">
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Screenshots](#-screenshots)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Controls](#-controls)
- [Game Mechanics](#-game-mechanics)
- [Project Structure](#-project-structure)
- [Requirements](#-requirements)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

**Epic Terminal Roguelike** is a fully-featured, turn-based dungeon crawler rendered entirely in the terminal. Descend through **50 procedurally-generated floors** across 5 unique biomes, battle **15+ epic multi-phase bosses**, collect powerful artifacts, socket runes into your equipment, and make strategic choices in random encounters.

Built with **Python** and **curses**, this game demonstrates that compelling gameplay doesn't require graphics—just thoughtful design and deep mechanics.

### Key Highlights

- 🏰 **50 Floors** across 5 themed biomes with progressive difficulty
- ⚔️ **15+ Epic Bosses** with 3-5 phase transitions and unique abilities
- 🎒 **6 Rarity Tiers** from Common to Artifact with random stats
- ✨ **Rune Socketing** system with 10 rune types
- 🗺️ **Secret Rooms** hidden behind walls (12% chance per floor)
- 🎲 **7 Floor Events** with meaningful choices
- 💾 **Save/Load** system with 3 save slots
- 📊 **25+ Statistics** tracked per run

---

## ✨ Features

### 🎮 Core Gameplay

| Feature | Description |
|---------|-------------|
| **Procedural Dungeons** | Every run is unique with randomized rooms, corridors, and layouts |
| **5 Themed Biomes** | Dungeon → Dark Forest → Crystal Caves → Infernal Depths → The Void |
| **Turn-Based Combat** | Strategic, think-before-you-move gameplay |
| **4 Playable Classes** | Warrior, Mage, Rogue, Paladin with unique abilities |
| **50 Floor Progression** | Escalating difficulty with milestone bosses |

### ⚔️ Combat System

| Feature | Description |
|---------|-------------|
| **7 Elements** | Physical, Fire, Ice, Lightning, Poison, Dark, Holy, Void |
| **Elemental Effectiveness** | Rock-paper-scissors style weaknesses |
| **Critical Hits** | Chance-based with configurable rates |
| **Lifesteal** | Heal a percentage of damage dealt |
| **Status Effects** | Poisoned, Burning, Frozen, Stunned, Bleeding, Shielded |
| **Floating Damage** | Visual combat feedback with numbers |

### 🎒 Items & Equipment

| Category | Details |
|----------|---------|
| **Weapons** | 22+ types (Daggers, Swords, Axes, Staves, Bows, Katanas, Elemental weapons) |
| **Armor** | 8+ types (Leather, Chainmail, Plate, Robes, Cloaks) |
| **Rarities** | Common, Uncommon, Rare, Epic, Legendary, Artifact |
| **Runes** | 10 types socketable into equipment for permanent bonuses |
| **Consumables** | Potions, Bombs, Elixirs, Scrolls (Escape, Identify, Enchant) |
| **Artifact Sets** | 6 sets with 2-piece and 4-piece bonuses |

### 🗺️ Exploration

| Feature | Details |
|---------|---------|
| **Minimap** | Real-time display showing rooms, enemies, stairs, secrets |
| **Secret Rooms** | Hidden behind walls with guaranteed rare+ loot |
| **Boss Arenas** | Expanded rooms for epic multi-phase fights |
| **Traps** | Spikes, poison darts, fire, teleport, curse traps |
| **Environmental Hazards** | Lava pools, ice patches (biome-specific) |

### 🎲 Random Events

| Event | Description |
|-------|-------------|
| **Mysterious Merchant** | Buy mystery items at a price |
| **Ancient Shrine** | Pray for blessings or risk desecration |
| **Trapped Adventurer** | Help, rob, or leave |
| **Cursed Treasure** | Take gold (risk curse) or inspect safely |
| **Rune Master** | Learn about runes or receive one free |
| **Enchantment Forge** | Upgrade equipment with magical fire |
| **Fountain of Youth** | Full heal, potions, or leave |

### 💾 Quality of Life

| Feature | Details |
|---------|---------|
| **Save/Load** | 3 save slots with JSON serialization |
| **Statistics** | 25+ tracked metrics (damage, exploration, items, time) |
| **Achievements** | 14 achievements with popup notifications |
| **Bestiary** | Track defeated monsters and their stats |
| **Death Screen** | Comprehensive run statistics |

---

## 📸 Screenshots

```
┌─────────────────────────────────────────────────────────────┐
│  Floor 15/50  |  Lvl 12  |  XP 145/280  |  Gold: 350       │
│  HP: [##########----------] 85/120                          │
│  STR:28  RES:18  LUCK:15  VIT:10                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ###############    #############                          │
│   #.............#    #...........#                          │
│   #..@..........#####..........#    Floor 15 - Dark Forest  │
│   #.......s...........k......##                             │
│   #..####.........####.....#    [G] Crimson Flame Sword     │
│   #..#  #.........#  #.....#    [EPIC]                      │
│   #..#..###########..#.....#                                │
│   #..#.............O.#.....#    > Stairs Down               │
│   #..#.................B...#    ? Shrine of Power           │
│   #..#####################..#                               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  You hit Skeleton for 34 damage.                            │
│  Skeleton hits you for 8 damage.                            │
│  Orc takes 45 damage from War Cry!                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation

### Prerequisites

- **Python 3.12 or higher**
- **Windows, Linux, or macOS**

### Windows

```powershell
# Clone or download the repository
cd "Roguelike game"

# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py
```

### Linux / macOS

```bash
# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py
```

> **Note for Windows users:** The game uses `windows-curses` for terminal rendering. This is included in `requirements.txt`.

---

## 🎮 Quick Start

1. **Launch the game**
   ```
   python main.py
   ```

2. **Read the Controls Guide** (appears automatically on first launch)

3. **Choose your class**
   - **Warrior** - High STR, starts with weapon, AoE War Cry
   - **Mage** - High LUCK/VIT, elemental Fireball ability
   - **Rogue** - High crit chance, Shadow Step teleport + crit
   - **Paladin** - High RES/VIT, Divine Shield immunity

4. **Begin your descent**
   - Explore rooms, fight monsters, collect loot
   - Find the boss and defeat it to unlock stairs
   - Descend 50 floors and defeat the Dark God!

---

## 🎹 Controls

### Movement & Combat

| Key | Action |
|-----|--------|
| `↑` `↓` `←` `→` | Move in cardinal directions |
| `W` `A` `S` `D` | Alternative movement |
| Move into enemy | Attack monster |
| `.` (period) | Wait one turn |

### Items & Equipment

| Key | Action |
|-----|--------|
| `G` | Pick up items on current tile |
| `I` | Open inventory (use/equip items) |
| `C` | View equipped items |
| `E` | Interact (merchants, shrines, events) |

### Character & Exploration

| Key | Action |
|-----|--------|
| `K` | View stats & learn traits |
| `U` | Use class special ability |
| `>` | Descend stairs (stand on `>` tile) |
| `B` | View bestiary |
| `?` | Show help screen |

### System

| Key | Action |
|-----|--------|
| `F5` | **Save game** (slot 1) |
| `F9` | **Load game** (3 slots) |
| `Q` | Quit game |
| `Esc` | Close menus/panels |
| `Enter` | Confirm selections |

---

## 📖 Game Mechanics

### 🎯 Character Progression

**Stats:**
- **Strength (STR)** - Increases damage by +0.5% per point
- **Resistance (RES)** - Reduces damage taken by 0.5% per point (cap 90%)
- **Luck (LUCK)** - Increases crit chance by +0.3% and improves drop rarity
- **Vitality (VIT)** - Increases max HP by +12 per point

**Leveling:**
- Gain XP by defeating monsters
- Level up grants +1 Trait Point
- Choose from 20+ traits (3 ranks each)
- Traits provide permanent passive bonuses

### ⚔️ Combat Formula

```
Damage = Base_Weapon_Damage × (1 + STR × 0.005) × Damage_Multipliers

Crit_Chance = 5% + (LUCK × 0.003) + Equipment_Bonuses

Crit_Damage = Damage × 1.5 × Crit_Damage_Bonuses

Final_Damage = max(1, Damage × (1 - Resistance_Reduction))
```

### 🎒 Item Rarity

| Rarity | Base Weight | Notes |
|--------|-------------|-------|
| Common | 70 | 1 booster, basic stats |
| Uncommon | 35 | 1 booster, moderate stats |
| Rare | 18 | 2 boosters, good stats |
| Epic | 8 | 2 boosters, high stats |
| Legendary | 1 + (LUCK × 0.3) | 3 boosters, excellent stats |
| Artifact | Special | Set bonuses, guaranteed stats |

> **Tip:** Luck stat increases the weight of Legendary items, making them more common.

### 🗺️ Floor Structure

| Floor Range | Biome | Features |
|-------------|-------|----------|
| 1 - 10 | Dungeon | Traps, guards, undead |
| 11 - 20 | Dark Forest | Wildlife, treants, fey |
| 21 - 30 | Crystal Caves | Elementals, gems |
| 31 - 40 | Infernal Depths | Lava, demons, fire hazards |
| 41 - 50 | The Void | Eldritch horrors, reality bends |

**Boss Floors:** Every 5th floor (5, 10, 15, 20, 25, 30, 35, 40, 45, 50)

**Special Floors:**
- **Floor 10:** Iron Golem / Forest Warden
- **Floor 20:** Crystal Lich / Demon Lord
- **Floor 30:** Abyss King / Frost Queen
- **Floor 40:** Void Herald / Ancient Dragon
- **Floor 50:** The Dark God (Final Boss)

---

## 📁 Project Structure

```
Roguelike game/
├── main.py                     # Main entry point (run this!)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── src/                        # Game source code
│   ├── __init__.py             # Package initializer
│   ├── constants.py            # Game constants & enumerations
│   ├── utils.py                # Utility functions (distance, RNG)
│   ├── items.py                # Item system (weapons, armor, runes)
│   ├── entities.py             # Player, monsters, bosses, traits
│   ├── dungeon.py              # Procedural dungeon generation
│   ├── combat.py               # Combat calculations, boss AI
│   ├── events.py               # Shrines, merchants, traps
│   └── game_systems.py         # Save/load, stats, damage numbers
│
├── docs/                       # Documentation
│   ├── README.md               # Full game documentation
│   ├── CHANGELOG.md            # Update history
│   ├── FEATURES_SUMMARY.md     # Feature details
│   ├── INTEGRATION_GUIDE.md    # Integration instructions
│   └── ORGANIZATION_SUMMARY.md # Project structure info
│
└── assets/
    └── audio/                  # Sound effects & BGM
        ├── bgm.wav
        ├── hit.wav
        ├── crit.wav
        ├── death.wav
        └── loot.wav
```

---

## 📦 Requirements

| Package | Version | Purpose |
|---------|---------|---------|
| `windows-curses` | >=2.3 | Terminal rendering (Windows) |
| `pygame` | >=2.6 | Audio system (optional) |

> **Note:** `pygame` is optional. The game runs without it (silently skips audio).

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Guidelines

- Follow existing code style and conventions
- Add comments for complex logic
- Test your changes thoroughly
- Update documentation if needed

---

## 🐛 Known Issues

- Terminal size below 80x24 may cause display issues
- Some curses implementations on non-Windows platforms may vary
- Audio requires `pygame` and may not work on all systems

---

## 📄 License

This project is licensed under the **MIT License**. See the LICENSE file for details.

---

## 🙏 Acknowledgments

- Inspired by classic roguelikes: NetHack, Angband, Brogue
- Built with [Python](https://www.python.org/) and [curses](https://docs.python.org/3/library/curses.html)
- Audio generated procedurally with [pygame](https://www.pygame.org/)

---

<p align="center">
  <strong>Made with ❤️ in Python</strong><br>
  <em>Version 3.0 - Ultimate Edition | April 2026</em>
</p>
