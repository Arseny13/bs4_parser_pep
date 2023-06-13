class ParserFindTagException(Exception):
    """Вызывается, когда парсер не может найти тег."""
    pass


class ResponseNoneException(Exception):
    """Вызывается, когда ответ None."""
    pass
