def bypass_guild_configured_check(func: callable) -> callable:
    """Decorator to skip the config check."""
    func.__starbot_bypass_config_check__ = True
    return func
