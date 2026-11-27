from enum import Enum
from pathlib import Path
import shutil

class BlenderFileStatus(Enum):
    WIP = "wip"
    SSOT = "ssot"

class BlenderFileActions(Enum):
    CHARACTER_MODEL = "Work on a character model"
    CHARACTER_RIG = "Work on a character rig"
    PROP = "Work on a prop"
    GRAYBOX = "Graybox"
    ANIMATE_GRAYBOX = "Animate characters with graybox"
    SET_WORK = "Work on a set"
    CHARACTER_MATERIALS = "Test character materials on set"
    COMPOSITE = "Composite a shot"

SSOT_CHECKLISTS = {
    BlenderFileActions.CHARACTER_MODEL.value: {
        "Both object and data blocks are properly named" : False,
        "Faces the -Y direction" : False,
        "Has correct pivot placement" : False,
        "Transforms are applied" : False,
        "Geometry is manifold" : False,
        "Has proper edge flow" : False,
        "Mostly quads" : False,
        "Topology is even" : False,
        "No n-gons" : False,
        "Has few poles" : False,
        "No 6+ poles" : False,
        "Has appropriate normal directions" : False,
        "Has appropriate poly count" : False,
        "Is UV-unwrapped" : False,
        "Only one UV map" : False,
        "No overlapping UVs per material" : False,
        "Minimal UV stretch" : False,
        "Model has at most two materials" : False
        },
    BlenderFileActions.CHARACTER_RIG.value: {
        "Rig is properly named through ARP" : False,
        "All parts of character are rigged" : False,
        "Rest pose is T-Pose" : False,
        "All Eye shape keys are present" : False,
        "All Eyebrow shape keys are present" : False,
        "All Nose & Mouth shape keys are present" : False,
        "All Expression shape keys are present" : False,
        "All deformations are believable" : False,
        "Eyes and jawbone move correctly with bones" : False,
        "All rig tests have passed" : False,
        },
    BlenderFileActions.PROP.value:{
        "Both object and data blocks are properly named" : False,
        "Faces the -Y direction" : False,
        "Has correct pivot placement" : False,
        "Transforms are applied" : False,
        "Geometry is manifold" : False,
        "Has proper edge flow" : False,
        "Mostly quads" : False,
        "Topology is even" : False,
        "No n-gons" : False,
        "Has few poles" : False,
        "No 6+ poles" : False,
        "Has appropriate normal directions" : False,
        "Has appropriate poly count" : False,
        "Is UV-unwrapped" : False,
        "Only one UV map" : False,
        "No overlapping UVs per material" : False,
        "Minimal UV stretch" : False,
        "Model has at most two materials" : False
        },
    BlenderFileActions.GRAYBOX.value:{
        "Layout matches animatic": False,
        "Cameras match animatic": False,
        },
    BlenderFileActions.ANIMATE_GRAYBOX.value:{
        "Characters move believably in space" : False,
        "Characters follow the animatic" : False,
        "No hairs or clothes clipping" : False,
        "No rigs have been scaled in any way" : False,
        "All rig motion is done on the rig using c_traj" : False,
        "Animation layers are baked to one layer" : False,
        "Goo Physics are baked" : False,
        },
    BlenderFileActions.SET_WORK.value:{
        "Set looks good" : False,
        "Set includes extras as needed" : False,
        "Set extras are animated" : False,
        "Set extras are parented to empties" : False,
        "Set is combined into minimal materials" : False,
        "Set has one UV map per object" : False,
        "Set has no overlapping UV islands per material" : False,
        },
    BlenderFileActions.CHARACTER_MATERIALS.value:{
        "Materials look good with the set" : False,
        "Materials make sense with the lighting" : False,
        },
    BlenderFileActions.COMPOSITE.value:{
        "Composite matches the visual style" : False,
    }
}

class BlenderFile:
    def __init__(
        self,
        project,
        action,
        scene=None,
        shot=None,
        character=None,
        setting=None,
        prop=None,
    ):
        self.project = project
        self.action = action
        self.scene = scene
        self.shot = shot
        self.character = character
        self.setting = setting
        self.prop = prop
        self.version = 1
        self.status = BlenderFileStatus.WIP
        self.unlock_approvals = 0
        self.checklist = self.assign_correct_checklist()
    
    def version_code(self):
        return f"{self.version:02d}"
    
    def sanitize(self, text):
        text = "".join(text.split(" "))
        b = "!@#$':;^%*()-–=+`~’"
        for c in b:
            text = text.replace(c, "")
        return text
    
    def get_filename(self, project_code):
        if self.action == BlenderFileActions.CHARACTER_MODEL.value:
            c = self.sanitize(self.character)
            # project_CharModel_character_status_version
            self.filename = "_".join([project_code, "CharModel", c, self.status.value, self.version_code()])
            return self.filename 
        elif self.action == BlenderFileActions.CHARACTER_RIG.value:
            c = self.sanitize(self.character)
            # project_Rig_character_status_version
            self.filename = "_".join([project_code, "CharRig", c, self.status.value, self.version_code()])
            return self.filename
        elif self.action == BlenderFileActions.PROP.value:
            p = [project_code, "Prop"]
            # project_Prop_level_setting_prop_status_version
            for thing in [self.scene, self.setting, self.prop]:
                p.append(self.sanitize(thing))
            p = p + [self.status.value, self.version_code()]
            self.filename = "_".join(p)
            return self.filename
        elif self.action == BlenderFileActions.GRAYBOX.value:
            p = [project_code, "Graybox"]
            for thing in [self.scene, self.shot]:
                p.append(self.sanitize(thing))
            p = p + [self.status.value, self.version_code()]
            self.filename = "_".join(p)
            return self.filename
        elif self.action == BlenderFileActions.ANIMATE_GRAYBOX.value:
            p = [project_code, "AnimGraybox"]
            for thing in [self.scene, self.shot]:
                p.append(self.sanitize(thing))
            p = p + [self.status.value, self.version_code()]
            self.filename = "_".join(p)
            return self.filename
        elif self.action == BlenderFileActions.SET_WORK.value:
            p = [project_code, "Set"]
            # project_Set_level_setting_status_version
            for thing in [self.scene, self.setting]:
                p.append(self.sanitize(thing))
            p = p + [self.status.value, self.version_code()]
            self.filename = "_".join(p)
            return self.filename
        elif self.action == BlenderFileActions.CHARACTER_MATERIALS.value:
            p = [project_code, "CharMaterials"]
            # project_CharMaterials_level_setting_status_version
            for thing in [self.scene, self.setting]:
                p.append(self.sanitize(thing))
            p = p + [self.status.value, self.version_code()]
            self.filename = "_".join(p)
            return self.filename
        elif self.action == BlenderFileActions.COMPOSITE.value:
            p = [project_code, "Composite"]
            # project_Composite_level_shot_status_version
            for thing in [self.scene, self.shot]:
                p.append(self.sanitize(thing))
            p = p + [self.status.value, self.version_code()]
            self.filename = "_".join(p)
            return self.filename

        raise ValueError(f"No filename is defined for Blender action {self.action!r}")
    
    def get_path(self, project_folder, project_code):
        filename = self.get_filename(project_code)
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError(
                f"No filename is defined for Blender action {self.action!r}"
            )

        filename_path = Path(filename)
        if filename_path.name != filename:
            raise ValueError("Blender filenames must not contain a directory path")
        if filename_path.suffix.lower() != ".blend":
            filename_path = filename_path.with_suffix(".blend")

        file_path = Path(project_folder).expanduser()
        if self.scene:
            file_path /= f"Scene {self.scene}"
        return file_path / filename_path
    
    def assign_correct_checklist(self):
        self.checklist = dict(SSOT_CHECKLISTS[self.action])
        return self.checklist
        
    def ready_to_request_ssot(self):
        for key in self.checklist:
            if self.checklist[key] is False:
                return False
        return True
    
    def ready_for_ssot(self):
        if self.ready_to_request_ssot():
            if self.unlock_approvals >= 2:
                return True
        return False
    
    def make_ssot(self, database=None, artist="", filepath=None):
        if not self.ready_for_ssot():
            return None

        project_directory = Path(
            str(self.project.directory_path)
        ).expanduser().resolve()
        project_code = str(self.project.project_code)
        source_path = (
            Path(filepath).expanduser().resolve()
            if filepath is not None
            else self.get_path(project_directory, project_code)
        )
        if not source_path.is_file():
            raise FileNotFoundError(
                f"Cannot make SSOT: Blender file does not exist: {source_path}"
            )

        if database is not None:
            make_ssot = getattr(database, "MakeBlenderFileSSOT", None)
            if callable(make_ssot):
                target_path = make_ssot(str(artist), str(source_path))
                if target_path:
                    self.status = BlenderFileStatus.SSOT
                    self.unlock_approvals = 2
                    return Path(str(target_path))

        previous_status = self.status
        self.status = BlenderFileStatus.SSOT
        try:
            target_path = self.get_path(
                str(project_directory),
                project_code,
            )
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if target_path != source_path:
                shutil.copy2(source_path, target_path)
        except Exception:
            self.status = previous_status
            raise

        if database is not None:
            metadata = {
                "project_name": self.project.name,
                "project_directory": str(project_directory),
                "scene": self.scene or "",
                "shot": self.shot or "",
                "character": self.character or "",
                "prop": self.prop or "",
                "setting": self.setting or "",
                "version": self.version,
                "action": self.action,
                "status": BlenderFileStatus.SSOT.value,
                "checklist": dict(self.checklist),
                "unlock_approvals": self.unlock_approvals,
            }
            record_use = getattr(database, "RecordBlenderFileUse", None)
            if callable(record_use):
                record_use(str(artist), str(target_path), metadata)

        return target_path