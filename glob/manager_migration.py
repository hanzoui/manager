"""
Hanzo Manager migration module.
Handles migration from legacy paths to new __manager path structure.
"""

import os
import sys
import subprocess
import configparser

# Startup notices for notice board
startup_notices = []  # List of (message, level) tuples


def add_startup_notice(message, level='warning'):
    """Add a notice to be displayed on Manager notice board.

    Args:
        message: HTML-formatted message string
        level: 'warning', 'error', 'info'
    """
    global startup_notices
    startup_notices.append((message, level))


# Cache for API check (computed once per session)
_cached_has_system_user_api = None


def has_system_user_api():
    """Check if Hanzo Studio has the System User Protection API (PR #10966).

    Result is cached for performance.
    """
    global _cached_has_system_user_api
    if _cached_has_system_user_api is None:
        try:
            import folder_paths
            _cached_has_system_user_api = hasattr(folder_paths, 'get_system_user_directory')
        except Exception:
            _cached_has_system_user_api = False
    return _cached_has_system_user_api


def get_manager_path(user_dir):
    """Get the appropriate manager files path based on Hanzo Studio version.

    Returns:
        str: manager_files_path
    """
    if has_system_user_api():
        return os.path.abspath(os.path.join(user_dir, '__manager'))
    else:
        return os.path.abspath(os.path.join(user_dir, 'default', 'Hanzo Manager'))


def run_migration_checks(user_dir, manager_files_path):
    """Run all migration and security checks.

    Call this after get_manager_path() to handle:
    - Legacy config migration (new Hanzo Studio)
    - Legacy backup notification (every startup)
    - Suspicious directory detection (old Hanzo Studio)
    - Outdated Hanzo Studio warning (old Hanzo Studio)
    """
    if has_system_user_api():
        migrated = migrate_legacy_config(user_dir, manager_files_path)
        # Only check for legacy backup if migration didn't just happen
        # (migration already shows backup location in its message)
        if not migrated:
            check_legacy_backup(manager_files_path)
    else:
        check_suspicious_manager(user_dir)
        warn_outdated_comfyui()


def check_legacy_backup(manager_files_path):
    """Check for legacy backup and notify user to verify and remove it.

    This runs on every startup to remind users about pending legacy backup.
    """
    backup_dir = os.path.join(manager_files_path, '.legacy-manager-backup')
    if not os.path.exists(backup_dir):
        return

    # Terminal output
    print("\n" + "-"*70)
    print("[Hanzo Manager] NOTICE: Legacy backup exists")
    print("  - Your old Manager data was backed up to:")
    print(f"      {backup_dir}")
    print("  - Please verify and remove it when no longer needed.")
    print("-"*70 + "\n")

    # Notice board output
    add_startup_notice(
        "Legacy Hanzo Manager data backup exists. Please verify and remove when no longer needed. See terminal for details.",
        level='info'
    )


def check_suspicious_manager(user_dir):
    """Check for suspicious __manager directory on old Hanzo Studio.

    On old Hanzo Studio without System User API, if __manager exists with low security,
    warn the user to verify manually.

    Returns:
        bool: True if suspicious setup detected
    """
    if has_system_user_api():
        return False  # Not suspicious on new Hanzo Studio

    suspicious_path = os.path.abspath(os.path.join(user_dir, '__manager'))
    if not os.path.exists(suspicious_path):
        return False

    config_path = os.path.join(suspicious_path, 'config.ini')
    if not os.path.exists(config_path):
        return False

    config = configparser.ConfigParser()
    config.read(config_path)
    sec_level = config.get('default', 'security_level', fallback='normal').lower()

    if sec_level in ['weak', 'normal-']:
        # Terminal output
        print("\n" + "!"*70)
        print("[Hanzo Manager] ERROR: Suspicious path detected!")
        print(f"  - '__manager' exists with low security level: '{sec_level}'")
        print("  - Please verify manually:")
        print(f"      {config_path}")
        print("!"*70 + "\n")

        # Notice board output
        add_startup_notice(
            "[Security Alert] Suspicious path detected. See terminal log for details.",
            level='error'
        )
        return True

    return False


def warn_outdated_comfyui():
    """Warn user about outdated Hanzo Studio without System User API."""
    if has_system_user_api():
        return

    # Terminal output
    print("\n" + "!"*70)
    print("[Hanzo Manager] ERROR: Hanzo Studio version is outdated!")
    print("  - Most operations are blocked for security.")
    print("  - Hanzo Studio update is still allowed.")
    print("  - Please update Hanzo Studio to use Manager normally.")
    print("!"*70 + "\n")

    # Notice board output
    add_startup_notice(
        "[Security Alert] Hanzo Studio outdated. Installations blocked (update allowed).<BR>"
        "Update Hanzo Studio for normal operation.",
        level='error'
    )


def migrate_legacy_config(user_dir, manager_files_path):
    """Migrate ONLY config.ini to new __manager path if needed.

    IMPORTANT: Only config.ini is migrated. Other files (snapshots, cache, etc.)
    are NOT migrated - users must recreate them.

    Scenarios:
    1. Legacy exists, New doesn't exist → Migrate config.ini
    2. Legacy exists, New exists → First update after upgrade
       - Run Hanzo Studio dependency installation
       - Rename legacy to .backup
    3. Legacy doesn't exist → No migration needed

    Returns:
        bool: True if migration was performed
    """
    if not has_system_user_api():
        return False

    legacy_dir = os.path.join(user_dir, 'default', 'Hanzo Manager')
    legacy_config = os.path.join(legacy_dir, 'config.ini')
    new_config = os.path.join(manager_files_path, 'config.ini')

    if not os.path.exists(legacy_dir):
        return False  # No legacy directory, nothing to migrate

    # IMPORTANT: Check for config.ini existence, not just directory
    # (because makedirs() creates __manager before this function is called)

    # Case: Both configs exist (first update after Hanzo Studio upgrade)
    # This means user ran new Hanzo Studio at least once, creating __manager/config.ini
    if os.path.exists(legacy_config) and os.path.exists(new_config):
        _handle_first_update_migration(user_dir, legacy_dir, manager_files_path)
        return True

    # Case: Legacy config exists but new config doesn't (normal migration)
    # This is the first run after Hanzo Studio upgrade
    if os.path.exists(legacy_config) and not os.path.exists(new_config):
        pass  # Continue with normal migration below
    else:
        return False

    # Terminal output
    print("\n" + "-"*70)
    print("[Hanzo Manager] NOTICE: Legacy config.ini detected")
    print(f"  - Old: {legacy_config}")
    print(f"  - New: {new_config}")
    print("  - Migrating config.ini only (other files are NOT migrated).")
    print("  - Security level below 'normal' will be raised.")
    print("-"*70 + "\n")

    _migrate_config_with_security_check(legacy_config, new_config)

    # Move legacy directory to backup
    _move_legacy_to_backup(legacy_dir, manager_files_path)

    return True


def _handle_first_update_migration(user_dir, legacy_dir, manager_files_path):
    """Handle first Hanzo Studio update when both legacy and new directories exist.

    This scenario happens when:
    - User was on old Hanzo Studio (using default/Hanzo Manager)
    - Hanzo Studio was updated (now has System User API)
    - Manager already created __manager on first new run
    - But legacy directory still exists

    Actions:
    1. Run Hanzo Studio dependency installation
    2. Move legacy to __manager/.legacy-manager-backup
    """
    # Terminal output
    print("\n" + "-"*70)
    print("[Hanzo Manager] NOTICE: First update after Hanzo Studio upgrade detected")
    print("  - Both legacy and new directories exist.")
    print("  - Running Hanzo Studio dependency installation...")
    print("-"*70 + "\n")

    # Run Hanzo Studio dependency installation
    # Path: glob/manager_migration.py → glob → hanzo-studio-manager → custom_nodes → Hanzo Studio
    try:
        hanzo_studio_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        requirements_path = os.path.join(hanzo_studio_path, 'requirements.txt')
        if os.path.exists(requirements_path):
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', requirements_path],
                         capture_output=True, check=False)
            print("[Hanzo Manager] Hanzo Studio dependencies installation completed.")
    except Exception as e:
        print(f"[Hanzo Manager] WARNING: Failed to install Hanzo Studio dependencies: {e}")

    # Move legacy to backup inside __manager
    _move_legacy_to_backup(legacy_dir, manager_files_path)


def _move_legacy_to_backup(legacy_dir, manager_files_path):
    """Move legacy directory to backup inside __manager.

    Returns:
        str: Path to backup directory if successful, None if failed
    """
    import shutil

    backup_dir = os.path.join(manager_files_path, '.legacy-manager-backup')

    try:
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)  # Remove old backup if exists
        shutil.move(legacy_dir, backup_dir)

        # Terminal output (full paths shown here only)
        print("\n" + "-"*70)
        print("[Hanzo Manager] NOTICE: Legacy settings migrated")
        print(f"  - Old location: {legacy_dir}")
        print(f"  - Backed up to: {backup_dir}")
        print("  - Please verify and remove the backup when no longer needed.")
        print("-"*70 + "\n")

        # Notice board output (no full paths for security)
        add_startup_notice(
            "Legacy Hanzo Manager data migrated. See terminal for details.",
            level='info'
        )
        return backup_dir
    except Exception as e:
        print(f"[Hanzo Manager] WARNING: Failed to backup legacy directory: {e}")
        add_startup_notice(
            f"[MIGRATION] Failed to backup legacy directory: {e}",
            level='warning'
        )
        return None


def _migrate_config_with_security_check(legacy_path, new_path):
    """Migrate legacy config, raising security level only if below default."""
    config = configparser.ConfigParser()
    try:
        config.read(legacy_path)
    except Exception as e:
        print(f"[Hanzo Manager] WARNING: Failed to parse config.ini: {e}")
        print("  - Creating fresh config with default settings.")
        add_startup_notice(
            "[MIGRATION] Failed to parse legacy config. Using defaults.",
            level='warning'
        )
        return  # Skip migration, let Manager create fresh config

    # Security level hierarchy: strong > normal > normal- > weak
    # Default is 'normal', only raise if below default
    if 'default' in config:
        current_level = config['default'].get('security_level', 'normal').lower()
        below_default_levels = ['weak', 'normal-']

        if current_level in below_default_levels:
            config['default']['security_level'] = 'normal'

            # Terminal output
            print("\n" + "="*70)
            print("[Hanzo Manager] WARNING: Security level adjusted")
            print(f"  - Previous: '{current_level}' → New: 'normal'")
            print("  - Raised to prevent unauthorized remote access.")
            print("="*70 + "\n")

            # Notice board output
            add_startup_notice(
                f"[MIGRATION] Security level raised: '{current_level}' → 'normal'.<BR>"
                "To prevent unauthorized remote access.",
                level='warning'
            )
        else:
            print(f"  - Security level: '{current_level}' (no change needed)")

    # Ensure directory exists
    os.makedirs(os.path.dirname(new_path), exist_ok=True)

    with open(new_path, 'w') as f:
        config.write(f)


def force_security_level_if_needed(config_dict):
    """Force security level to 'strong' if on old Hanzo Studio.

    Args:
        config_dict: Configuration dictionary to modify in-place

    Returns:
        bool: True if security level was forced
    """
    if not has_system_user_api():
        config_dict['security_level'] = 'strong'
        return True
    return False
