class HTTPError(Exception):
    """Ошибка: соединения."""

    pass


class EndpointError(Exception):
    """Ошибка: эндпойнт не корректен."""

    pass


class TelegramError(Exception):
    """Ошибка: отправка сообщения."""

    pass
