import re


class ProjectStructure:
    PROJECT_STATUS_VALUES = frozenset(
        {
            "Not Started",
            "Active",
            "Postponed",
            "Completed",
            "Post Launch",
            "Canceled",
        }
    )
    SCENE_NUMBER_PATTERN = re.compile(r"(?:0[1-9]|[1-9][0-9])")
    SHOT_NAME_PATTERN = re.compile(r"(?:0[1-9]|[1-9][0-9])[A-Z]?")
    PROJECT_CODE_PATTERN = re.compile(r"[A-Za-z]{2,5}")
    REQUIRED_APPROVALS = 2

    @classmethod
    def ValidateProjectCode(cls, project_code, allow_empty=True):
        if not isinstance(project_code, str):
            raise ValueError("Project code must be text")
        if project_code == "" and allow_empty:
            return project_code
        if cls.PROJECT_CODE_PATTERN.fullmatch(project_code) is None:
            raise ValueError("Project code must be 2-5 letters with no spaces")
        return project_code

    @classmethod
    def Validate(cls, structure):
        if not isinstance(structure, dict):
            raise ValueError("Project structure must be a JSON object")
        scenes = structure.get("scenes")
        characters = structure.get("characters")
        props = structure.get("props", [])
        status = structure.get("status", "Not Started")
        project_code = cls.ValidateProjectCode(
            structure.get("project_code", ""),
        )
        if (
            not isinstance(scenes, list)
            or not isinstance(characters, list)
            or not isinstance(props, list)
        ):
            raise ValueError(
                "Project scenes, characters, and props must be JSON arrays"
            )
        if not isinstance(status, str) or status not in cls.PROJECT_STATUS_VALUES:
            raise ValueError(f"Unknown project status {status!r}")

        normalized_scenes = []
        seen_scenes = set()
        for level in scenes:
            if not isinstance(level, dict):
                raise ValueError("Each project level must be a JSON object")
            name = level.get("name")
            subtitle = level.get("subtitle", "")
            shots = level.get("shots")
            settings = level.get("settings", [])
            if (
                not isinstance(name, str)
                or cls.SCENE_NUMBER_PATTERN.fullmatch(name) is None
            ):
                raise ValueError(f"Level numbers must be from 01 to 99: {name!r}")
            if not isinstance(subtitle, str):
                raise ValueError(f"Level subtitle for {name!r} must be text")
            if not isinstance(shots, list):
                raise ValueError(f"Shots for level {name!r} must be a JSON array")
            if not isinstance(settings, list):
                raise ValueError(f"Settings for level {name!r} must be a JSON array")
            if name in seen_scenes:
                raise ValueError(f"Level {name!r} is duplicated")
            seen_scenes.add(name)

            normalized_shots = []
            seen_shots = set()
            for shot in shots:
                if (
                    not isinstance(shot, str)
                    or cls.SHOT_NAME_PATTERN.fullmatch(shot) is None
                ):
                    raise ValueError(
                        f"Shot names must be XX or XXY, with XX from 01 to 99 and Y uppercase: {shot!r}"
                    )
                if shot in seen_shots:
                    raise ValueError(f"Shot {shot!r} is duplicated in level {name!r}")
                seen_shots.add(shot)
                normalized_shots.append(shot)
            normalized_scenes.append(
                {
                    "name": name,
                    "subtitle": subtitle.strip(),
                    "shots": normalized_shots,
                    "settings": cls._NormalizeNames(settings, "Setting"),
                }
            )

        normalized_characters = cls._NormalizeNames(characters, "Character")
        normalized_props = cls._NormalizeNames(props, "Prop")
        return {
            "scenes": normalized_scenes,
            "characters": normalized_characters,
            "props": normalized_props,
            "status": status,
            "project_code": project_code,
        }

    @staticmethod
    def _NormalizeNames(values, kind):
        normalized = []
        seen = set()
        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{kind} names must be non-empty strings")
            value = value.strip()
            key = value.casefold()
            if key in seen:
                raise ValueError(f"{kind} {value!r} is duplicated")
            seen.add(key)
            normalized.append(value)
        return normalized

    @classmethod
    def Normalize(
        cls,
        structure,
        default_status="Not Started",
        default_project_code="",
    ):
        if not isinstance(structure, dict):
            raise ValueError("Project structure must be a JSON object")
        scenes = structure.get("scenes", [])
        if not isinstance(scenes, list):
            raise ValueError("Project scenes must be a JSON array")

        used_numbers = {
            level.get("name")
            for level in scenes
            if isinstance(level, dict)
            and isinstance(level.get("name"), str)
            and cls.SCENE_NUMBER_PATTERN.fullmatch(level["name"])
        }
        normalized_scenes = []
        next_number = 1
        for level in scenes:
            if not isinstance(level, dict):
                raise ValueError("Each project level must be a JSON object")
            name = level.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Level names must be non-empty strings")
            if cls.SCENE_NUMBER_PATTERN.fullmatch(name):
                normalized_scenes.append(
                    {
                        "name": name,
                        "subtitle": level.get("subtitle", ""),
                        "shots": level.get("shots", []),
                        "settings": level.get("settings", []),
                    }
                )
                continue

            while f"{next_number:02}" in used_numbers:
                next_number += 1
            if next_number > 99:
                raise ValueError("A project cannot contain more than 99 scenes")
            normalized_scenes.append(
                {
                    "name": f"{next_number:02}",
                    "subtitle": level.get("subtitle") or name.strip(),
                    "shots": level.get("shots", []),
                    "settings": level.get("settings", []),
                }
            )
            used_numbers.add(f"{next_number:02}")
            next_number += 1

        return cls.Validate(
            {
                "scenes": normalized_scenes,
                "characters": structure.get("characters", []),
                "props": structure.get("props", []),
                "status": structure.get("status", default_status),
                "project_code": structure.get(
                    "project_code",
                    default_project_code,
                ),
            }
        )

    @staticmethod
    def GetApprovals(request):
        approvals = request.get("approvals", [])
        if (
            not isinstance(approvals, list)
            or any(not isinstance(approval, str) for approval in approvals)
            or len(approvals) != len(set(approvals))
        ):
            raise ValueError("Project change approvals must be unique names")
        return list(approvals)
