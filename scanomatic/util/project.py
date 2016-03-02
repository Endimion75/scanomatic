import os
import glob

import scanomatic.io.logger as logger
import scanomatic.io.paths as paths

_logger = logger.Logger("Legacy compatibility")
_paths = paths.Paths()


def rename_project(new_name, old_name=None, update_folder_name=False, update_image_names=True):

    if update_image_names:
        rename_project_images(new_name, old_name=old_name)

    if update_folder_name:
        rename_project_folder(new_name)


def _get_basepath(name):

    return os.path.dirname(os.path.abspath(name))


def _ensure_only_basename(name):

    return os.path.basename(os.path.abspath(name))


def _ensure_valid_old_name(old_name):

    if old_name is None:
        return os.path.basename(os.path.abspath("."))
    return old_name


def rename_project_images(new_name, old_name=None):

    base_path = _get_basepath(new_name)
    new_name = _ensure_only_basename(new_name)
    old_name = _ensure_valid_old_name(old_name)
    cut_site = len(old_name)
    search_pattern = "{0}_*_*.tiff".format(old_name)

    for image_path in glob.glob(os.path.join(base_path, search_pattern)):

        image_name = os.path.basename(image_path)
        destination = os.path.join(base_path, new_name + image_name[cut_site:])
        _logger.info("Renaming file {0} => {1}".format(image_path, destination))

        os.rename(image_path, destination)


def rename_project_folder(new_name):

    base_path = _get_basepath(new_name)
    destination = os.path.join(os.path.dirname(base_path), new_name)

    _logger.info("Renaming project directory {0} => {1}".format(base_path, destination))

    os.rename(base_path, destination)

