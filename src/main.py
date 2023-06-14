import re
import logging
from urllib.parse import urljoin
from collections import defaultdict

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from constants import (
    BASE_DIR, MAIN_DOC_URL,
    RE_PYTHON_VERSION_STATUS,
    RE_END_PDF_A4_ZIP, PEP_0_URL
)
from configs import configure_argument_parser, configure_logging
from outputs import control_output
from utils import get_response, find_tag
from exceptions import ResponseNoneException, ParserFindTagException


def create_soup(session, url):
    """Функция создания "супа" из урла."""
    response = get_response(session, url)
    if response is None:
        error_msg = f'{url} не загрузилась'
        logging.error(error_msg, stack_info=True)
        raise ResponseNoneException(error_msg)
    return BeautifulSoup(response.text, features='lxml')


def whats_new(session):
    """Парсер для проверки "что нового в питоне"."""
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = create_soup(session, whats_new_url)
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all(
        'li',
        attrs={'class': 'toctree-l1'}
    )
    results = []
    results.append(('Ссылка на статью', 'Заголовок', 'Редактор, Автор'))
    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        try:
            soup = create_soup(session, version_link)
        except ResponseNoneException:
            continue
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))
    return results


def latest_versions(session):
    """Парсер для последние одновления."""
    soup = create_soup(session, MAIN_DOC_URL)
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
        else:
            error_msg = 'Не нашлось нужного тега'
            logging.error(error_msg, stack_info=True)
            raise ParserFindTagException(error_msg)

    results = []
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(RE_PYTHON_VERSION_STATUS, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (link, version, status)
        )
    return results


def download(session):
    """Парсер скачивания архива."""
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    soup = create_soup(session, downloads_url)
    main_tag = find_tag(soup, 'div', attrs={'role': 'main'})
    table_tag = find_tag(main_tag, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(
        table_tag,
        'a',
        attrs={'href': re.compile(RE_END_PDF_A4_ZIP)}
    )
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    try:
        downloads_dir.mkdir(exist_ok=True)
    except PermissionError:
        raise PermissionError('Нет прав для создания папки.')
    archive_path = downloads_dir / filename
    response = session.get(archive_url)

    with open(archive_path, 'wb') as file:
        file.write(response.content)

    info_msg = f'Архив был загружен и сохранён: {archive_path}'
    logging.info(info_msg)


def status_pep(article_tag):
    """Получение словаря статусов."""
    results = defaultdict(list)
    status_tag = find_tag(
        article_tag,
        'section',
        attrs={'id': 'pep-status-key'}
    )
    li_tags = status_tag.find_all('li')
    for li in li_tags:
        abbr = find_tag(
            li,
            'strong',
        )
        name = find_tag(
            li,
            'em',
        )
        key = abbr.text
        if key == '<No letter>':
            key = ''
        results[key].append(name.text)
    return results


def pep(session):
    """Парсер пепа."""
    soup = create_soup(session, PEP_0_URL)
    article_tag = find_tag(
        soup,
        'article',
    )
    index_tag = find_tag(
        article_tag,
        'section',
        attrs={'id': 'index-by-category'}
    )
    section_by_pep = index_tag.find_all('section')
    count = 0
    expected_status = status_pep(article_tag)
    results = {}
    results['Статус'] = 'Количество'
    for section in tqdm(section_by_pep):
        table_tag = section.find('table')
        if table_tag is None:
            continue
        tbody_tag = find_tag(
            table_tag,
            'tbody',
        )
        tr_tags = tbody_tag.find_all('tr')
        for tr in tr_tags:
            status_tag = find_tag(
                tr,
                'abbr',
            )
            status_table = status_tag.text[1:]
            name_status = expected_status[status_table][0]
            if name_status not in results:
                results[name_status] = 0
            status_tag = find_tag(
                tr,
                'abbr',
            )
            id_tag = find_tag(
                tr,
                'a'
            )
            pep_link = id_tag['href']
            id_url = urljoin(PEP_0_URL, pep_link)
            soup = create_soup(session, id_url)
            id_pep_tag = find_tag(
                soup,
                'dl'
            )
            dt_tags = id_pep_tag.find_all('dt')
            for dt in dt_tags:
                dd = dt.find(string='Status')
                if dd is not None:
                    status_id = dt.find_next_sibling().string
                    count += 1
                    break
            if status_id not in expected_status[status_table]:
                results[status_id] = 1
                error_msg = (
                    f'Несовпадающие статусы: {id_url}\n'
                    f'Статус в карточке: {status_id}\n'
                    f'Ожидаемые статусы: {expected_status[status_table]}'
                )
                logging.error(error_msg, stack_info=True)
            else:
                results[name_status] += 1
    results['Total'] = count
    results = [(key, value) for key, value in results.items()]
    return results


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')

    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    logging.info('Парсер запущен!')
    results = MODE_TO_FUNCTION[parser_mode](session)

    if results is not None:
        file_path = control_output(results, args)
        if file_path is not None:
            info_msg = f'Файл с результатами был сохранён: {file_path}'
            logging.info(info_msg)

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
