import re
import logging
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from constants import BASE_DIR, MAIN_DOC_URL, EXPECTED_STATUS, PEP_URL
from configs import configure_argument_parser, configure_logging
from outputs import control_output
from utils import get_response, find_tag


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')
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
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, features='lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))
    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
        else:
            raise Exception('Ничего не нашлось')

    results = []
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (link, version, status)
        )
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_tag = find_tag(soup, 'div', attrs={'role': 'main'})
    table_tag = find_tag(main_tag, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(
        table_tag,
        'a',
        attrs={'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)

    with open(archive_path, 'wb') as file:
        file.write(response.content)

    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    pep_url = PEP_URL + '#pep-status-key'
    response = get_response(session, pep_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
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
            if status_table not in results:
                results[status_table] = 0
            status_tag = find_tag(
                tr,
                'abbr',
            )
            id_tag = find_tag(
                tr,
                'a'
            )
            pep_link = id_tag['href']
            id_url = urljoin(pep_url, pep_link)
            response = get_response(session, id_url)
            if response is None:
                return
            soup = BeautifulSoup(response.text, features='lxml')
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
            if status_id not in EXPECTED_STATUS[status_table]:
                error_msg = (
                    f'Несовпадающие статусы: {id_url}\n'
                    f'Статус в карточке: {status_id}\n'
                    f'Ожидаемые статусы: {EXPECTED_STATUS[status_table]}'
                )
                logging.error(error_msg, stack_info=True)
            else:
                results[status_table] += 1
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

    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')

    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)

    if results is not None:
        control_output(results, args)

    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
