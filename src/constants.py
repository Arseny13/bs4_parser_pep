from pathlib import Path

MAIN_DOC_URL = 'https://docs.python.org/3/'
BASE_DIR = Path(__file__).parent
DOWLOADS_DIR = BASE_DIR / 'downloads'
RESULTS_DIR = BASE_DIR / 'results'
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'parser.log'

LOG_FORMAT = '"%(asctime)s - [%(levelname)s] - %(message)s"'
DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'

PEP_URL = 'https://peps.python.org/'
PEP_0_URL = PEP_URL + '#pep-status-key'

RE_PYTHON_VERSION_STATUS = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
RE_END_PDF_A4_ZIP = r'.+pdf-a4\.zip$'

PRETTY_MODE = 'pretty'
FILE_MODE = 'file'

EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}
