from typing import (
    Self
)

class CmlReader():
    def __init__(self: Self, path: str, /) -> None:
        self.path: str = path

    def read(self) -> dict:
        configs: dict = {}
        with open(self.path, "r") as file:
            lines = file.readlines()
            for line in lines:
                line = line.strip()
                if not line: continue
                if line.startswith("#"): continue
                if ">" in line:
                    identifier, open_brk = line.split(">", 1)
                    configs[identifier.strip()] = open_brk.strip()
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    configs[key.strip()] = value.strip()
                    continue
                if "]" in line:
                    continue
        return configs

    def fread(self) -> dict[str, list]:
        configs: dict[str, list] = {}
        with open(self.path, "r") as file:
            lines = file.readlines()
            for line in lines:
                line = line.strip()
                if not line: continue
                if line.startswith("#"): continue
                if ">" in line:
                    identifier, pointer, bracket = line.split(" ", 2)
                    configs[identifier.strip()] = [pointer.strip(), bracket.strip()]
                    continue
                if "=" in line:
                    key, pointer, value = line.split(" ", 2)
                    configs[key.strip()] = [pointer.strip(), value.strip()]
                    continue
                if "]" in line:
                    bracket = line.strip()
                    configs["closing_bracket"] = [bracket.strip()]
                    continue
        return configs

    def sntz(self, configs: dict[str, list]) -> dict:
        conf: dict[str, list] = {}

        for key, value in configs.items():
            if "\"" in value[1]:
                conf[key] = [value[0], value[1].strip("\"")]
            pass
        return conf
