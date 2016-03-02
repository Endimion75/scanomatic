from enum import Enum
from scanomatic.models.factories.compile_project_factory import CompileImageAnalysisFactory, CompileProjectFactory
from scanomatic.io.logger import Logger

FIRST_PASS_SORTING = Enum("FIRST_PASS_SORTING", names=("Index", "Time"))


class CompilationResults(object):

    def __init__(self, compilation_path=None, compile_instructions_path=None, sort_mode=FIRST_PASS_SORTING.Time):

        self._logger = Logger("Compilation results")
        self._compilation_path = compilation_path
        self._compile_instructions = None
        self._plates = None
        self._plate_position_keys = None
        self._image_models = []
        self._used_models = []
        self._current_model = None
        self._loading_length = 0
        if compile_instructions_path:
            self._load_compile_instructions(compile_instructions_path)
        if compilation_path:
            self._load_compilation(self._compilation_path, sort_mode=sort_mode)

    @classmethod
    def create_from_data(cls, path, compile_instructions, image_models, used_models=None):

        if used_models is None:
            used_models = []

        new = cls()
        new._compilation_path = path
        new._compile_instructions = CompileProjectFactory.copy(compile_instructions)
        new._image_models = CompileImageAnalysisFactory.copy_iterable_of_model(list(image_models))
        new._used_models = CompileImageAnalysisFactory.copy_iterable_of_model(list(used_models))
        new._loading_length = len(new._image_models)
        return new

    def _load_compile_instructions(self, path):

        try:
            self._compile_instructions = CompileProjectFactory.serializer.load(path)[0]
        except IndexError:
            self._logger.error("Could not load path {0}".format(path))
            self._compile_instructions = None

    def _load_compilation(self, path, sort_mode=FIRST_PASS_SORTING.Time):

        images = CompileImageAnalysisFactory.serializer.load(path)
        self._logger.info("Loaded {0} compiled images".format(len(images)))

        self._reindex_plates(images)

        if sort_mode is FIRST_PASS_SORTING.Time:
            self._image_models = list(CompileImageAnalysisFactory.copy_iterable_of_model_update_indices(images))
        else:
            self._image_models = list(CompileImageAnalysisFactory.copy_iterable_of_model_update_time(images))

        self._loading_length = len(self._image_models)

    @staticmethod
    def _reindex_plates(images):

        for image in images:

            if image and image.fixture and image.fixture.plates:

                for plate in image.fixture.plates:
                    plate.index -= 1

    def __len__(self):

        return self._loading_length

    def __getitem__(self, item):
        """


        :rtype: scanomatic.models.compile_project_model.CompileImageAnalysisModel
        """
        if not self._image_models:
            return None

        if item < 0:
            item %= len(self._image_models)

        try:
            return sorted(self._image_models, key=lambda x: x.image.time_stamp)[item]
        except (ValueError, IndexError):
            return None

    def __add__(self, other):

        """

        :type other: CompilationResults
        """

        # TODO: start time needed to add compilation results in relevant manner
        start_time_difference = 0

        other_start_index = len(self)
        other_image_models = []
        for index in range(len(other)):
            model = CompileImageAnalysisFactory.copy(other[index])
            model.time += start_time_difference
            model.index += other_start_index
            other_image_models.append(model)

        other_image_models += self._image_models
        other_image_models = sorted(other_image_models, key=lambda x: x.image.time_stamp)

        return CompilationResults.create_from_data(self._compilation_path, self._compile_instructions,
                                                   other_image_models, self._used_models)

    @property
    def compile_instructions(self):

        """


        :rtype: scanomatic.models.compile_project_model.CompileInstructionsModel
        """

        return self._compile_instructions

    @property
    def plates(self):

        res = self[-1]
        if res:
            return res.fixture.plates
        return None

    @property
    def last_index(self):

        return len(self._image_models) - 1

    @property
    def total_number_of_images(self):

        return len(self._image_models) + len(self._used_models)

    @property
    def current_image(self):
        """

        :rtype : scanomatic.models.compile_project_model.CompileImageAnalysisModel
        """
        return self._current_model

    @property
    def current_absolute_time(self):

        return self.current_image.image.time_stamp + self.compile_instructions.start_time

    def recycle(self):

        self._image_models += self._used_models
        self._used_models = []
        self._current_model = None

    def get_next_image_model(self):
        """

        :rtype : scanomatic.models.compile_project_model.CompileImageAnalysisModel
        """
        model = self[-1]
        self._current_model = model
        if model:
            self._image_models.remove(model)
            self._used_models.append(model)
        return model