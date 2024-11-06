import logging
import os
import sys
import time
from http import HTTPStatus
from typing import Dict, List, Union

import requests
import telegram
import telebot

from dotenv import load_dotenv
from exceptions import HTTPError, EndpointError, TelegramError


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Функция проверки доступности переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot: telegram.Bot, message: str):
    """Sends a message to Telegram."""
    try:
        logging.error('Начинаем отправку сообщения!')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug('Сообщение успешно отправлено в Telegram')
    except telegram.error.TelegramError as e:
        raise TelegramError("Ошибка отправки сообщения в Telegram.") from e


def get_api_answer(timestamp: int) -> Dict[str, Union[str, str]]:
    """Делает запрос к единственному эндпоинту API-сервиса."""
    logging.info('Начали запрос к API')
    current_timestamp = timestamp or int(time.time())
    payload = {'from_date': current_timestamp}
    params_api = {'url': ENDPOINT, 'headers': HEADERS, 'params': payload}
    try:
        response = requests.get(**params_api)
    except Exception as error:
        raise EndpointError('Ошибка в запросе к API {error} с параметрами: '
                            '{url}, {headers}, {params}'
                            .format(**params_api, error=error))
    if response.status_code != HTTPStatus.OK:
        raise HTTPError('Ошибка соединения: {status}, {text}'.format(
            status=response.status_code,
            text=response.text))
    return response.json()


def check_response(response: Dict[str, Union[str, str]]) \
        -> List[Union[str, str]]:
    """Функция проверки ответа API на соответствие."""
    if not isinstance(response, dict):
        raise TypeError("homeworks не словарь")
    if "homeworks" not in response:
        raise KeyError("В ответе API нет ключа homeworks")
    if not isinstance(response["homeworks"], list):
        raise TypeError("Ключ homeworks не список")
    if "current_date" not in response:
        raise KeyError("Ключ current_date пустой")
    return response["homeworks"]


def parse_status(homework: Dict[str, Union[str, str]]) \
        -> str:
    """Функция присвоения статуса домашней работе."""
    logging.info("Старт проверки статусов ДЗ")
    if "homework_name" not in homework:
        raise KeyError("В ответе отсутствует ключ homework_name")
    homework_name = homework.get("homework_name")
    status = homework.get("status")
    if not status:
        raise KeyError("В ответе отсутствует ключ status")
    if status not in (HOMEWORK_VERDICTS):
        raise ValueError(f"Неизвестный статус работы - {status}")
    verdict = HOMEWORK_VERDICTS[homework.get("status")]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Недоступны переменные окружения!')
        sys.exit('Программа принудительно остановлена')
    bot = telebot.TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    old_message = 'messages'
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = homeworks[0]
                status = parse_status(homework)
            else:
                status = f'{timestamp}, изменений в домашних работах нет.'
            if status != old_message:
                old_message = status
                send_message(bot=bot, message=status)
            else:
                logging.debug('Новые статусы отсутствуют')
            timestamp = response.get('current_date', timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != old_message:
                old_message = message
                send_message(bot=bot, message=message)
            logging.error(message, exc_info=True)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
        filename='main.log',
        filemode='w'
    )
    main()
