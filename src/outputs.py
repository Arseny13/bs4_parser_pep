import csv
import datetime as dt

from prettytable import PrettyTable

from constants import BASE_DIR, DATETIME_FORMAT, PRETTY_MODE, FILE_MODE


def default_output(results):
    for row in results:
        print(*row)


def pretty_output(results, *args):
    table = PrettyTable()
    table.field_names = results[0]
    table.align = 'l'
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args):
    results_dir = BASE_DIR / 'results'
    try:
        results_dir.mkdir(exist_ok=True)
    except PermissionError:
        raise PermissionError('Нет прав для создания папки.')
    parser_mode = cli_args.mode
    now = dt.datetime.now()
    now_formatted = now.strftime(DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = results_dir / file_name
    with open(file_path, 'w', encoding='utf-8') as f:
        writer = csv.writer(f, dialect='unix')
        writer.writerows(results)

    return file_path


MODE_TO_OUTPUT = {
    PRETTY_MODE: pretty_output,
    FILE_MODE: file_output,
}


def control_output(results, cli_args):
    output = cli_args.output
    if output in MODE_TO_OUTPUT:
        MODE_TO_OUTPUT[output](results, cli_args)
    else:
        default_output(results)
