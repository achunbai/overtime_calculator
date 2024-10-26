# 一个便利的计算器，用于计算加班时长等
# 适用于 深圳佛山桂林
# 评价部分从之前的html中移植，如有冒犯 雨我无瓜
# -*- coding: utf-8 -*-
import csv
import os
import json
import requests
import argparse
import shutil
import platform
from bs4 import BeautifulSoup
from typing import Dict, Set, Tuple, List, Optional
from datetime import datetime, timedelta, time
from tabulate import tabulate
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager


# 定义路径前缀
CONFIG_PATH = 'config/'
OUTPUT_PATH = 'output/'
LOCAL_DATA_PATH = 'data/'


# 这里设置Cookie和配置文件路径
COOKIES_FILE = CONFIG_PATH + 'cookies.json'
CONFIG_FILE = CONFIG_PATH + 'config.json'


# 请求头信息
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
HOST = 'hr.quectel.com'
ORIGIN = 'https://hr.quectel.com'
REFERER = 'https://hr.quectel.com/portal/index'


# 本地文件操作
def get_cookie():
    """
    从 COOKIE_FILE 中读取 Cookie。

    返回值:
        dict: 如果存在 Cookie 文件，返回保存的 Cookie；否则返回 None。
    """
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, 'r', encoding='utf-8') as file:
            cookie = json.load(file)
            return cookie
    return None

def read_config():
    """
    读取 CONFIG_FILE。

    返回值:
        dict: 如果存在配置文件，返回保存的配置数据；否则返回 None。
    """
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            config = json.load(file)
    return config

def get_clock_in_api_endpoint_from_config():
    """
    从 CONFIG_FILE 中读取打卡数据接口。

    返回值:
        str: 打卡数据接口的 URL，如果配置文件存在且包含该信息；否则返回 None。
    """
    config_data = read_config()
    if config_data:
        return config_data.get('clock_in_api_endpoint')
    return None

def get_process_application_api_endpoint_from_config():
    """
    从 CONFIG_FILE 中读取流程申请信息接口。

    返回值:
        str: 流程申请信息接口的 URL，如果配置文件存在且包含该信息；否则返回 None。
    """
    config_data = read_config()
    if config_data:
        return config_data.get('process_application_api_endpoint')
    return None

def get_holiday_data_from_local(records: json, holiday_data: json) -> Tuple[Dict, Set]:
    """
    从本地 JSON 数据中获取指定年份的节假日数据。

    参数:
        records (json): 包含打卡记录的 JSON 数据。
        holiday_data (json): 包含节假日信息的 JSON 数据。

    返回值:
        Tuple[Dict, Set]: 返回一个包含节假日和工作日的元组。
            - Dict: 节假日数据，键为日期，值为工资倍数。
            - Set: 工作日数据，包含日期的集合。

    异常:
        SystemExit: 如果数据文件为空或格式不正确。
    """
    if not records:
        print("数据文件为空或格式不正确。")
        exit()

    if holiday_data:
        holidays = {}
        workdays = set()
        for date, info in holiday_data['holiday'].items():
            if info['date'][:-3] == records[0]['SHIFTTERM'][:-3]:
                if info['holiday']:
                    holidays[info['date']] = info['wage']
                else:
                    workdays.add(info['date'])
        return holidays, workdays
    else:
        print("节假日数据文件为空或格式不正确。")
        exit()

def ensure_directory_exists(file_path):
    """
    确保文件路径的目录存在。如果不存在，则创建它。

    参数:
        file_path (str): 文件路径。
    """
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def save_cookie(cookie):
    """
    保存 Cookie 到 COOKIE_FILE。

    参数:
        cookie (dict): 要保存的 Cookie。
    """
    ensure_directory_exists(COOKIES_FILE)
    with open(COOKIES_FILE, 'w', encoding='utf-8') as file:
        json.dump({'user_cookie': cookie}, file)

def save_config(config_data):
    """
    保存配置数据到配置文件。
    
    参数:
        config_data (dict): 要保存的配置数据。
    """
    ensure_directory_exists(CONFIG_FILE)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as file:
        json.dump(config_data, file, ensure_ascii=False, indent=4)

def save_clock_in_api_endpoint_to_config(config_data):
    """
    保存获取到的打卡数据接口到 CONFIG_FILE。
    
    参数:
        config_data (str): 打卡数据接口的 URL。
    """
    config = read_config()
    config['clock_in_api_endpoint'] = config_data
    save_config(config)

def save_process_application_api_endpoint_to_config(config_data):
    """
    保存获取到的流程申请信息接口到 CONFIG_FILE。
    
    参数:
        config_data (str): 流程申请信息接口的 URL。
    """
    config = read_config()
    config['process_application_api_endpoint'] = config_data
    save_config(config)


# 在线获取
def get_holiday_data_online(records: json) -> Tuple[Dict, Set]:
    """
    在线获取指定年份的节假日数据。

    参数:
        records (json): 包含打卡记录的 JSON 数据。

    返回值:
        Tuple[Dict, Set]: 返回一个包含节假日和工作日的元组。
            - Dict: 节假日数据，键为日期，值为工资倍数。
            - Set: 工作日数据，包含日期的集合。

    异常:
        SystemExit: 如果数据文件为空或格式不正确。
    """
    if records:
        sample_date = records[0]['SHIFTTERM']
        year = sample_date.split('-')[0]
    else:
        print("数据文件为空或格式不正确。")
        exit()
    headers = {
        'User-Agent': USER_AGENT
    }
    try:
        api_url = f'https://timor.tech/api/holiday/year/{year}'
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        holiday_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        holiday_data = None
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        holiday_data = None
    if holiday_data:
        holidays = {}
        workdays = set()
        for date, info in holiday_data['holiday'].items():
            if info['date'][:-3] == records[0]['SHIFTTERM'][:-3]:
                if info['holiday']:
                    holidays[info['date']] = info['wage']
                else:
                    workdays.add(info['date'])
    return holidays, workdays

def get_clock_in_api_endpoint_online(user_cookie):
    """
    从用户的 Cookie 信息中获取个人打卡查询的用户变量。
    
    参数：
        user_cookie：用户的 Cookie 信息，用于身份验证。

    返回值：
        个人打卡查询的用户变量。    
    """
    user_cookie = str(user_cookie)  # 强制转换为字符串
    url = "https://hr.quectel.com/"
    headers = {
        'Host': HOST,
        'Origin': ORIGIN,
        'Referer': REFERER,
        'User-Agent': USER_AGENT,
        'Cookie': user_cookie
    }
    response = requests.request("GET", url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    link = soup.find('a', {'title': '个人考勤查询'})
    if link is None:
        raise ValueError("未找到个人考勤查询链接")
    href = link['href']
    user_variable = href[href.index('!')+1:]
    return user_variable

def get_process_application_api_endpoint_online(user_cookie):
    """
    从用户的 Cookie 信息中获取个人流程申请的用户变量。

    参数：
        user_cookie：用户的 Cookie 信息，用于身份验证。

    返回值：
        个人流程申请的用户变量。    
    """
    user_cookie = str(user_cookie)  # 强制转换为字符串
    url = "https://hr.quectel.com/"
    headers = {
        'Host': HOST,
        'Origin': ORIGIN,
        'Referer': REFERER,
        'User-Agent': USER_AGENT,
        'Cookie': user_cookie
    }
    response = requests.request("GET", url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    link = soup.find('a', {'title': '流程申请'})
    if link is None:
        raise ValueError("未找到个人流程申请查询链接")
    href = link['href']
    user_variable = href[href.index('!')+1:]
    return user_variable

def get_clock_in_data(user_variable, user_cookie, target_month, target_year):
    """
    从指定网页获取个人打卡查询数据。

    参数：
        - user_variable：用户变量，用于构建 URL。
        - user_cookie：用户的 Cookie 信息，用于身份验证。
        - target_month：目标月份，格式为数字，例如 9 表示九月。
        - target_year（可选）：目标年份。

    返回值：
        服务器响应的 JSON 数据，包含个人打卡查询结果。
    """
    # 确保 target_month 是两位数格式
    target_month = f"{int(target_month):02d}"
    
    # 220302: 个人打卡查询
    url = f"https://hr.quectel.com/ajax/function/alist!{user_variable}.220302"
    user_cookie = str(user_cookie)  # 强制转换为字符串
    payload = json.dumps({
        "appParam": {"TERM": f"{target_year}-{target_month}-01T00:00:00.000Z"},
        "appFnKey": "SE0302",
        "formData": {}
    })
    headers = {
        'Host': HOST,
        'Origin': ORIGIN,
        'Referer': REFERER,
        'User-Agent': USER_AGENT,
        'Cookie': user_cookie,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    
    return response.json()

def get_attendance_data(user_variable, user_cookie, target_month, target_year):
    """
    从指定网页获取个人考勤查询数据。

    参数：
        - user_variable：用户变量，用于构建 URL。
        - user_cookie：用户的 Cookie 信息，用于身份验证。
        - target_month：目标月份，格式为数字，例如 9 表示九月。
        - target_year：目标年份。

    返回值：
        服务器响应的 JSON 数据，包含个人考勤查询结果。
    """
    # 确保 target_month 是两位数格式
    target_month = f"{int(target_month):02d}"
    
    # 220398: 个人考勤查询
    url = f"https://hr.quectel.com/ajax/function/alist!{user_variable}.220398"
    user_cookie = str(user_cookie)  # 强制转换为字符串
    payload = json.dumps({
        "appParam": {"TERM": f"{target_year}-{target_month}-01T00:00:00.000Z"},
        "appFnKey": "SE0398",
        "formData": {}
    })
    headers = {
        'Host': HOST,
        'Origin': ORIGIN,
        'Referer': REFERER,
        'User-Agent': USER_AGENT,
        'Cookie': user_cookie,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    
    return response.json()

def get_process_application_data(user_variable, user_cookie):
    """
    从指定网页获取审批流程中的请假数据，事假可以用加班抵扣，年假就不计算迟到。

    参数：
    - user_variable：用户变量，用于构建 URL。
    - user_cookie：用户的 Cookie 信息，用于身份验证。

    返回值：
    - 服务器响应的 JSON 数据，包含个人流程审批查询结果。
    """
    # 290104: 已完成流程申请查询
    url = f"https://hr.quectel.com/ajax/function/alist!{ user_variable }.290104"
    user_cookie = str(user_cookie)  # 强制转换为字符串
    payload = json.dumps({
        "searchcols": "",
        "order": "asc",
        "limit": 0,
        "offset": 0,
        "total": 0,
        "editType": 0,
        "form": {
            "appParam": {
            "TREEID": 7
            },
            "appFnKey": "SW0104",
            "formData": {
                "SW0101": {
                    "fnparam": {},
                    "data": [
                    {
                        "E_EXTATTR": "SW0102,SW0104,SE0348",
                        "FINISHNUM": "0",
                        "VALID": "1",
                        "NEWNUM": "0",
                        "PID": "1000",
                        "RETURNNUM": "0",
                        "K_PKEYS": "CTdI8IsausezsJ_zJEHwGQ",
                        "K_LOCKED": "",
                        "K_EXTRAS": "ld5OMqeQ9gwmyA5ArfvbdA",
                        "EMPID": "16326",
                        "AUTHKEY": "ODJ26UDjT_siqMi42VPqog",
                        "INAPPNUM": "0",
                        "TITLE": "请假申请",
                        "ID": "7"
                    }
                    ],
                "old": [],
                "bnparam": {}
                }
            }
        }
    })
    headers = {
        'Host': HOST,
        'Origin': ORIGIN,
        'Referer': REFERER,
        'User-Agent': USER_AGENT,
        'Cookie': user_cookie,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    
    return response.json()

def get_delay_deduction_data(auth_key, user_cookie):
    """
    通过 AUTHKEY 获取延时工时扣减的数据

    参数：
    - auth_key：流程申请中项目的 AUTHKEY，用于构建 URL。
    - user_cookie：用户的 Cookie 信息，用于身份验证。

    返回值：
    - 服务器响应的 JSON 数据，包含延时工时扣减申请审批查询结果。
    """
    # 290104: 已完成流程申请查询
    url = f"https://hr.quectel.com/ajax/flowform/formlist!{ auth_key }"
    user_cookie = str(user_cookie)  # 强制转换为字符串
    payload = json.dumps({
        "formData": {},
        "bizData": {},
        "bizFnKey": 'null',
        "comments": 'null',
        "fileIds": 'null',
        "signData": 'null',
        "receivers": 'null',
        "freeNode": 'null'
    })
    headers = {
        'Host': HOST,
        'Origin': ORIGIN,
        'Referer': REFERER,
        'User-Agent': USER_AGENT,
        'Cookie': user_cookie,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    
    return response.json()


# 浏览器操作
def fetch_cookie_via_browser(browser='auto'):
    """
    启动浏览器获取 Cookie 并返回。

    参数:
        browser (str): 使用的浏览器类型 ('chrome', 'edge', 'auto')。默认为 'auto'。

    返回值:
        str: 获取到的 Cookie 字符串，如果成功；否则返回 None。
    """
    if browser == 'auto':
        # 自动检测 Chrome 浏览器是否存在
        print(f"您的系统为{platform.system()}，正在检测 Chrome 或 Edge 浏览器是否安装...")
        chrome_path = None
        if platform.system() == 'Windows':
            system_drive = os.getenv('SystemDrive', 'C:')
            # 需要在Program Files前面添加斜杠，不然获取到的路径不正确
            chrome_path = os.path.join(system_drive, "\\Program Files", "Google", "Chrome", "Application", "chrome.exe")
            if os.path.exists(chrome_path):
                browser = 'chrome'
            else:
                browser = 'edge'
        elif platform.system() == 'Linux':
            if shutil.which("google-chrome") or shutil.which("chromium-browser"):
                browser = 'chrome'
            elif shutil.which("microsoft-edge"):
                browser = 'edge'
            else:
                print("未找到 Chrome 或 Edge 浏览器，请至少安装其中一种浏览器。")
                exit()
        elif platform.system() == 'Darwin':  # macOS
            if os.path.exists("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
                browser = 'chrome'
            elif os.path.exists("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"):
                browser = 'edge'
            else:
                print("未找到 Chrome 或 Edge 浏览器，请至少安装其中一种浏览器, MacOS中Safari经过测试不可用, 需要关闭自动化才可以与页面进行交互。")
                exit()
        else:
            print("未知的操作系统。")
            exit()

    if browser == 'edge':
        options = EdgeOptions()
        service = EdgeService(EdgeChromiumDriverManager().install())
    else:
        options = ChromeOptions()
        service = ChromeService(ChromeDriverManager().install())

        # 添加 Chrome 选项
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-browser-side-navigation")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

    print(f"正在启动{browser}浏览器以获取Cookie...")
    driver = webdriver.Chrome(service=service, options=options) if browser == 'chrome' else webdriver.Edge(service=service, options=options)
    driver.get("https://hr.quectel.com")

    print("请在打开的浏览器中登录网站...")
    input("登录完成后按回车继续...")

    # 确保浏览器窗口保持打开状态
    try:
        cookies = driver.get_cookies()
    except Exception as e:
        print(f"获取Cookie时出错: {e}")
        driver.quit()
        return None

    driver.quit()

    cookie_str = "; ".join(f"{cookie['name']}={cookie['value']}" for cookie in cookies)
    return cookie_str


# 逻辑部分
def get_day_type(date: str, holidays: Dict[str, int], workdays: Set[str]) -> str:
    """
    判断指定日期的性质。

    参数:
        date (str): 要判断的日期，格式为 'YYYY-MM-DD'。
        holidays (Dict[str, int]): 节假日数据，键为日期，值为工资倍数。
        workdays (Set[str]): 工作日数据，包含日期的集合。

    返回值:
        str: 返回日期的性质，可能的值为 "节假日", "节假日(周末)", "周末", "工作日"。
    """
    if date in holidays:
        if holidays[date] == 3:
            return "节假日"
        return "节假日(周末)"
    if date not in workdays and datetime.strptime(date, '%Y-%m-%d').weekday() >= 5:
        return "周末"
    return "工作日"

def parse_process_application_data(leave_data: List[Dict], user_cookie: str) -> Tuple[Dict[str, List[Tuple[str, str]]], Dict[str, List[Tuple[str, str]]], Dict[str, List[Tuple[str, str]]]]:
    """
    解析流程申请数据。

    参数:
        leave_data (List[Dict]): 包含年假、事假和延时工时扣减记录的列表，每个记录是一个字典。
        user_cookie (str): 用户的 Cookie 信息，用于身份验证。

    返回值:
        Tuple[Dict[str, List[Tuple[str, str]]], Dict[str, List[Tuple[str, str]]], Dict[str, List[Tuple[str, str]]]]: 返回三个字典，分别存储年假、事假和延时工时扣减的信息。
        - annual_leave (Dict[str, List[Tuple[str, str]]]): 年假数据，键为日期，值为时间段的列表（开始时间，结束时间）。
        - personal_leave (Dict[str, List[Tuple[str, str]]]): 事假数据，键为日期，值为时间段的列表（开始时间，结束时间）。
        - delay_deduction (Dict[str, List[Tuple[str, str]]]): 延时工时扣减数据，键为日期，值为时间段的列表（开始时间，结束时间）。
    """
    annual_leave = {}  # 存储年假的字典
    personal_leave = {}  # 存储事假的字典
    delay_deduction = {}  # 存储延时工时扣减的字典

    for record in leave_data:
        abstracts = record['ABSTRACTS']  # 获取摘要信息
        parts = abstracts.split('|')
        leave_type = parts[1] if len(parts) > 1 else None

        if leave_type in ['年假', '事假'] and len(parts) > 3:
            try:
                if ' - ' in parts[3]:
                    start_time, end_time = parts[3].split(' - ')
                elif ' 至 ' in parts[3]:
                    start_time, end_time = parts[3].split(' 至 ')
                else:
                    raise ValueError("Invalid time range format")

                start_datetime = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
                end_datetime = datetime.strptime(end_time, '%Y-%m-%d %H:%M')

                # 计算每一天的请假时间段
                current_datetime = start_datetime
                while current_datetime.date() <= end_datetime.date():
                    date_str = current_datetime.strftime('%Y-%m-%d')
                    if current_datetime.date() == start_datetime.date():
                        # 第一天的请假时间段
                        day_start_time = start_datetime
                        day_end_time = min(end_datetime, datetime.combine(current_datetime.date(), time(18, 0)))
                    elif current_datetime.date() == end_datetime.date():
                        # 最后一天的请假时间段
                        day_start_time = datetime.combine(current_datetime.date(), time(9, 0))
                        day_end_time = end_datetime
                    else:
                        # 中间天的请假时间段
                        day_start_time = datetime.combine(current_datetime.date(), time(9, 0))
                        day_end_time = datetime.combine(current_datetime.date(), time(18, 0))

                    # 根据请假类型将数据存储到相应的字典中
                    if leave_type == '年假':
                        if date_str not in annual_leave:
                            annual_leave[date_str] = []
                        annual_leave[date_str].append((day_start_time.strftime('%H:%M'), day_end_time.strftime('%H:%M')))
                    elif leave_type == '事假':
                        if date_str not in personal_leave:
                            personal_leave[date_str] = []
                        personal_leave[date_str].append((day_start_time.strftime('%H:%M'), day_end_time.strftime('%H:%M')))

                    current_datetime += timedelta(days=1)
            except ValueError as e:
                print(f"Error parsing time range in record: {record}")
                print(f"Exception: {e}")

        elif leave_type == '销假申请':
            try:
                if ' - ' in parts[3]:
                    start_time, end_time = parts[3].split(' - ')
                elif ' 至 ' in parts[3]:
                    start_time, end_time = parts[3].split(' 至 ')
                else:
                    raise ValueError("Invalid time range format")

                start_datetime = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
                end_datetime = datetime.strptime(end_time, '%Y-%m-%d %H:%M')

                # 计算每一天的销假时间段
                current_datetime = start_datetime
                while current_datetime.date() <= end_datetime.date():
                    date_str = current_datetime.strftime('%Y-%m-%d')
                    if leave_type == '年假' and date_str in annual_leave:
                        annual_leave[date_str] = [(s, e) for s, e in annual_leave[date_str] if not (s == start_datetime.strftime('%H:%M') and e == end_datetime.strftime('%H:%M'))]
                    elif leave_type == '事假' and date_str in personal_leave:
                        personal_leave[date_str] = [(s, e) for s, e in personal_leave[date_str] if not (s == start_datetime.strftime('%H:%M') and e == end_datetime.strftime('%H:%M'))]

                    current_datetime += timedelta(days=1)
            except ValueError as e:
                print(f"Error parsing time range in record: {record}")
                print(f"Exception: {e}")

        elif leave_type == '延时工时扣减申请':
            auth_key = record['AUTHKEY']
            print(f"正在获取延时工时扣减数据: {auth_key}")
            deduction_data = get_delay_deduction_data(auth_key, user_cookie)
            for form in deduction_data['formList']:
                begin_time = form['formData']['CARDBEGINTIME']
                end_time = form['formData']['CARDENDTIME']
                start_date = begin_time.split('T')[0]  # 提取开始日期
                if start_date not in delay_deduction:
                    delay_deduction[start_date] = []
                delay_deduction[start_date].append((begin_time.split('T')[1], end_time.split('T')[1]))

    return annual_leave, personal_leave, delay_deduction  # 返回年假、事假和延时工时扣减的字典

def parse_attendance_data(attendance_json: str) -> Tuple[Dict[str, List[int]], int, int]:
    """
    解析个人考勤信息的JSON数据，提取每日的迟到分钟数、当月累计的迟到次数和当月累计的迟到分钟数。

    参数：
        - attendance_json：个人考勤信息的JSON数据。

    返回值：
        - daily_late_minutes：每日的迟到分钟数字典，键为日期，值为迟到分钟数列表。
        - total_late_count：当月累计的迟到次数。
        - total_late_minutes：当月累计的迟到分钟数。
    """
    # 解析JSON数据
    # 如果传入的是列表，直接使用；如果是字符串，解析为列表
    if isinstance(attendance_json, str):
        attendance_data = json.loads(attendance_json)
    else:
        attendance_data = attendance_json
    
    # 初始化结果变量
    daily_late_minutes = {}
    total_late_count = None
    total_late_minutes = None
    
    for record in attendance_data:
        # 提取日期和每日的迟到分钟数
        date_str = record.get("TERM", "")
        late_minutes_str = record.get("LTRM_1", "0")
        late_minutes = int(late_minutes_str) if late_minutes_str.isdigit() else 0
        
        if date_str:
            if date_str not in daily_late_minutes:
                daily_late_minutes[date_str] = []
            daily_late_minutes[date_str].append(late_minutes)
        
        # 提取当月累计的迟到次数和迟到分钟数（只需要提取一次）
        if total_late_count is None:
            total_late_count = int(record.get("LATE", 0))
        if total_late_minutes is None:
            total_late_minutes = int(record.get("LATEMIN", 0))

    return daily_late_minutes, total_late_count, total_late_minutes

def count_weekends(year: int, month: int, holidays: list, workdays: set) -> int:
    """
    计算指定年份和月份中的周末天数（不包括节假日和工作日）。

    参数:
        year (int): 年份。
        month (int): 月份。
        holidays (list): 节假日列表，包含日期的字符串，格式为 'YYYY-MM-DD'。
        workdays (set): 工作日集合，包含日期的字符串，格式为 'YYYY-MM-DD'。

    返回值:
        int: 指定月份中的周末天数（不包括节假日和工作日）。
    """
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    weekends = 0
    current_day = first_day
    while current_day <= last_day:
        cur = str(current_day.year) + '-' + str(current_day.month).zfill(2) + '-' + str(current_day.day).zfill(2)
        if current_day.weekday() in (5, 6) and cur not in holidays and cur not in workdays:
            weekends += 1
        current_day += timedelta(days=1)
    return weekends

def pay_rate_cal(day_type: str) -> str:
    """
    计算加班费率。

    参数:
        day_type (str): 日期类型，可以是 "工作日", "周末", "节假日(周末)" 或 "节假日"。

    返回值:
        str: 对应日期类型的加班费率。
    """
    # 工作日加班费20块/小时,周末30,节假日60
    return 20 if day_type == "工作日" else 30 if day_type == "周末" or day_type == "节假日(周末)" else 60 if day_type == "节假日" else 0

def overtime_cal(first_check_time: str, last_check_time: str, day_type: str) -> str:
    """
    计算加班时长。

    参数:
        first_check_time (str): 第一次打卡时间，格式为 'HH:MM:SS'。
        last_check_time (str): 最后一次打卡时间，格式为 'HH:MM:SS'。
        day_type (str): 日期类型，可以是 "工作日", "周末", "节假日(周末)" 或 "节假日"。

    返回值:
        str: 加班时长（小时）。
    """
    # 只要异地打卡就不算加班,即使是节假日
    if last_check_time[-6:] == '(异地打卡)':
        return 0
    if day_type == '工作日':
        ret = (datetime.strptime(last_check_time, '%H:%M:%S') - datetime.strptime('19:00:00', '%H:%M:%S')).total_seconds()
        return ret / 3600 if ret > 0 else 0
    else:
        ret = (datetime.strptime(last_check_time, '%H:%M:%S') - datetime.strptime(first_check_time, '%H:%M:%S')).total_seconds()
        return ret / 3600 if ret > 0 else 0

def overtime_pay_cal(overtime: str, rate: str) -> str:
    """
    计算加班薪资。

    参数:
        overtime (str): 加班时长（小时）。
        rate (str): 加班费率。

    返回值:
        str: 加班薪资。
    """
    # 两数相乘
    return str(float(overtime) * float(rate))

def allowance_cal(overtime: str, day_type: str) -> str:
    """
    计算餐补。

    参数:
        overtime (str): 加班时长（小时）。
        day_type (str): 日期类型，可以是 "工作日", "周末", "节假日(周末)" 或 "节假日"。

    返回值:
        str: 餐补金额。
    """
    # 工作日加班超过1小时给20,周末和节假日超过4小时给20
    if day_type == '工作日':
        return 20 if float(overtime) >= 1.0 else 0
    else:
        return 20 if float(overtime) >= 4.0 else 0

def income_cal(overtime_pay: str, allowance: str) -> str:
    """
    计算总收入。

    参数:
        overtime_pay (str): 加班薪资。
        allowance (str): 餐补金额。

    返回值:
        str: 总收入。
    """
    # 两数相加
    return float(overtime_pay) + float(allowance)

def late_time_cal(first_check_time: str, day_type: str, late_minutes: Optional[int] = None) -> str:
    """
    计算迟到时间。

    参数:
        first_check_time (str): 第一次打卡时间，格式为 'HH:MM:SS'。
        day_type (str): 日期类型，可以是 "工作日", "周末", "节假日(周末)" 或 "节假日"。
        late_minutes (Optional[int]): 迟到分钟数。如果未提供，则根据 first_check_time 计算。

    返回值:
        str: 迟到时间（分钟）。
    """
    # 只要异地打卡就不算迟到
    if first_check_time[-6:] == '(异地打卡)' or day_type != '工作日':
        return "0"
    
    if late_minutes is None:
        ret = (datetime.strptime(first_check_time, '%H:%M:%S') - datetime.strptime('09:00:00', '%H:%M:%S')).total_seconds() / 60
    else:
        ret = late_minutes
    
    return str(ret) if ret > 0 else "0"

def summarize(result: list, workdays: set, holidays: list, total_late_count: int, total_late_minutes: int) -> list:
    """
    汇总统计结果。

    参数:
        result (list): 打卡记录的统计结果。
        workdays (set): 工作日集合。
        holidays (list): 节假日列表。
        total_late_count (int): 当月累计的迟到次数。
        total_late_minutes (int): 当月累计的迟到分钟数。

    返回值:
        list: 汇总统计结果。
    """
    day_of_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    year = int(result[0][0].split('-')[0])
    month = int(result[0][0].split('-')[1])
    total_overtime_pay = 0.0
    total_meal_allowance = 0.0
    total_workday_overtime_pay = 0.0
    total_weekend_overtime_pay = 0.0
    total_holiday_overtime_pay = 0.0
    total_income = 0.0
    total_workday_hours = 0.0
    total_weekend_hours = 0.0
    total_holiday_hours = 0.0
    required_workdays = day_of_month[month - 1] - len(holidays) - count_weekends(year, month, holidays, workdays)
    actual_workdays = 0.0
    total_personal_leave_hours = 0.0

    # 先计算事假的小时数
    for i in result:
        total_personal_leave_hours += (float(i[12]))
    
    personal_leave_remain_hours = total_personal_leave_hours
    for i in result:
        total_overtime_pay += float(i[6])
        total_meal_allowance += float(i[7])
        total_workday_overtime_pay += float(i[6]) if i[3] == '工作日' else 0.0
        total_weekend_overtime_pay += float(i[6]) if i[3] == '周末' else 0.0
        total_holiday_overtime_pay += float(i[6]) if i[3] == '节假日' else 0.0
        total_income += float(i[8])
        total_workday_hours += float(i[5]) if i[3] == '工作日' else 0.0
        total_weekend_hours += float(i[5]) if i[3] == '周末' else 0.0
        total_holiday_hours += float(i[5]) if i[3] == '节假日' else 0.0
        actual_workdays += 1 if i[3] == '工作日' else 0
        
    # 计算实际扣减后的加班费
    # 事假可以用加班抵扣，优先抵扣工作日加班
    actual_workday_hours = total_workday_hours - personal_leave_remain_hours
    if actual_workday_hours < 0:
        actual_workday_hours = 0
        personal_leave_remain_hours -= total_workday_hours
    else:
        personal_leave_remain_hours = 0
    actual_weekend_hours = total_weekend_hours - personal_leave_remain_hours
    if actual_weekend_hours < 0:
        actual_weekend_hours = 0
        personal_leave_remain_hours -= total_weekend_hours
    else:
        personal_leave_remain_hours = 0
    actual_holiday_hours = total_holiday_hours - personal_leave_remain_hours
    if actual_holiday_hours < 0:
        actual_holiday_hours = 0
        personal_leave_remain_hours -= total_holiday_hours
    else:
        personal_leave_remain_hours = 0

    # 处理迟到时间的扣减
    late_minutes_remain = total_late_minutes
    if late_minutes_remain > 0:
        for i in result:
            if late_minutes_remain <= 0:
                break
            if i[3] == '工作日':
                if 1 <= int(i[1].split(':')[1]) <= 30:
                    late_minutes_remain -= 60 + int(i[1].split(':')[1])
                elif 31 <= int(i[1].split(':')[1]) <= 60:
                    late_minutes_remain -= 120 + int(i[1].split(':')[1])
                elif int(i[1].split(':')[1]) > 60:
                    late_minutes_remain -= 480
            elif i[3] == '周末':
                if 1 <= int(i[1].split(':')[1]) <= 30:
                    late_minutes_remain -= 60 + int(i[1].split(':')[1])
                elif 31 <= int(i[1].split(':')[1]) <= 60:
                    late_minutes_remain -= 120 + int(i[1].split(':')[1])
                elif int(i[1].split(':')[1]) > 60:
                    late_minutes_remain -= 480
            elif i[3] == '节假日':
                if 1 <= int(i[1].split(':')[1]) <= 30:
                    late_minutes_remain -= 60 + int(i[1].split(':')[1])
                elif 31 <= int(i[1].split(':')[1]) <= 60:
                    late_minutes_remain -= 120 + int(i[1].split(':')[1])
                elif int(i[1].split(':')[1]) > 60:
                    late_minutes_remain -= 480

    actual_workday_overtime_pay = actual_workday_hours * 20
    actual_weekend_overtime_pay = actual_weekend_hours * 30
    actual_holiday_overtime_pay = actual_holiday_hours * 60
    actual_overtime_pay = actual_workday_overtime_pay + actual_weekend_overtime_pay + actual_holiday_overtime_pay
    actual_total_income = actual_overtime_pay + total_meal_allowance

    # 获取最晚打卡日期
    latest_date = max(i[0] for i in result)

    # 获取昨天的日期
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # 选择最晚打卡日期或昨天的日期
    cutoff_date = latest_date if latest_date < yesterday else yesterday

    # 动态生成表格
    table = [
        ["总加班薪资", f"{total_overtime_pay:.2f} 元"],
        ["实际加班薪资", f"{actual_overtime_pay:.2f} 元"],
        ["总餐补", f"{total_meal_allowance:.2f} 元"],
        ["总工作日加班收入", f"{total_workday_overtime_pay:.2f} 元"],
        ["总周末加班收入", f"{total_weekend_overtime_pay:.2f} 元"],
        ["总节假日加班收入", f"{total_holiday_overtime_pay:.2f} 元"],
        ["总收入", f"{total_income:.2f} 元"],
        ["扣减后预计工作日加班收入", f"{actual_workday_overtime_pay:.2f} 元"],
        ["扣减后预计周末加班收入", f"{actual_weekend_overtime_pay:.2f} 元"],
        ["扣减后预计节假日加班收入", f"{actual_holiday_overtime_pay:.2f} 元"],
        ["扣减后预计总加班收入", f"{actual_overtime_pay:.2f} 元"],
        ["扣减后预计总收入", f"{actual_total_income:.2f} 元"],
        ["总工作日加班时长", f"{total_workday_hours:.2f} 小时"],
        ["总周末加班时长", f"{total_weekend_hours:.2f} 小时"],
        ["总节假日加班时长", f"{total_holiday_hours:.2f} 小时"],
        ["总加班时长", f"{total_workday_hours + total_weekend_hours + total_holiday_hours:.2f} 小时"],
        ["扣减后预计工作日加班时长", f"{actual_workday_hours:.2f} 小时"],
        ["扣减后预计周末加班时长", f"{actual_weekend_hours:.2f} 小时"],
        ["扣减后预计节假日加班时长", f"{actual_holiday_hours:.2f} 小时"],
        ["扣减后预计总加班时长", f"{actual_workday_hours + actual_weekend_hours + actual_holiday_hours:.2f} 小时"],
        [f"截止到{cutoff_date}的总迟到次数", f"{total_late_count} 次"],
        [f"截止到{cutoff_date}的总迟到分钟数", f"{total_late_minutes} 分钟"],
        ["应出勤天数", f"{required_workdays} 天"],
        ["实际出勤天数", f"{actual_workdays} 天"]
    ]
    print(tabulate(table, headers=["汇总项目", "信息"], tablefmt="grid"))
    if total_late_minutes >= 30:
        print("小碧崽治这么喜欢迟到，有你好果汁吃！")

    return table

# 主程序
if __name__ == '__main__':
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(description='参数配置，是否使用本地数据，是否清除或者删除配置文件，是否指定浏览器')

    # 添加命令行参数
    parser.add_argument('--local', action='store_true', help='使用本地数据')
    parser.add_argument('--delete_sensitive_files', action='store_true', help='删除敏感文件')
    parser.add_argument('--clean-run', action='store_true', help='清除所有配置并重新运行')
    parser.add_argument('--broswer', choices=['chrome', 'edge', 'auto'], default='auto', help='指定使用的浏览器 (chrome, edge 或 auto), Safari浏览器不可用, 后续也不会添加Safari支持')

    args = parser.parse_args()

    if args.delete_sensitive_files:
        if os.path.exists(COOKIES_FILE):
            os.remove(COOKIES_FILE)
            print("Cookie文件已删除")
        else:
            print("Cookie文件不存在，干净又卫生！")
        if os.path.exists(OUTPUT_PATH):
            for filename in os.listdir(OUTPUT_PATH):
                file_path = os.path.join(OUTPUT_PATH, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"删除文件 {file_path} 时出错: {e}")
            print("报表输出目录中的所有文件已删除")
        else:
            print("报表输出目录不存在，干净又卫生！")
        exit()
    if args.clean_run:
        if os.path.exists(COOKIES_FILE):
            os.remove(COOKIES_FILE)
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        print("Cookie文件和配置文件已删除")
    if args.local:
        if os.path.exists(LOCAL_DATA_PATH + 'data.json'):
            with open(LOCAL_DATA_PATH + 'data.json', 'r', encoding='utf-8') as file:
                clock_in_data = json.load(file)
            print("使用本地数据，请注意节假日信息年份")
            holidays = Dict()
            workdays = Set()
            if os.path.exists(LOCAL_DATA_PATH + 'holidays.json'):
                with open(LOCAL_DATA_PATH + 'holidays.json', 'r', encoding='utf-8') as file:
                    info = json.load(file)
                holidays, workdays = get_holiday_data_from_local(clock_in_data, info)
            else:
                print(f"未找到本地信息，正在获取文件对应的节假日信息，请稍后...")
                holidays, workdays = get_holiday_data_online(clock_in_data)
            result = []			    # 这玩意存结果,列表里边是元组,元组可通过下标访问(python限定)
            group_by_date = {}	    # 按日期统计打卡时间
            overtime_income = 0.0   # 加班费
            for item in clock_in_data:
                group_by_date.setdefault(item['SHIFTTERM'], []).append(item['CARDTIME'][11::])		# 过滤掉打卡时间里的年月日
            for i in group_by_date:
                sorted(group_by_date[i], key=lambda time: datetime.strptime(time[:8], '%H:%M:%S'))	# 排序,时间早的在前面
                date = i																# 日期
                first_check_time = group_by_date[i][0]									# 最早的打卡时间
                last_check_time = group_by_date[i][-1]									# 最晚的打卡时间
                day_type = get_day_type(date, holidays, workdays)						# 今天啥日子
                rate = pay_rate_cal(day_type)											# 加班一小时该给多少钱
                overtime = overtime_cal(first_check_time, last_check_time, day_type)	# 加了多久班(单位小时)
                overtime_pay = overtime_pay_cal(overtime, rate)							# 加班费多少
                overtime_income += float(overtime_pay)									# 总加班费
                allowance = allowance_cal(overtime, day_type)							# 有没有食补
                total_income = income_cal(overtime_pay, allowance)						# 一天的总收入
                late_minutes = late_time_cal(first_check_time, day_type)				# 迟到了多久
                result.append((date, first_check_time[:8], last_check_time[:8], day_type, rate, overtime, overtime_pay, allowance, total_income, late_minutes))
            # 评价信息
            rank = ''
            if overtime_income < 300:
                rank = '李在赣神魔？'
            elif 300 <= overtime_income < 500:
                rank = '不太行'
            elif 500 <= overtime_income < 1000:
                rank = '一般，建议多加点 冲1000'
            elif 1000 <= overtime_income <= 1500:
                rank = '牛逼'
            elif 1500 <= overtime_income < 2000:
                rank = '逆天'
            elif overtime_income >= 2000:
                rank = f'你是懂加班的，白加了 {overtime_pay - 2000} 元'
            current_year = datetime.now().year
            file_name = OUTPUT_PATH + '本地数据加班情况分析报表.csv'
            summarize(result, workdays, holidays)
            print(f"\n**********************\n义眼丁真，鉴定您的级别为：\n {rank}\n**********************\n")
            print(f"正在保存数据到 {file_name}...")

            # 保存报表
            with open(file_name, 'w', newline='', encoding='utf-8-sig') as csvfile:    
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(["日期", "最早打卡时间", "最晚打卡时间", "本日性质", "加班时薪", "加班时长", "加班薪资", "延时餐补", "总收入", "迟到分钟数"])
                csvwriter.writerows(result)
            exit()
        else:
            print("本地数据文件不存在，下面将进行在线获取")

    # 获取用户输入的年月
    target_year = input("请输入年份，不输入默认为当年: ")
    if target_year.isdigit() and 2010 <= int(target_year) <= datetime.now().year:
        target_year = int(target_year)
    else:
        target_year = datetime.now().year

    target_month = input("请输入月份，不输入默认为当月: ")
    if target_month.isdigit() and 1 <= int(target_month) <= 12:
        target_month = int(target_month)
    else:
        target_month = datetime.now().month

    print(f"正在查询{target_year}年{target_month}月的加班情况，请稍后...")

    # 读取配置
    clock_in_api_endpoint = get_clock_in_api_endpoint_from_config()
    process_application_api_endpoint = get_process_application_api_endpoint_from_config()
    cookie = get_cookie()

    # 如果配置文件不存在或者配置文件中的接口地址为空，则需要重新获取
    if not cookie:
        print("未找到Cookie，正在启动浏览器以获取Cookie...")
        cookie = fetch_cookie_via_browser(args.broswer)
        if cookie:
            save_cookie(cookie)
        else:
            print("Cookie获取失败，请重试")
            exit()
    
    # 如果配置文件中的打卡数据接口为空，则需要重新获取
    if not clock_in_api_endpoint:
        print("未找到打卡数据接口，正在获取...")
        clock_in_api_endpoint = get_clock_in_api_endpoint_online(cookie)
        save_clock_in_api_endpoint_to_config(clock_in_api_endpoint)
    
    # 如果配置文件中的流程申请数据接口为空，则需要重新获取
    if not process_application_api_endpoint:
        print("未找到流程申请数据接口，正在获取...")
        process_application_api_endpoint = get_process_application_api_endpoint_online(cookie)
        save_process_application_api_endpoint_to_config(process_application_api_endpoint)

    # 获取打卡和流程申请数据
    clock_in_data = get_clock_in_data(clock_in_api_endpoint, cookie, target_month, target_year)
    process_application_data = get_process_application_data(process_application_api_endpoint, cookie)
    attendance_data = get_attendance_data(clock_in_api_endpoint, cookie, target_month, target_year)

    # 检查返回的 JSON 数据中是否包含 'expired' 或 'No access' 字段
    def check_and_refresh_data(data, fetch_function, *args):
        if 'expired' in data or 'No access' in data:
            print("Cookie已过期或接口API已失效，正在重新获取...")
            cookie = fetch_cookie_via_browser(args.broswer)
            if cookie:
                save_cookie(cookie)
                return fetch_function(*args)
            else:
                print("Cookie获取失败，请重试")
                exit()
        return data

    clock_in_data = check_and_refresh_data(clock_in_data, get_clock_in_data, clock_in_api_endpoint, cookie, target_month, target_year)
    process_application_data = check_and_refresh_data(process_application_data, get_process_application_data, process_application_api_endpoint, cookie)
    attendance_data = check_and_refresh_data(attendance_data, get_attendance_data, clock_in_api_endpoint, cookie, target_month, target_year)

    # 获取并计算加班信息
    holidays, workdays = get_holiday_data_online(clock_in_data)
    # 从流程申请中获取年假、事假以及延时工时扣减数据
    annual_leave, personal_leave, delay_deduction = parse_process_application_data(process_application_data, cookie)
    # 从出勤数据中获取迟到信息
    daily_late_minutes, total_late_count, total_late_minutes = parse_attendance_data(attendance_data)
    result = []			        # 这玩意存结果,列表里边是元组,元组可通过下标访问(python限定)
    group_by_date = {}	        # 按日期统计打卡时间
    late_minutes = 0.0          # 迟到分钟数
    overtime_income = 0.0       # 加班费
    annual_leave_total = 0.0    # 年假总时间
    personal_leave_total = 0.0  # 事假总时间
    for item in clock_in_data:
        group_by_date.setdefault(item['SHIFTTERM'], []).append(item['CARDTIME'][11::])		# 过滤掉打卡时间里的年月日
    for i in group_by_date:
        sorted(group_by_date[i], key=lambda time: datetime.strptime(time[:8], '%H:%M:%S'))	# 排序,时间早的在前面
        date = i																# 日期
        first_check_time = group_by_date[i][0]									# 最早的打卡时间
        last_check_time = group_by_date[i][-1]									# 最晚的打卡时间
        day_type = get_day_type(date, holidays, workdays)						# 今天啥日子
        rate = pay_rate_cal(day_type)											# 加班一小时该给多少钱
        overtime = overtime_cal(first_check_time, last_check_time, day_type)	# 加了多久班(单位小时)
        # 计算延时扣减总时间
        delay_deduction_time = 0.0
        if i in delay_deduction:
            for start_time, end_time in delay_deduction[i]:
                start_time = datetime.strptime(start_time, '%H:%M:%S')
                end_time = datetime.strptime(end_time, '%H:%M:%S')
                delay_deduction_time += (end_time - start_time).total_seconds() / 3600
            overtime -= delay_deduction_time
        overtime_pay = overtime_pay_cal(overtime, rate)							# 加班费多少
        overtime_income += float(overtime_pay)									# 总加班费
        allowance = allowance_cal(overtime, day_type)							# 有没有食补
        total_income = income_cal(overtime_pay, allowance)						# 一天的总收入
        # 计算事假和年假的时间
        annual_leave_time = 0.0
        personal_leave_time = 0.0
        if i in annual_leave:
            # 获取 annual_leave 中的第一个时间
            leave_start_time_str = annual_leave[i][0][0]
            leave_start_time = datetime.strptime(leave_start_time_str, '%H:%M').time()
            # 计算当天年假时间，第二个时间和第一个时间相减
            annual_leave_time = (datetime.strptime(annual_leave[i][0][1], '%H:%M') - datetime.strptime(leave_start_time_str, '%H:%M')).total_seconds() / 3600

            # 比较 first_check_time 和 leave_start_time，取最早值
            first_check_time = min(first_check_time, leave_start_time)
        if i in personal_leave:
            # 获取 personal_leave 中的第一个时间
            leave_start_time_str = personal_leave[i][0][0]
            leave_start_time = datetime.strptime(leave_start_time_str, '%H:%M').time()
            # 计算当天事假时间，第二个时间和第一个时间相减
            personal_leave_time = (datetime.strptime(personal_leave[i][0][1], '%H:%M') - datetime.strptime(leave_start_time_str, '%H:%M')).total_seconds() / 3600
        
            # 比较 first_check_time 和 leave_start_time，取最早值
            first_check_time = min(first_check_time, leave_start_time)
        late_minutes = late_time_cal(first_check_time, day_type, sum(daily_late_minutes[i]) if i in daily_late_minutes else 0 )				# 迟到了多久
        result.append((date, first_check_time[:8], last_check_time[:8], day_type, rate, overtime, overtime_pay, allowance, total_income, late_minutes, delay_deduction_time, annual_leave_time, personal_leave_time))

    # 评价信息
    rank = ''
    if overtime_income < 300:
        rank = '李在赣神魔？'
    elif 300 <= overtime_income < 500:
        rank = '不太行'
    elif 500 <= overtime_income < 1000:
        rank = '一般，建议多加点 冲1000'
    elif 1000 <= overtime_income <= 1500:
        rank = '牛逼'
    elif 1500 <= overtime_income < 2000:
        rank = '逆天'
    elif overtime_income >= 2000:
        rank = f'你是懂加班的，白加了 {overtime_pay - 2000} 元'
    print(f"\n**********************\n义眼丁真，鉴定您的级别为：\n {rank}\n**********************\n")
    
    # 汇总统计结果
    summarize_data = summarize(result, workdays, holidays, total_late_count, total_late_minutes)

    # 生成报表文件名
    file_name = f"{OUTPUT_PATH}{target_year}年{target_month:02d}月加班情况详细分析报表.csv"
    print(f"正在保存数据到 {file_name}...")

    # 保存报表
    ensure_directory_exists(OUTPUT_PATH)
    with open(file_name, 'w', newline='', encoding='utf-8-sig') as csvfile:    
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["日期", "最早打卡时间", "最晚打卡时间", "本日性质", "加班时薪", "加班时长", "加班薪资", "延时餐补", "总收入", "迟到分钟数", "延时工时扣减时间", "年假时间", "事假时间"])
        csvwriter.writerows(result)
        csvwriter.writerows([[], [], ["汇总项目", "信息"]])  # 写入两个空行和汇总项目表头
        csvwriter.writerows(summarize_data)