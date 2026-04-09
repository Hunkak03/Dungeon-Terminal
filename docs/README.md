## 🎮 EPIC TERMINAL ROGUELIKE

A comprehensive, feature-rich roguelike dungeon crawler with 50 floors, epic multi-phase bosses, artifacts, traits, elemental combat, and more!

### 📁 Project Structure

```
Roguelike game/
├── main.py                  # Main game file (run this!)
├── requirements.txt         # Python dependencies
├── src/                     # Game source code
│   ├── __init__.py
│   ├── constants.py         # Game constants
│   ├── utils.py             # Utility functions
│   ├── items.py             # Item system
│   ├── entities.py          # Player & monsters
│   ├── dungeon.py           # Dungeon generation
│   ├── combat.py            # Combat system
│   ├── events.py            # Events & encounters
│   └── game_systems.py      # Save/load, stats, etc.
├── docs/                    # Documentation
│   ├── README.md
│   ├── CHANGELOG.md
│   ├── FEATURES_SUMMARY.md
│   └── INTEGRATION_GUIDE.md
└── assets/
    └── audio/               # Sound files
```

### ✨ Features

- **50 Floors** across 5 themed biomes (Dungeon, Forest, Caves, Hell, Void)
- **15+ Epic Bosses** with 3-5 phase transitions and unique abilities
- **Artifact System** with set bonuses
- **Trait/Perk System** for character customization
- **Elemental Combat** (Fire, Ice, Lightning, Poison, Dark, Holy, Void)
- **Rune System** - Socket runes into equipment for bonuses
- **Secret Rooms** - Hidden behind walls with better loot
- **Floor Events** - Shrines, merchants, encounters with choices
- **Save/Load System** - 3 save slots (F5 to save)
- **Minimap** - Top-right corner shows dungeon layout
- **Damage Numbers** - Floating combat feedback
- **Achievement Popups** - Notifications when unlocked
- **Full Statistics** - 25+ tracked metrics on death screen
- **Procedurally Generated** dungeons with rooms and corridors

### 🚀 Installation

```powershell
pip install -r requirements.txt
```

### 🎮 Running

```powershell
python main.py
```

### 📖 Controls Guide

When you start the game, you'll see a comprehensive controls guide showing:

**📍 MOVEMENT**
- `↑ ↓ ← → / WASD` - Move around
- Move into enemy - Attack
- `.` - Wait one turn

**🎒 ITEMS & EQUIPMENT**
- `G` - Pick up items
- `I` - Inventory
- `C` - Equipment
- `E` - Interact (merchants, shrines, events)

**👤 CHARACTER**
- `K` - Stats & Traits
- `U` - Class ability

**🗺️ EXPLORATION**
- `>` - Descend stairs
- `B` - Bestiary
- `?` - Help

**⚙️ SYSTEM**
- `F5` - Save game (3 save slots)
- `F9` - Load game
- `Q` - Quit
- `Esc` - Close menus
- `Enter` - Confirm

### 🎯 Classes

- **Warrior**: High STR, War Cry (AoE damage)
- **Mage**: High LUCK/VIT, Fireball (ranged nuke)
- **Rogue**: High LUCK, Shadow Step (teleport + crit)
- **Paladin**: High RES/VIT, Divine Shield (immunity)

### 💡 Tips

1. **Read the startup guide** - Shows all controls
2. **Explore every room** - Items are distributed across rooms
3. **Check your tile** - Item names appear when you walk over them
4. **Floor 10+** drops better rarity items
5. **Invest in Luck** - Improves drop quality
6. **Use class abilities** - They're powerful with cooldowns
7. **Secret rooms** - Walk into walls near rooms to find them!

### 🐛 Notes

- Turn-based roguelike - think before you move!
- Death is permanent, but you can restart immediately
- Each run is unique due to procedural generation
- On Windows, ensure `windows-curses` is installed

---

*Version: 3.0 - Ultimate Edition*
*Last Updated: April 9, 2026*
