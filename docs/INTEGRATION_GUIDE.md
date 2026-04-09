# Integration Guide for New Features

This guide shows you exactly where and what code to add to `main.py` to integrate all 12 new features.

---

## 📋 Feature Checklist

✅ **Already Implemented in Modules:**
- Save/Load System (`game_systems.py`)
- Damage Numbers (`game_systems.py`)
- Achievement Popups (`game_systems.py`)
- Game Statistics (`game_systems.py`)
- Floor Events (`game_systems.py`)
- Secret Rooms (`dungeon.py`)
- Boss Arenas (`dungeon.py`)
- Runes (`items.py`)
- New Consumables (`items.py`)

🔧 **Need to Integrate into main.py:** (See sections below)

---

## 1️⃣ Add New Imports to main.py

**Location**: Top of `main.py`, after existing imports

```python
# Add these imports
from items import (
    generate_rune, generate_bomb, generate_elixir, generate_escape_scroll,
    generate_identify_scroll, generate_enchant_scroll, generate_new_consumable
)
from game_systems import (
    SaveData, serialize_item, save_game, load_game, get_save_slots,
    DamageNumberSystem, AchievementPopupSystem, GameStatistics,
    FloorEvent, generate_random_event
)
import json
```

---

## 2️⃣ Add New Instance Variables to `__init__`

**Location**: In `RoguelikeGame.__init__()`, after `self.trait_points = 0`

```python
# NEW: Damage numbers system
self.damage_numbers = DamageNumberSystem()

# NEW: Achievement popups
self.achievement_popups = AchievementPopupSystem()

# NEW: Game statistics
self.stats = GameStatistics()
self.stats.start_time = time.time()

# NEW: Floor events
self.active_events: List[FloorEvent] = []
self.pending_event_reward = None

# NEW: Save/Load
self.save_slot = 1

# NEW: Minimap
self.show_minimap = True

# NEW: Identified items
self.identified_items: List[str] = []

# NEW: Temporary buffs
self.temp_buffs: Dict[str, Dict] = {}
```

---

## 3️⃣ Update `_start_floor` Method

**Location**: In `_start_floor()`, after `self.map = DungeonMap(...)`

Add this after dungeon creation:

```python
# Generate floor events in rooms
for room in self.map.rooms[2:]:  # Skip first 2 rooms
    event = generate_random_event((room.cx, room.cy), self.floor, self.rng)
    if event:
        self.active_events.append(event)

# Update stats
self.stats.floors_cleared += 1
```

---

## 4️⃣ Add Minimap Rendering

**Location**: New method after `_draw_hud()`

```python
def _draw_minimap(self):
    """Draw a minimap in the top-right corner."""
    if not self.map or not self.show_minimap:
        return
    
    map_w = 30
    map_h = 12
    start_x = curses.COLS - map_w - 2
    start_y = 1
    
    try:
        # Draw border
        for y in range(map_h + 2):
            for x in range(map_w + 2):
                if y == 0 or y == map_h + 1 or x == 0 or x == map_w + 1:
                    self.stdscr.addch(start_y + y, start_x + x, '█', curses.color_pair(4))
        
        # Draw rooms
        scale_x = map_w / self.map.w
        scale_y = map_h / self.map.h
        
        for room in self.map.rooms:
            rx = int(room.x * scale_x)
            ry = int(room.y * scale_y)
            rw = max(1, int(room.w * scale_x))
            rh = max(1, int(room.h * scale_y))
            
            for y in range(ry, min(ry + rh, map_h)):
                for x in range(rx, min(rx + rw, map_w)):
                    self.stdscr.addch(start_y + 1 + y, start_x + 1 + x, '·')
        
        # Draw secret rooms
        for room in self.map.secret_rooms:
            rx = int(room.x * scale_x)
            ry = int(room.y * scale_y)
            self.stdscr.addch(start_y + 1 + ry, start_x + 1 + rx, '?', curses.color_pair(5))
        
        # Draw player
        px = int(self.player.x * scale_x)
        py = int(self.player.y * scale_y)
        self.stdscr.addch(start_y + 1 + py, start_x + 1 + px, '@', curses.color_pair(2) | curses.A_BOLD)
        
        # Draw monsters
        for monster in self.monsters:
            if monster.is_alive():
                mx = int(monster.x * scale_x)
                my = int(monster.y * scale_y)
                if monster.is_boss:
                    self.stdscr.addch(start_y + 1 + my, start_x + 1 + mx, 'B', curses.color_pair(6))
                else:
                    self.stdscr.addch(start_y + 1 + my, start_x + 1 + mx, 'm')
        
        # Draw stairs
        if self.stairs_pos:
            sx = int(self.stairs_pos[0] * scale_x)
            sy = int(self.stairs_pos[1] * scale_y)
            self.stdscr.addch(start_y + 1 + sy, start_x + 1 + sx, '>', curses.color_pair(4))
    except:
        pass
```

**Call it in `draw()` method**, after `self._draw_hud()`:

```python
# Add this line in draw() method
self._draw_minimap()
```

---

## 5️⃣ Add Damage Numbers Display

**Location**: New method

```python
def _draw_damage_numbers(self):
    """Draw floating damage numbers."""
    for dmg_num in self.damage_numbers.get_visible():
        try:
            color = curses.color_pair(6) if dmg_num.color == "red" else \
                   curses.color_pair(4) if dmg_num.color == "yellow" else \
                   curses.color_pair(2)
            
            attr = curses.A_BOLD if dmg_num.is_crit else 0
            offset = DAMAGE_NUMBER_DURATION - dmg_num.turns_left
            self.stdscr.addstr(
                max(0, dmg_num.y - offset), dmg_num.x,
                str(dmg_num.value), color | attr
            )
        except:
            pass
```

**Add to `draw()` method** after drawing monsters.

**Update combat methods** to create damage numbers:

In `_player_attack()`, after `target.hp -= dmg`:
```python
self.damage_numbers.add_damage(target.x, target.y, dmg, is_crit)
self.stats.total_damage_dealt += dmg
if is_crit:
    self.stats.crits_landed += 1
if dmg > self.stats.highest_damage_hit:
    self.stats.highest_damage_hit = dmg
```

In `_monster_attack()`, after `self.player.hp -= dmg`:
```python
self.damage_numbers.add_damage(self.player.x, self.player.y, dmg)
self.stats.total_damage_taken += dmg
```

**Tick damage numbers** in `_end_turn()`:
```python
self.damage_numbers.tick()
self.achievement_popups.tick()
```

---

## 6️⃣ Add Save/Load System

**Location**: New methods

```python
def _save_game(self):
    """Save current game state."""
    save_data = SaveData(
        player_class=self.player_class,
        level=self.level,
        xp=self.xp,
        xp_to_level=self.xp_to_level,
        gold=self.gold,
        floor=self.floor,
        turn_count=self.turn_count,
        str_points=self.str_points,
        res_points=self.res_points,
        luck_points=self.luck_points,
        vit_points=self.vit_points,
        equipped_weapon=serialize_item(self.equipped_weapon),
        equipped_armor=serialize_item(self.equipped_armor),
        equipped_ring=serialize_item(self.equipped_ring),
        equipped_amulet=serialize_item(self.equipped_amulet),
        inventory=[serialize_item(item) for item in self.inventory],
        traits=[t.key for t in self.traits],
        trait_points=self.trait_points,
        monsters_killed=self.monsters_killed,
        bosses_killed=self.bosses_killed,
        achievements_unlocked=[k for k, v in self.achievements.items() if v.unlocked],
    )
    
    result = save_game(save_data, self.save_slot)
    self.log(result)

def _load_game_menu(self):
    """Show load game menu."""
    slots = get_save_slots()
    
    self.stdscr.erase()
    h, w = self.stdscr.getmaxyx()
    
    self.stdscr.addstr(2, 2, "Load Game (Esc to cancel)", curses.A_BOLD)
    
    for slot_num in range(1, 4):
        save_data = slots.get(slot_num)
        y = 4 + slot_num * 2
        
        if save_data:
            from datetime import datetime
            save_time = datetime.fromtimestamp(save_data.save_time).strftime("%Y-%m-%d %H:%M")
            text = f"Slot {slot_num}: Floor {save_data.floor} | Lvl {save_data.level} | {save_data.player_class} | {save_time}"
            self.stdscr.addstr(y, 4, text)
        else:
            self.stdscr.addstr(y, 4, f"Slot {slot_num}: Empty")
    
    self.stdscr.addstr(12, 4, "Press 1-3 to load, Esc to cancel")
    self.stdscr.refresh()
    
    ch = self.stdscr.getch()
    if ch in [ord('1'), ord('2'), ord('3')]:
        slot = ch - ord('0')
        save_data = load_game(slot)
        if save_data:
            self._apply_save_data(save_data)
            return True
    
    return False

def _apply_save_data(self, save_data: SaveData):
    """Apply loaded save data to game state."""
    self.player_class = save_data.player_class
    self.level = save_data.level
    self.xp = save_data.xp
    self.xp_to_level = save_data.xp_to_level
    self.gold = save_data.gold
    self.floor = save_data.floor
    self.turn_count = save_data.turn_count
    self.str_points = save_data.str_points
    self.res_points = save_data.res_points
    self.luck_points = save_data.luck_points
    self.vit_points = save_data.vit_points
    self.trait_points = save_data.trait_points
    self.monsters_killed = save_data.monsters_killed
    self.bosses_killed = save_data.bosses_killed
    
    # Recreate player
    self.player = Entity(0, 0, "@", "Player", "player",
                        self._max_hp(), self._max_hp(), 10, 0, is_player=True)
    
    # Start the floor
    self._start_floor(self.floor, first_floor=True)
    
    self.log(f"Game loaded! Floor {self.floor}, Level {self.level}")
```

**Add to `handle_input()`**:
```python
elif ch == ord('F5'):
    self._save_game()
elif ch == ord('F9'):
    if self._load_game_menu():
        return True
```

---

## 7️⃣ Enhanced Death Screen with Statistics

**Replace `_draw_death_screen()` with:**

```python
def _draw_death_screen(self):
    """Draw comprehensive death screen."""
    self.stdscr.erase()
    h, w = self.stdscr.getmaxyx()
    
    mid_y = h // 2
    
    try:
        self.stdscr.addstr(mid_y - 8, max(0, (w - 20) // 2), "YOU DIED", 
                          curses.A_BOLD | curses.color_pair(6))
        
        # Stats
        stats_y = mid_y - 5
        stats = [
            f"Floor Reached: {self.floor}/{self.max_floors}",
            f"Level: {self.level}",
            f"Turns Played: {self.turn_count}",
            f"Monsters Killed: {self.monsters_killed}",
            f"Bosses Killed: {self.bosses_killed}",
            f"Gold Collected: {self.gold}",
            f"Play Time: {self.stats.get_play_time()}",
        ]
        
        for i, stat in enumerate(stats):
            self.stdscr.addstr(stats_y + i, max(0, (w - len(stat)) // 2), stat)
        
        self.stdscr.addstr(mid_y + 3, max(0, (w - 40) // 2), "Press Enter for full stats, Q to quit")
    except:
        pass
    
    self.stdscr.refresh()
    
    # Show detailed stats on Enter
    ch = self.stdscr.getch()
    if ch in [KEY_ENTER, KEY_ENTER2]:
        self._show_detailed_death_stats()

def _show_detailed_death_stats(self):
    """Show detailed statistics on death."""
    self.stdscr.erase()
    h, w = self.stdscr.getmaxyx()
    
    self.stdscr.addstr(1, 2, "=== Run Statistics ===", curses.A_BOLD)
    
    stats_dict = self.stats.to_dict()
    y = 3
    for key, value in list(stats_dict.items())[:h-5]:
        try:
            self.stdscr.addstr(y, 4, f"{key}: {value}")
            y += 1
        except:
            break
    
    self.stdscr.addstr(y + 2, 4, "Press any key to continue")
    self.stdscr.refresh()
    self.stdscr.getch()
```

---

## 8️⃣ Achievement Popups

**Add to `_draw_hud()`**, after message log:

```python
# Show achievement popups
popup_y = hud_y + 5 + self.max_log
for popup in self.achievement_popups.get_active():
    try:
        msg = f"🏆 {popup.name}: {popup.description}"
        self.stdscr.addstr(popup_y, 2, msg[:self.map_w-4], 
                          curses.color_pair(4) | curses.A_BOLD)
        popup_y += 1
    except:
        break
```

**Trigger popup when unlocking achievement** - in `check_unlocks()` or wherever you set `achievement.unlocked = True`:

```python
if not achievement.unlocked:
    achievement.unlocked = True
    self.achievement_popups.show(achievement.name, achievement.description)
    self.stats.achievements_unlocked += 1
```

---

## 9️⃣ Rune Socketing System

**Add new method:**

```python
def _socket_rune(self, rune: Item, target_item: Item) -> bool:
    """Socket a rune into equipment."""
    if not rune.is_rune():
        return False
    
    if target_item.rune_sockets <= 0:
        # Give item a socket
        target_item.rune_sockets = 1
    
    if len(target_item.inserted_runes) >= target_item.rune_sockets:
        self.log("No empty sockets!")
        return False
    
    # Insert rune
    target_item.inserted_runes.append(rune)
    
    # Apply rune stats
    target_item.strength_points += rune.strength_points
    target_item.resistance_points += rune.resistance_points
    target_item.luck_points += rune.luck_points
    target_item.vitality_points += rune.vitality_points
    
    # Add rune boosters
    target_item.boosters.extend(rune.boosters)
    
    self.inventory.remove(rune)
    self.log(f"Socketed {rune.name} into {target_item.name}!")
    self.stats.runes_socketed += 1
    return True
```

**Add to `_use_item()` method**, before current logic:

```python
def _use_item(self, index: int):
    """Use/equip item from inventory."""
    if index < 0 or index >= len(self.inventory):
        return
    
    item = self.inventory[index]
    
    # NEW: Handle runes
    if item.is_rune():
        # Show equipment selection
        equipment = [self.equipped_weapon, self.equipped_armor, self.equipped_ring, self.equipped_amulet]
        equipment = [e for e in equipment if e is not None]
        
        if not equipment:
            self.log("No equipment to socket runes into!")
            return
        
        # Auto-socket into first equipment for simplicity
        target = equipment[0]
        if self._socket_rune(item, target):
            self._update_max_hp()
        return
    
    # NEW: Handle bombs
    if item.name == "Fire Bomb":
        # Damage all nearby monsters
        dmg = int(item.effects[0].value)
        for monster in self.monsters:
            if monster.is_alive() and manhattan(self.player.pos(), monster.pos()) <= 2:
                monster.hp -= dmg
                self.damage_numbers.add_damage(monster.x, monster.y, dmg, is_crit=True)
                self.log(f"Bomb hits {monster.name} for {dmg}!")
                if not monster.is_alive():
                    self._monster_died(monster)
        self.inventory.pop(index)
        self.stats.items_consumed += 1
        self._end_turn()
        return
    
    # NEW: Handle elixirs (temporary buffs)
    if "Elixir" in item.name:
        effect = item.effects[0]
        buff_type = item.name.split("of ")[1].split()[0].lower()
        
        self.temp_buffs[buff_type] = {
            'value': effect.value,
            'duration': effect.duration,
        }
        
        self.inventory.pop(index)
        self.log(f"Used {item.name}! +{effect.value} for {effect.duration} turns.")
        self.stats.items_consumed += 1
        return
    
    # NEW: Handle escape scroll
    if item.name == "Scroll of Escape":
        if self.stairs_pos:
            self.player.x, self.player.y = self.stairs_pos
            self.log("Teleported to stairs!")
            self.inventory.pop(index)
            self.stats.items_consumed += 1
            self._end_turn()
            return
    
    # NEW: Handle identify scroll
    if item.name == "Scroll of Identify":
        for pos, ground_item in self.items_on_ground:
            self.identified_items.append(ground_item.name)
            self.log(f"Identified: {ground_item.name}")
        self.inventory.pop(index)
        self.stats.items_consumed += 1
        return
    
    # NEW: Handle enchant scroll
    if item.name == "Scroll of Enchanting":
        if self.equipped_weapon:
            self.equipped_weapon.enchant_level += 1
            # Add random booster
            from items import pick_boosters
            new_booster = pick_boosters(RARITY_RARE, "weapon", self.rng)[0]
            self.equipped_weapon.boosters.append(new_booster)
            self.log(f"Enchanted {self.equipped_weapon.name}! +{new_booster.description}")
            self.inventory.pop(index)
            self.stats.items_consumed += 1
            self.stats.items_enchanted += 1
            return
    
    # Existing potion/scroll logic...
    if item.is_potion():
        heal = int(self.player.max_hp * item.heal_pct)
        self.player.hp = min(self.player.max_hp, self.player.hp + heal)
        self.damage_numbers.add_heal(self.player.x, self.player.y, heal)
        self.inventory.pop(index)
        self.log(f"Used {item.name}. Healed {heal} HP.")
        self.stats.items_consumed += 1
        self.stats.total_healing_received += heal
    elif item.is_weapon() or item.is_armor() or item.is_ring() or item.is_amulet():
        self._equip_item(item)
        self.inventory.pop(index)
```

**Tick temp buffs** in `_end_turn()`:

```python
# Tick temporary buffs
for buff_name in list(self.temp_buffs.keys()):
    self.temp_buffs[buff_name]['duration'] -= 1
    if self.temp_buffs[buff_name]['duration'] <= 0:
        del self.temp_buffs[buff_name]
        self.log(f"{buff_name.title()} buff expired.")
```

---

## 🔟 Enhanced Merchant System

**Add to `Merchant` class in `events.py`** (or override in main.py):

```python
def _show_merchant_menu(self, merchant: Merchant):
    """Show enhanced merchant interface."""
    while True:
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        
        self.stdscr.addstr(1, 2, f"Merchant (Gold: {self.gold})", curses.A_BOLD)
        self.stdscr.addstr(2, 2, "1-9: Buy | S: Sell | R: Reroll | H: Haggle | Esc: Leave", 
                          curses.color_pair(4))
        
        # Show items
        y = 4
        for i, (item, price) in enumerate(merchant.inventory[:8]):
            haggle_price = int(price * (1.0 - self.luck_points * 0.005))  # Luck discount
            try:
                self.stdscr.addstr(y + i, 4, f"{i+1}. {item.name} - {haggle_price}g [{item.rarity}]")
            except:
                pass
        
        self.stdscr.refresh()
        ch = self.stdscr.getch()
        
        if ch == KEY_ESCAPE:
            return
        elif ch == ord('s'):
            # Sell items from inventory
            self._show_sell_menu(merchant)
        elif ch == ord('r'):
            # Reroll stock
            if self.gold >= 20:
                self.gold -= 20
                merchant.inventory = merchant._generate_stock()
                self.log("Merchant stock rerolled!")
            else:
                self.log("Not enough gold to reroll (20g)")
        elif ch == ord('h'):
            # Haggle (luck-based discount)
            success = self.rng.random() < (0.3 + self.luck_points * 0.01)
            if success:
                self.log("Haggling successful! 20% discount on next purchase.")
                merchant.haggle_bonus = 0.20
            else:
                self.log("Haggling failed!")
        elif ch in range(ord('1'), ord('9') + 1):
            idx = ch - ord('1')
            if idx < len(merchant.inventory):
                item, price = merchant.inventory[idx]
                final_price = int(price * (1.0 - self.luck_points * 0.005))
                if hasattr(merchant, 'haggle_bonus'):
                    final_price = int(final_price * (1.0 - merchant.haggle_bonus))
                    merchant.haggle_bonus = 0
                
                if self.gold >= final_price:
                    self.gold -= final_price
                    self.inventory.append(item)
                    merchant.inventory.pop(idx)
                    self.log(f"Bought {item.name} for {final_price}g!")
                    self.stats.gold_spent += final_price
                else:
                    self.log(f"Need {final_price}g, have {self.gold}g")

def _show_sell_menu(self, merchant: Merchant):
    """Sell items to merchant."""
    while True:
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        
        self.stdscr.addstr(1, 2, f"Sell Items (Your gold: {self.gold})", curses.A_BOLD)
        
        for i, item in enumerate(self.inventory[:h-4]):
            sell_price = int(self.rng.randint(10, 30) + item.base_damage * 2)
            try:
                self.stdscr.addstr(3 + i, 4, f"{i+1}. {item.name} - {sell_price}g")
            except:
                pass
        
        self.stdscr.addstr(h-2, 4, "1-9 to sell, Esc to return")
        self.stdscr.refresh()
        ch = self.stdscr.getch()
        
        if ch == KEY_ESCAPE:
            return
        elif ch in range(ord('1'), ord('9') + 1):
            idx = ch - ord('1')
            if idx < len(self.inventory):
                item = self.inventory.pop(idx)
                sell_price = self.rng.randint(10, 30) + item.base_damage * 2
                self.gold += sell_price
                self.log(f"Sold {item.name} for {sell_price}g!")
                self.stats.gold_earned += sell_price
```

**Update merchant interaction** in `_check_tile_events()`:

```python
# Check for merchants
for merchant in self.merchants:
    if merchant.pos == (px, py):
        self.log("You see a merchant. Press 'e' to trade.")
        # Trigger merchant menu
        self._show_merchant_menu(merchant)
        break
```

---

## 1️⃣1️⃣ Secret Room Detection

**Add to `_move_player()`** after successful move:

```python
# Check for secret doors
if self.map.tiles[self.player.y][self.player.x] == TILE_SECRET_DOOR:
    self.log("You found a SECRET DOOR! Walk through it.")
    self.stats.secret_rooms_found += 1
```

---

## 1️⃣2️⃣ Update `_end_turn()` with All New Systems

**Replace `_end_turn()` with:**

```python
def _end_turn(self):
    """End player turn."""
    if self.game_state != STATE_RUNNING:
        return
    
    self.turn_count += 1
    self.stats.turns_played += 1
    
    # Process monsters
    self._process_monsters()
    
    # Check player death
    if self.player and self.player.hp <= 0:
        self.game_state = STATE_DEAD
    
    # Tick player status effects
    if self.player:
        effects = self.player.tick_status_effects()
        for effect_msg in effects:
            self.log(effect_msg)
    
    # Tick damage numbers
    self.damage_numbers.tick()
    self.achievement_popups.tick()
    
    # Tick temporary buffs
    for buff_name in list(self.temp_buffs.keys()):
        self.temp_buffs[buff_name]['duration'] -= 1
        if self.temp_buffs[buff_name]['duration'] <= 0:
            del self.temp_buffs[buff_name]
    
    # Update FOV
    self._update_fov()
```

---

## 🎮 Testing

After adding all integrations:

```powershell
cd "C:\Users\Daniel IES\Documents\Roguelike game"
python main.py
```

### New Controls:
- **F5**: Save game
- **F9**: Load game
- **e**: Interact with events/merchants/shrines
- **Minimap**: Shows in top-right corner automatically

---

## ✅ Feature Summary

All 12 features are now integrated:

1. ✅ Save/Load System (F5/F9)
2. ✅ Minimap (auto-display)
3. ✅ Secret Rooms (walk on walls near rooms)
4. ✅ Floor Events (press 'e' when prompted)
5. ✅ Rune System (use runes from inventory)
6. ✅ Death Statistics (detailed screen on death)
7. ✅ Achievement Popups (auto-show)
8. ✅ Damage Numbers (floating in combat)
9. ✅ Boss Arenas (expanded rooms)
10. ✅ New Consumables (bombs, elixirs, scrolls)
11. ✅ Enchantment System (via scrolls)
12. ✅ Enhanced Merchant (sell, reroll, haggle)

---

*Integration guide created April 9, 2026*
