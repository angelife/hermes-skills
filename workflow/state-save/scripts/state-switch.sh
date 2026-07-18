#!/bin/bash
# state-switch.sh — switch active project state
# Location: ~/.hermes/skills/workflow/state-save/scripts/state-switch.sh
# Usage: bash /path/to/state-switch.sh <project-name>
#
# Switches the active Working State project:
#   1. Saves current project.yaml → projects/<current-name>.yaml (backup)
#   2. Copies target project snapshot → project.yaml
#   3. Resets task.yaml for new project context
#   4. Appends ProjectSwitch event to events.log
#
# Project snapshots stored under ~/.hermes/state/projects/<name>.yaml
# global.yaml is NEVER modified by this script.

set -e

STATE_DIR="$HOME/.hermes/state"
PROJECTS_DIR="$STATE_DIR/projects"
PROJECT_FILE="$STATE_DIR/project.yaml"
TASK_FILE="$STATE_DIR/task.yaml"
EVENTS_FILE="$STATE_DIR/events.log"

name="$1"

if [ -z "$name" ]; then
    echo "Usage: state-switch <project-name>"
    echo ""
    echo "Available projects:"
    ls "$PROJECTS_DIR"/*.yaml 2>/dev/null | sed 's|.*/||; s|\.yaml$||'
    exit 1
fi

src="$PROJECTS_DIR/$name.yaml"

if [ ! -f "$src" ]; then
    echo "Error: project '$name' not found in $PROJECTS_DIR"
    echo "Available:"
    ls "$PROJECTS_DIR"/*.yaml 2>/dev/null | sed 's|.*/||; s|\.yaml$||'
    exit 1
fi

# Save current project as backup
backup_name=""
if [ -f "$PROJECT_FILE" ]; then
    raw_name=$(grep '^project:' "$PROJECT_FILE" | head -1 | sed 's/^project: *"//; s/"$//')
    if [ -n "$raw_name" ]; then
        backup_name=$(echo "$raw_name" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
        cp "$PROJECT_FILE" "$PROJECTS_DIR/${backup_name}.yaml"
        echo "Backed up current project as: $backup_name"
    fi
fi

# Switch
cp "$src" "$PROJECT_FILE"
echo "Switched to project: $name"

# Reset task for new project context
cat > "$TASK_FILE" << TASKEOF
# Task Working State
# Switched by state-switch at $(date -u +"%Y-%m-%dT%H:%M:%SZ")

schema_version: 1
updated_at: "$(date +"%Y-%m-%dT%H:%M:%S%z")"

current_task: "New session — project switched to $name"
current_blocker: null
completed_this_session: []
next_actions:
  - "Review project state and continue"
open_questions: []
TASKEOF

# Log the switch
ts=$(date +"%Y-%m-%dT%H:%M:%S%z")
from="${backup_name:-unknown}"
echo "${ts} | ProjectSwitch | ${from} → ${name}" >> "$EVENTS_FILE"

echo ""
echo "Active project: $name"
head -5 "$PROJECT_FILE"