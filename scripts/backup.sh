#!/bin/bash
BACKUP_DIR="/home/poteete/projects/automotive-diagnostic-skills/backups/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

echo "Backing up databases and credentials to $BACKUP_DIR..."

cp -r /home/poteete/projects/automotive-diagnostic-skills/database "$BACKUP_DIR/database"
cp -r /home/poteete/projects/automotive-diagnostic-skills/data/vector_store "$BACKUP_DIR/vector_store"
cp -r /home/poteete/.openclaw/credentials "$BACKUP_DIR/credentials"

echo "Backup complete!"