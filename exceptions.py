class HTTPError(Exception):
    """Ошибка: соединения."""


class EndpointError(Exception):
    """Ошибка: эндпойнт не корректен."""


class TelegramError(Exception):
    """Ошибка: отправка сообщения."""
