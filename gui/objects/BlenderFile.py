from enum import Enum
from pathlib import Path

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
    
    def get_filename(self, project_code):
        if self.action == BlenderFileActions.CHARACTER_MODEL.value:
            c = "".join(self.character.split(" ")) # remove any spaces
            self.filename = "_".join([project_code, "CharModel", c, self.status.value, self.version_code()])
            # the caller uses a worker to get the project_code from database
            return self.filename 
    
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
        for key in self.checklist.keys:
            if self.checklist[key] == False:
                return False
        return True
    
    def ready_for_ssot(self):
        if self.ready_to_request_ssot():
            if self.unlock_approvals == 2:
                return True
        return False
    
    def make_ssot(self):
        if (self.ready_for_ssot):
            self.status = BlenderFileStatus.SSOT
            # make a duplicate of the file, rename 