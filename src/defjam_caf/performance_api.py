"""Use the selected game toolchain's read-only, versioned authoring API."""
import json
from pathlib import Path
import tempfile

from .container import SaveError
from .fighter_mod import contract


class Link:
    def __init__(self, runtime, data, workspace):
        self.runtime = Path(runtime).resolve()
        self.game = (Path(data)/'extracted').resolve()
        self.workspace = Path(workspace)/'performance'
        self.workspace.mkdir(parents=True, exist_ok=True)
        if not self.game.is_dir():
            raise SaveError('Open your game data directory first')
        self.catalog = self.call('workshop-catalog')
        if self.catalog.get('schema') != 'fighter-workshop-catalog-1':
            raise SaveError('These fighter tools do not support the performance editor')

    def call(self, command, request=None):
        with tempfile.TemporaryDirectory(prefix='request-',dir=self.workspace) as folder:
            arguments = [command,'--game',str(self.game)]
            if request is not None:
                path = Path(folder)/'request.json'
                path.write_text(json.dumps(request),encoding='utf-8')
                arguments += ['--workshop-request',str(path)]
            return contract(self.runtime,arguments,folder,self.workspace)

    def voice(self, request):
        return self.call('workshop-audio',request)

    def animation(self, request):
        return self.call('workshop-animation',request)
