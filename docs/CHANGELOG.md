# Changelog - Latest Update

## 🎮 New Features & Improvements

### 📍 Item Display Enhancement
- **Item names now appear** when you stand on the same tile as an item
- Shows item name and rarity with color coding
- Single item: Displays full name with rarity badge
- Multiple items: Shows count and "Press G to pick up" message
- Color-coded based on item rarity (white/green/cyan/magenta/yellow/red)

### 👾 Enhanced Monster System
**Added 15+ new enemy types:**

#### Elite Monsters (Floor 10+)
- Ogre - Heavy hitter with high HP
- Wraith - Fast and deadly
- Troll - Regenerating brute
- Lesser Demon - Fire-resistant demon
- Dark Cultist - Magic user
- Stone Golem - Armored tank

#### Biome-Specific Monsters
**Dungeon (Floors 1-10):**
- Dungeon Guard - Elite guard
- Undead Prisoner - Restless spirit

**Dark Forest (Floors 11-20):**
- Dire Wolf - Pack hunter
- Corrupted Treant - Ancient guardian
- Shadow Dryad - Deceptive fey

**Crystal Caves (Floors 21-30):**
- Crystal Bug - Gem-encrusted insect
- Troglodyte - Cave dweller
- Earth Elemental - Living rock

**Infernal Depths (Floors 31-40):**
- Fire Imp - Mischievous demon
- Hellhound - Fire-breathing hound
- Young Balrog - Ancient fire demon

**The Void (Floors 41-50):**
- Voidling - Void creature
- Eldritch Horror - Unspeakable being
- Warp Stalker - Teleporting predator

### 🏠 Smarter Monster Placement
- Monsters now spawn **inside rooms** instead of random locations
- 1-2 monsters per room on deeper floors
- Better distribution across the map
- Monsters maintain minimum distance from player spawn
- More strategic exploration required

### 🎁 Improved Loot Distribution
**Room-Based Item Placement:**
- Items now spawn **inside rooms** for better exploration rewards
- Each room gets at least one item
- **Treasure rooms** have 30% chance for bonus items
- Treasure room items get +5 luck bonus for better rarity rolls

**Progressive Rarity System:**
- **Floor 10+**: 20% chance for guaranteed Rare+ items
- **Floor 20+**: 10% chance for guaranteed Epic+ items
- Deeper floors = better loot quality
- All items have **random stats** and **random rarity**
- Luck stat influences drop quality

### 🎯 Better Game Balance
- Monster count scales gently: 4 + floor/3 (was 5 + floor/2)
- More manageable early game
- Smoother difficulty curve
- Better room-to-room pacing

### 📊 UI Improvements
- Item name display with color-coded rarity
- Clear "[G]" prompt when items are on your tile
- Better visual feedback for loot
- Maintained clean, uncluttered HUD

---

## 🎮 How to Play

```powershell
cd "C:\Users\Daniel IES\Documents\Roguelike game"
python main.py
```

### Key Controls
- **Arrow Keys / WASD**: Move / Attack
- **G**: Pick up items (item name shows when you're on it!)
- **I**: Inventory
- **C**: Equipment
- **K**: Stats & Traits
- **B**: Bestiary
- **U**: Class Ability
- **>**: Descend stairs
- **Q**: Quit

---

## 💡 Tips

1. **Explore every room** - Items are distributed across rooms
2. **Check your tile** - Item names appear when you walk over them
3. **Floor 10+** drops better rarity items
4. **Floor 20+** has chances for Epic items
5. **Treasure rooms** often have bonus loot
6. **Luck stat** improves drop quality - invest in it!
7. **Different biomes** have unique monsters - prepare accordingly

---

## 🐛 Bug Fixes
- Fixed undefined element references in combat system
- Improved item spawning logic
- Better room-based entity placement
- Enhanced loot distribution fairness

---

*Last Updated: April 9, 2026*
*Version: 2.0 - Enhanced Edition*
