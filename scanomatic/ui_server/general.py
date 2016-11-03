import glob
import os
import re
from StringIO import StringIO
from itertools import chain
from flask import send_file, request, send_from_directory, jsonify
import numpy as np
import zipfile
from urllib import unquote, quote

from scanomatic.io.app_config import Config
from scanomatic.io.paths import Paths
from scanomatic.io.logger import Logger
from scanomatic.models.factories.scanning_factory import ScanningModelFactory
from scipy.misc import toimage
from scanomatic.image_analysis.first_pass_image import FixtureImage
from scanomatic.models.fixture_models import GrayScaleAreaModel, FixturePlateModel
from scanomatic.image_analysis.image_grayscale import is_valid_grayscale

_safe_dir = re.compile(r"^[A-Za-z_0-9.%/ \\]*$" if os.sep == "\\" else r"^[A-Za-z_0-9.%/ ]*$")
_no_super = re.compile(r"/?\.{2}/")
_logger = Logger("UI API helpers")
_ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.tiff'}
_TOO_LARGE_GRAYSCALE_AREA = 300000


def image_is_allowed(ext):
    """Validates that the image extension is allowed

    :param ext: The image file's extension
    :type ext: str
    :returns bool
    """
    global _ALLOWED_EXTENSIONS
    return ext.lower() in _ALLOWED_EXTENSIONS


def get_2d_list(data, key, **kwargs):
    """

    :param data: Example a request.values
    :param key: The key used without list marks
    :return: Nested tuples.
    """

    key += "[{0}][]"

    def _list_enumerator():
        i = 0
        while True:
            tmp = key.format(i)
            if tmp in data:
                yield tmp
                i += 1
            else:
                break

    return tuple(data.getlist(k, **kwargs) for k in _list_enumerator())


def get_area_too_large_for_grayscale(grayscale_area_model):
    global _TOO_LARGE_GRAYSCALE_AREA
    area_size = (grayscale_area_model.x2 - grayscale_area_model.x1) * \
                (grayscale_area_model.y2 - grayscale_area_model.y1)

    return area_size > _TOO_LARGE_GRAYSCALE_AREA


def get_grayscale_is_valid(values, grayscale):

    if values is None:
        return False

    return is_valid_grayscale(grayscale['targets'], values)


def usable_plates(plates):

    def usable_plate(plate):
        """

        :type plate: scanomatic.models.fixture_models.FixturePlateModel
        """
        return plate.x2 > plate.x1 and plate.y2 > plate.y1

    def unique_valid_indices():

        return tuple(sorted(plate.index - 1 for plate in plates)) == tuple(range(len(plates)))

    if not all(usable_plate(plate) for plate in plates):
        _logger.warning("Some plate coordinates are wrong")
        return False
    elif not unique_valid_indices():
        _logger.warning("Plate indices are bad")
        return False
    elif len(plates) == 0:
        _logger.warning("No plates")
        return False
    return True


def safe_directory_name(name):
    return _safe_dir.match(name) is not None and _no_super.search(name) is None


def convert_url_to_path(url):
    if url is None:
        url = ""
    else:
        url = unquote(url).split("/")
    root = Config().paths.projects_root
    return os.path.abspath(os.path.join(*chain([root], url)))


def convert_path_to_url(prefix, path):
    if prefix:
        path = "/".join(chain([prefix], os.path.relpath(path, Config().paths.projects_root).split(os.sep)))
    else:
        path = "/".join(os.path.relpath(path, Config().paths.projects_root).split(os.sep))

    path = quote(path.encode('utf8'))

    if safe_directory_name(path):
        return path
    return None


def path_is_in_jail(path):

    return Config().paths.projects_root in path


def get_search_results(path, url_prefix):

    projects = _get_possible_paths(path)
    names = list(get_project_name(p) for p in projects)
    urls = list(convert_path_to_url(url_prefix, p) for p in projects)
    if None in urls:
        try:
            names, urls = zip(*tuple((n, u) for n, u in zip(names, urls) if u is not None))
        except ValueError:
            pass
    return {'names': names, 'urls': urls}


def _get_possible_paths(path):

    dirs = tuple()
    root = None
    for root, dirs, _ in os.walk(path, followlinks=True):
        break

    if root is None:
        return tuple()
    return tuple(os.path.join(root, d) for d in dirs)


def get_project_name(project_path):
    no_name = None

    if not path_is_in_jail(project_path):
        return no_name

    candidates = glob.glob(os.path.join(project_path, Paths().scan_project_file_pattern.format("*")))
    if candidates:
        for candidate in candidates:
            model = ScanningModelFactory.serializer.load_first(candidate)
            if model:
                return model.project_name if model.project_name else no_name

    if project_path:
        return get_project_name(os.path.dirname(project_path))

    return no_name


def strip_empty_exits(exits, data):
    """
        :param exits : Exit keys
        :type exits : list[str]

        :param data : Data dict
        :type data : dict
    """
    all_exits = [e for e in exits]

    for e in all_exits:
        if e in data and (data[e] is None or len(data[e]) == 0):
            _logger.info("Removing {0} from exits because {1} is empty".format(e, data[e]))
            del data[e]
            exits.remove(e)
            _logger.info("Exits now {0}".format(exits))
        elif e not in data:
            exits.remove(e)
            _logger.info("Removing {0} from exits because not in data {1}, exits now {2}".format(e, data, exits))


def json_response(exits, data, success=True):

    strip_empty_exits(exits, data)
    is_endpoint = len(exits) == 0
    data["is_endpoint"] = is_endpoint

    if success is not None:
        data["success"] = success

    if is_endpoint:
        if "exits" in data:
            del data["exits"]
    else:
        data["exits"] = exits

    return data


def get_common_root_and_relative_paths(*file_list):

    dir_list = set(tuple(os.path.dirname(f) if os.path.isfile(f) else f for f in file_list))
    common_test = zip(*(os.path.split(p) for p in dir_list))
    root = ""
    for d_list in common_test:
        if all(d == d_list[0] for d in d_list):
            root = os.path.join(root, d_list[0])
        else:
            break

    root += os.path.sep
    start_at = len(root)
    return root, tuple(f[start_at:] for f in file_list)


def serve_zip_file(zip_name, *file_list):
    """Serves a zip-file created from a file list

    Code inspired by:
    http://stackoverflow.com/questions/2463770/python-in-memory-zip-library#2463818

    The filesystem in the zip will use the deepest common denominator in the filelist
    as its root.

    :param file_list: local paths
    :return: Flask sending of data
    """

    # file_list = tuple(str(f) for f in file_list)
    data_buffer = StringIO()
    zf = zipfile.ZipFile(data_buffer, 'a', zipfile.ZIP_DEFLATED, False)
    root, local_names = get_common_root_and_relative_paths(*file_list)
    for local_file in local_names:
        print("{0}  {1}".format(local_file, os.path.join(root, local_file)))
        zf.write(os.path.join(root, local_file), local_file)

    for zfile in zf.filelist:
        zfile.create_system = 0

    zf.close()

    data_buffer.seek(0)

    return send_file(data_buffer,
                     mimetype='application/zip, application/octet-stream',
                     as_attachment=True,
                     attachment_filename=str(zip_name))


def serve_pil_image(pil_img):
    img_io = StringIO()
    pil_img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')


def serve_numpy_as_image(data):
    return serve_pil_image(toimage(data))


def get_fixture_image_by_name(name, ext="tiff"):

    fixture_file = Paths().get_fixture_path(name)
    image_path = os.path.extsep.join((fixture_file, ext))
    return get_fixture_image(name, image_path)


def get_fixture_image(name, image_path):

    fixture = FixtureImage()
    fixture.name = name
    fixture.set_image(image_path=image_path)
    return fixture


def usable_markers(markers, image):

    def marker_inside_image(marker):
        """Compares marker to image shape

        Note that image shape comes in y, x order while markers come in x, y order

        Args:
            marker: (x, y) coordinates
        """
        val = (marker > 0).all() and marker[0] < image.shape[1] and marker[1] < image.shape[0]
        if not val:
            _logger.error("Marker {marker} is outside image {shape}".format(marker=marker, shape=image.shape))
        return val

    try:
        markers_array = np.array(markers, dtype=float)
    except ValueError:
        return False

    if markers_array.ndim != 2 or markers_array.shape[0] < 3 or markers_array.shape[1] != 2:
        _logger.error("Markers have bad shape {markers}".format(markers=markers))
        return False

    if len(set(map(tuple, markers_array))) != len(markers):
        _logger.error("Some marker is duplicated {markers}".format(markers=markers))
        return False

    return all(marker_inside_image(marker) for marker in markers_array)


def split_areas_into_grayscale_and_plates(areas):

    gs = None
    plates = []

    for area in areas:

        try:
            if area['grayscale']:
                gs = GrayScaleAreaModel(x1=area['x1'], x2=area['x2'], y1=area['y1'], y2=area['y2'])
            else:
                plates.append(FixturePlateModel(x1=area['x1'], x2=area['x2'], y1=area['y1'], y2=area['y2'],
                                                index=area['plate']))

        except (AttributeError, KeyError, TypeError):

            _logger.warning("Bad data: '{0}' does not have the expected area attributes".format(area))

    return gs, plates


_app_runs_locally = False


def set_local_app():
    global _app_runs_locally
    _app_runs_locally = True


def get_app_is_local():
    return _app_runs_locally

__ip_memory = {}


def memoize_ip(f):

    def _inner(ip):
        if ip in __ip_memory:
            return __ip_memory[ip]
        else:
            val = f(ip)
            if len(__ip_memory) > 1000:
                del __ip_memory[__ip_memory.keys()[-1]]

            __ip_memory[ip] = val

            return val

    return _inner


@memoize_ip
def is_local_ip(ip):

    # TODO: Only handles IPv4

    if ip is None:
        return False

    if ip == '127.0.0.1':
        return True

    if ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('169.254.'):
        return True

    iplist = ip.split(".")
    if ip.startswith('172.'):

        if len(iplist) == 4 and iplist[1] in ('16', '17', '18', '19', '20',
                                              '21', '22', '23', '24', '25',
                                              '26', '27', '28', '29', '30', '31'):

            return True

    return False


def decorate_access_restriction(restricted_route):

    class Restrictor(object):

        def __getattribute__(self, item):

            def restrictor(*args, **kwargs):
                if not _app_runs_locally or is_local_ip(request.remote_addr):
                    return restricted_route(*args, **kwargs)
                else:
                    _logger.warning("Illegal access attempt to {0} from {1}".format(restricted_route, request.remote_addr))
                    return send_from_directory(Paths().ui_root, Paths().ui_access_restricted)

            ret = restrictor
            ret.func_name = "{0}_{1}".format(ret.func_name, item)
            return ret

    return getattr(Restrictor(), restricted_route.__name__)


def decorate_api_access_restriction(restricted_route):

    class Restrictor(object):

        def __getattribute__(self, item):

            def restrictor(*args, **kwargs):

                if not _app_runs_locally or is_local_ip(request.remote_addr):
                    return restricted_route(*args, **kwargs)
                else:
                    _logger.warning("Illegal access attempt to {0} from {1}".format(
                        restricted_route, request.remote_addr))
                    return jsonify(success=False, is_endpoint=True, reason="Your IP is not white-listed, access denied")

            ret = restrictor
            ret.func_name = "{0}_{1}".format(ret.func_name, item)
            return ret

    return getattr(Restrictor(), restricted_route.__name__)
