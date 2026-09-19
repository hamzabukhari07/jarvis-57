# JARVIS — Action System

All actions self-describe via module-level TOOL dict.

## Discovery
Scans actions/ directory at startup. Files starting with _ skipped. Validates TOOL dict, name, description, parameters, handler.

## Dispatch
From main.py _execute_tool(): inline tools -> action registry -> plugin registry.

## Built-in Actions
web_search, screen_processor, background_monitor, proactive, system_monitor, computer_settings, browser_control, file_controller, file_processor, send_message, weather_report, flight_finder, youtube_video, game_updater, code_helper, dev_agent, desktop.

## Action Registration
Actions register undo capability via core.undo.push_undo().