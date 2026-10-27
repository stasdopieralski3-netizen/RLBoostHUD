RL BOOST HUD - Windows 11 / Epic Games Rocket League

IMPORTANT: Official Rocket League Stats API documents the Boost field as SPECTATOR ONLY.
In live ranked matches, player boost values may all show N/A. This is expected,
not a broken HUD. No values are guessed or simulated.

SETUP
1. Install Python 3.11+ from python.org (check Add Python to PATH).
2. Find Rocket League's installation directory using Epic Games Launcher.
3. In <Rocket League install>\TAGame\Config\ edit TAStatsAPI.ini (or
   DefaultStatsAPI.ini if TAStatsAPI.ini does not exist).
   Under [TAGame.MatchStatsExporter_TA], set:

   [TAGame.MatchStatsExporter_TA]
   PacketSendRate=10
   Port=49123
   WebPort=49124

   Back up the original INI first. If the section already exists, edit its
   values rather than adding duplicate sections.
4. Restart Rocket League fully AFTER saving the INI.
5. Double-click build_windows.bat to install requirements and build executable.
6. Run dist\RLBoostHUD.exe and enter a match. For the desktop HUD to remain
   visible, use Rocket League Borderless / Windowed mode.

CONTROLS
Drag the top bar to move the HUD.
Click-through ON passes mouse clicks through the overlay on Windows.
Press Ctrl+Shift+U to turn click-through OFF.
Close using the Close button (unlock first if necessary).
Ctrl+Shift+H hides the HUD while it has keyboard focus.

DATA & SAFETY
Reads only ws://127.0.0.1:49124 via Rocket League's documented Stats API.
Does not read process memory, inject DLLs, modify packets, or bypass anti-cheat.
This is not an assurance of approval by Psyonix/Epic. Verify their current rules.

Official reference: https://www.rocketleague.com/developer/stats-api
