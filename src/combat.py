"""Combat system with elements, status effects, and boss AI."""
import random
from typing import Dict, List, Optional, Tuple
from constants import *
from utils import Vec2, manhattan, chebyshev, circle_points
from entities import Entity, StatusEffect, PhaseAbility, MonsterTemplate
from items import Item


# Elemental effectiveness matrix
ELEMENTAL_EFFECTIVENESS = {
    ELEM_FIRE: {ELEM_ICE: 1.5, ELEM_PHYSICAL: 1.0, ELEM_FIRE: 0.75},
    ELEM_ICE: {ELEM_FIRE: 1.5, ELEM_PHYSICAL: 1.0, ELEM_ICE: 0.75},
    ELEM_LIGHTNING: {ELEM_PHYSICAL: 1.2, ELEM_ICE: 1.5, ELEM_LIGHTNING: 0.75},
    ELEM_POISON: {ELEM_PHYSICAL: 1.1, ELEM_POISON: 0.5},
    ELEM_DARK: {ELEM_HOLY: 0.75, ELEM_DARK: 0.5, ELEM_PHYSICAL: 1.0},
    ELEM_HOLY: {ELEM_DARK: 1.5, ELEM_PHYSICAL: 1.0, ELEM_HOLY: 0.75},
    ELEM_VOID: {ELEM_PHYSICAL: 1.3, ELEM_VOID: 0.5},
    ELEM_PHYSICAL: {ELEM_PHYSICAL: 1.0},
}


class CombatSystem:
    """Handles all combat calculations."""
    
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.combat_log: List[str] = []
    
    def log(self, msg: str) -> None:
        self.combat_log.append(msg)
    
    def calculate_damage(self, attacker: Entity, defender: Entity, 
                        weapon: Optional[Item] = None,
                        forced_crit: bool = False,
                        is_player: bool = False) -> Tuple[int, bool, str]:
        """
        Calculate damage dealt.
        Returns: (damage, is_crit, element_used)
        """
        # Base damage
        if weapon:
            base_dmg = weapon.base_damage
            element = weapon.element
        else:
            base_dmg = attacker.base_damage
            element = attacker.element
        
        # Apply strength multiplier
        str_mult = 1.0
        if is_player:
            # Strength points give +0.5% each
            str_mult = 1.0 + (attacker.base_damage * 0.005)  # Placeholder
        
        damage = base_dmg * str_mult
        
        # Critical hit
        is_crit = forced_crit
        if not is_crit and is_player:
            crit_chance = 0.05  # Base 5%
            # Add luck-based crit
            # This will be called with proper player stats
            is_crit = self.rng.random() < crit_chance
        
        if is_crit:
            crit_mult = 1.5
            damage *= crit_mult
        
        # Elemental damage
        element_bonus = 0
        if element != ELEM_PHYSICAL:
            # Check defender's resistance
            effectiveness = self.get_elemental_effectiveness(element, defender)
            element_bonus = int(base_dmg * 0.3 * effectiveness)
        
        damage += element_bonus
        
        # Apply defender's resistance
        res_reduction = 0.0
        if not is_player:
            # Monster attacking player - apply player resistance
            pass  # Handled by caller
        else:
            # Player attacking monster
            res_reduction = defender.base_armor * 0.01  # 1% per armor point
        
        # Apply resistance boosters from equipment
        damage = damage * (1.0 - res_reduction)
        
        # Ensure minimum damage
        damage = max(1, int(round(damage)))
        
        element_desc = ELEMENT_NAMES.get(element, "Physical")
        if is_crit:
            element_desc = f"CRITICAL {element_desc}"
        
        return (damage, is_crit, element_desc)
    
    def get_elemental_effectiveness(self, element: str, defender: Entity) -> float:
        """Get elemental effectiveness against a defender."""
        # Default effectiveness
        if element in ELEMENTAL_EFFECTIVENESS:
            # Check if defender has specific resistance
            if defender.element in ELEMENTAL_EFFECTIVENESS[element]:
                return ELEMENTAL_EFFECTIVENESS[element][defender.element]
        return 1.0
    
    def apply_status_effect(self, target: Entity, effect_name: str, 
                           duration: int, value: float = 0.0) -> None:
        """Apply a status effect to a target."""
        effect = StatusEffect(
            name=effect_name,
            duration=duration,
            value=value,
            description=f"Affected by {effect_name}"
        )
        target.add_status_effect(effect)
    
    def process_status_effects(self, entity: Entity) -> List[str]:
        """Process all status effects on an entity. Returns messages."""
        messages = entity.tick_status_effects()
        
        # Check for stun
        if entity.has_status_effect(STATUS_STUNNED):
            messages.append(f"{entity.name} is stunned and can't act!")
        
        return messages


class BossAI:
    """Handles boss special abilities and phase transitions."""
    
    def __init__(self, boss: Entity, template: MonsterTemplate, rng: random.Random):
        self.boss = boss
        self.template = template
        self.rng = rng
        self.current_phase = 1
    
    def check_phase_transition(self) -> Optional[str]:
        """Check if boss should transition to a new phase."""
        if not self.template.phase_thresholds:
            return None
        
        hp_pct = self.boss.hp / max(1, self.boss.max_hp)
        thresholds = self.template.phase_thresholds
        
        # Calculate which phase we should be in
        new_phase = 1
        for i, threshold in enumerate(thresholds):
            if hp_pct <= threshold:
                new_phase = i + 2  # Phase 1 is base, then 2, 3, etc.
        
        if new_phase > self.current_phase:
            old_phase = self.current_phase
            self.current_phase = new_phase
            self.boss.phase = new_phase
            
            # Phase transition effects
            if new_phase == 2:
                self.boss.base_damage = int(self.boss.base_damage * 1.15)
            elif new_phase == 3:
                self.boss.base_damage = int(self.boss.base_damage * 1.20)
            elif new_phase >= 4:
                self.boss.base_damage = int(self.boss.base_damage * 1.25)
            
            return f"{self.boss.name} enters Phase {new_phase}!"
        
        return None
    
    def execute_special_ability(self, player: Entity, game_state) -> bool:
        """
        Execute a special ability. Returns True if ability was used.
        game_state should provide access to dungeon map and other entities.
        """
        # Check cooldowns
        for ability in self.boss.abilities:
            if ability.current_cd > 0:
                ability.current_cd -= 1
                continue
            
            # Check if ability is available for current phase
            if ability.min_phase > self.current_phase:
                continue
            
            # Roll for ability use
            if self.rng.random() < ability.chance:
                return self._use_ability(ability, player, game_state)
        
        return False
    
    def _use_ability(self, ability: PhaseAbility, player: Entity, game_state) -> bool:
        """Execute a specific ability."""
        ability_name = ability.name.lower()
        
        if "shockwave" in ability_name or "stomp" in ability_name:
            return self._ability_shockwave(player, game_state)
        elif "charge" in ability_name:
            return self._ability_charge(player, game_state)
        elif "summon" in ability_name:
            return self._ability_summon(ability, game_state)
        elif "fire" in ability_name or "inferno" in ability_name or "breath" in ability_name:
            return self._ability_fire(player, game_state)
        elif "ice" in ability_name or "freeze" in ability_name or "blizzard" in ability_name:
            return self._ability_ice(player, game_state)
        elif "void" in ability_name or "reality" in ability_name:
            return self._ability_void(player, game_state)
        elif "drain" in ability_name or "siphon" in ability_name:
            return self._ability_drain(player, game_state)
        elif "teleport" in ability_name or "phase" in ability_name or "step" in ability_name:
            return self._ability_teleport(player, game_state)
        elif "multi" in ability_name or "double" in ability_name:
            return self._ability_multi_attack(player, game_state)
        elif "annihilation" in ability_name or "oblivion" in ability_name or "collapse" in ability_name:
            return self._ability_ultimate(player, game_state)
        elif "web" in ability_name or "root" in ability_name:
            return self._ability_cc(player, game_state, STATUS_STUNNED)
        elif "poison" in ability_name:
            return self._ability_cc(player, game_state, STATUS_POISONED)
        else:
            # Generic heavy attack
            return self._ability_heavy_attack(player, game_state)
    
    def _ability_shockwave(self, player: Entity, game_state) -> bool:
        """AoE damage around boss."""
        dmg = int(self.boss.base_damage * 1.2)
        dist = chebyshev(self.boss.pos(), player.pos())
        
        if dist <= 2:
            self._deal_damage_to_player(player, dmg, "shockwave")
            self.boss.special_cd = 2
            return True
        
        self.boss.special_cd = 2
        return False
    
    def _ability_charge(self, player: Entity, game_state) -> bool:
        """Charge toward player."""
        # Simplified: if adjacent after charge, attack
        dx = 1 if player.x > self.boss.x else (-1 if player.x < self.boss.x else 0)
        dy = 1 if player.y > self.boss.y else (-1 if player.y < self.boss.y else 0)
        
        # Move 2 tiles toward player
        for _ in range(2):
            nx, ny = self.boss.x + dx, self.boss.y + dy
            if game_state['map'].is_walkable(nx, ny):
                # Check not on player
                if not (nx == player.x and ny == player.y):
                    self.boss.x, self.boss.y = nx, ny
        
        # Attack if adjacent
        if chebyshev(self.boss.pos(), player.pos()) <= 1:
            self._melee_attack(player, game_state)
        
        self.boss.special_cd = 3
        return True
    
    def _ability_summon(self, ability: PhaseAbility, game_state) -> bool:
        """Summon minions."""
        # This requires game_state to have spawn functionality
        if 'spawn_minion' in game_state:
            count = 2
            minion_template = self._get_minion_template()
            for _ in range(count):
                game_state['spawn_minion'](minion_template, self.boss.pos())
        
        self.boss.special_cd = 4
        return True
    
    def _ability_fire(self, player: Entity, game_state) -> bool:
        """Fire-based AoE."""
        dmg = int(self.boss.base_damage * 1.3)
        dist = chebyshev(self.boss.pos(), player.pos())
        
        if dist <= 3:
            self._deal_damage_to_player(player, dmg, "fire storm")
            # Apply burning
            game_state['combat'].apply_status_effect(player, STATUS_BURNING, 3, 3)
        
        self.boss.special_cd = 3
        return True
    
    def _ability_ice(self, player: Entity, game_state) -> bool:
        """Ice-based attack."""
        dmg = int(self.boss.base_damage * 1.2)
        self._deal_damage_to_player(player, dmg, "ice attack")
        
        # Chance to freeze
        if self.rng.random() < 0.3:
            game_state['combat'].apply_status_effect(player, STATUS_FROZEN, 2)
        
        self.boss.special_cd = 3
        return True
    
    def _ability_void(self, player: Entity, game_state) -> bool:
        """Void damage."""
        dmg = int(self.boss.base_damage * 1.4)
        self._deal_damage_to_player(player, dmg, "void energy")
        self.boss.special_cd = 3
        return True
    
    def _ability_drain(self, player: Entity, game_state) -> bool:
        """Drain player HP."""
        drain_amount = int(player.hp * 0.15)
        player.hp -= drain_amount
        self.boss.hp = min(self.boss.max_hp, self.boss.hp + drain_amount)
        
        self.log(f"{self.boss.name} drains {drain_amount} HP from you!")
        self.boss.special_cd = 3
        return True
    
    def _ability_teleport(self, player: Entity, game_state) -> bool:
        """Teleport near player."""
        px, py = player.pos()
        candidates = []
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = px + dx, py + dy
                if game_state['map'].is_walkable(nx, ny):
                    candidates.append((nx, ny))
        
        if candidates:
            self.boss.x, self.boss.y = self.rng.choice(candidates)
            # Follow up with attack
            if chebyshev(self.boss.pos(), player.pos()) <= 1:
                self._melee_attack(player, game_state)
        
        self.boss.special_cd = 3
        return True
    
    def _ability_multi_attack(self, player: Entity, game_state) -> bool:
        """Multiple attacks."""
        for _ in range(2):
            if player.hp > 0:
                self._melee_attack(player, game_state)
        
        self.boss.special_cd = 4
        return True
    
    def _ability_ultimate(self, player: Entity, game_state) -> bool:
        """Ultimate ability - massive damage."""
        dmg = int(self.boss.base_damage * 2.0)
        self._deal_damage_to_player(player, dmg, "ULTIMATE ATTACK")
        self.boss.special_cd = 8
        return True
    
    def _ability_cc(self, player: Entity, game_state, effect: str) -> bool:
        """Crowd control ability."""
        dmg = int(self.boss.base_damage * 1.1)
        self._deal_damage_to_player(player, dmg, effect)
        
        duration = 3 if effect == STATUS_POISONED else 2
        game_state['combat'].apply_status_effect(player, effect, duration, 5)
        
        self.boss.special_cd = 3
        return True
    
    def _ability_heavy_attack(self, player: Entity, game_state) -> bool:
        """Generic heavy attack."""
        dmg = int(self.boss.base_damage * 1.5)
        self._deal_damage_to_player(player, dmg, "heavy attack")
        self.boss.special_cd = 2
        return True
    
    def _melee_attack(self, player: Entity, game_state) -> None:
        """Standard melee attack."""
        dmg = max(1, self.boss.base_damage)
        self._deal_damage_to_player(player, dmg, "melee")
    
    def _deal_damage_to_player(self, player: Entity, damage: int, attack_type: str) -> None:
        """Apply damage to player with resistance calculation."""
        # Get resistance from game_state
        final_damage = max(1, damage)  # Simplified
        player.hp -= final_damage
        self.log(f"{self.boss.name} uses {attack_type} for {final_damage} damage!")
    
    def _get_minion_template(self) -> MonsterTemplate:
        """Get template for summoned minions."""
        return MonsterTemplate(
            key="minion",
            name=f"{self.boss.name} Minion",
            symbol="m",
            max_hp=max(10, self.boss.max_hp // 10),
            base_damage=max(5, self.boss.base_damage // 4),
            xp_given=max(5, self.boss.xp_given // 10),
        )
    
    def log(self, msg: str) -> None:
        if 'log' in dir(self):
            pass  # Will be set by game


class MonsterAI:
    """Basic monster AI."""
    
    def __init__(self, rng: random.Random):
        self.rng = rng
    
    def decide_action(self, monster: Entity, player: Entity, game_state) -> str:
        """
        Decide monster action.
        Returns: "move", "attack", "wait", or ability name
        """
        dist = manhattan(monster.pos(), player.pos())
        can_see = dist <= monster.aggro_range
        
        # Behavior modifiers
        if monster.behavior == "cowardly" and monster.hp < monster.max_hp * 0.3:
            # Run away
            return "flee"
        elif monster.behavior == "ambush" and not can_see:
            # Stay still until player is close
            if dist <= 2:
                return "attack"
            return "wait"
        
        if can_see:
            if dist == 1 or (monster.is_boss and dist <= 2):
                return "attack"
            else:
                return "move"
        else:
            # Wander
            return "wander"
