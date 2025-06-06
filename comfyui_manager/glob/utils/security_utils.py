from comfyui_manager.glob import manager_core as core


def is_allowed_security_level(level):
    if level == "block":
        return False
    elif level == "high":
        if is_local_mode:
            return core.get_config()["security_level"] in ["weak", "normal-"]
        else:
            return core.get_config()["security_level"] == "weak"
    elif level == "middle":
        return core.get_config()["security_level"] in ["weak", "normal", "normal-"]
    else:
        return True


async def get_risky_level(files, pip_packages):
    json_data1 = await core.get_data_by_mode("local", "custom-node-list.json")
    json_data2 = await core.get_data_by_mode(
        "cache",
        "custom-node-list.json",
        channel_url="https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main",
    )

    all_urls = set()
    for x in json_data1["custom_nodes"] + json_data2["custom_nodes"]:
        all_urls.update(x.get("files", []))

    for x in files:
        if x not in all_urls:
            return "high"

    all_pip_packages = set()
    for x in json_data1["custom_nodes"] + json_data2["custom_nodes"]:
        all_pip_packages.update(x.get("pip", []))

    for p in pip_packages:
        if p not in all_pip_packages:
            return "block"

    return "middle"
