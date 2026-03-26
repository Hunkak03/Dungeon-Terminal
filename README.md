## Terminal Roguelike (ASCII)

Run:

```powershell
pip install -r requirements.txt
python main.py
```

Controls (in-game):
- Move: arrows / `WASD`
- `I`: inventory
- `C`: equipped gear
- `K`: stats (spend level points)
- `B`: bestiary (defeated monsters)
- `U`: class special attack
- `Enter`: confirm menus / restart after death
- `Esc`: close panels
- `Q`: quit

Notes:
- This is a single-floor roguelike designed to be fast to iterate on.
- If `curses` fails on Windows, ensure you installed `windows-curses`.
- On first run, the game can auto-generate simple `.wav` sounds into `assets/audio/` if they are missing.
