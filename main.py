from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from time import sleep, time
from random import uniform, randint
import requests
import bs4
import re
import logging
import configparser
import csv
from playsound import playsound
import os
import datetime
from unidecode import unidecode

PHONE_SELECTION_URL = 'https://sms-receive.net/'
PHONE_BASE_URL = 'https://sms-receive.net/'

CURRENT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

FORMAT = '<%(asctime)-15s>[%(levelname)s]： %(message)s'
logging.basicConfig(format=FORMAT, filename=os.path.join(CURRENT_DIRECTORY, 'history.log'), filemode='a', encoding='utf-8', level=logging.INFO)

def get_soup(url):
    response = requests.get(url)

    if response.ok:
        soup = bs4.BeautifulSoup(response.text, "lxml")
    else:
        logging.error(response)
        return None

    return soup


def get_latest_code(driver):
    res = []
    driver.find_element_by_css_selector('body > div.uk-margin-large-left.uk-margin-large-right > div > div > div > div.uk-alert.uk-text-center > div:nth-child(4) > button').click()
    wait()
    MAXIMUM_LENGTH = 100
    for i in range(MAXIMUM_LENGTH):
        try:
            cell = driver.find_element_by_css_selector(
                '#messages > tbody > tr:nth-child(' + str(i + 1) + ') > td:nth-child(1)')
            if cell.text == 'SEAPminhap':
                msg = driver.find_element_by_css_selector(
                    '#messages > tbody > tr:nth-child(' + str(i + 1) + ') > td:nth-child(2)')
                t = driver.find_element_by_css_selector(
                    '#messages > tbody > tr:nth-child(' + str(i + 1) + ') > td:nth-child(3)')
                if 'minute' in t.text:
                    break
                code = re.findall(r'\d+', msg.text)[0]
                res.append(code)

            driver.execute_script("arguments[0].scrollIntoView();", cell)
        except Exception as e:
           print(e)

    return res


def wait():
    rand = uniform(1, 2)
    sleep(rand)


def exists(driver, selector):
    try:
        driver.find_element_by_css_selector(selector)
    except NoSuchElementException:
        return False
    return True


def get_available_phone():
    # Check if the phone has exceed limit
    cache_file = os.path.join(CURRENT_DIRECTORY, 'cache.txt')

    today = str(datetime.datetime.now().date())

    last_date = ''

    try:
        with open(cache_file, 'r') as file:
            last_date = file.read().strip()
    except:
        pass

    if today == last_date:
        return None, config['DEFAULT']['PHONE_NUMBER']

    soup = get_soup(PHONE_SELECTION_URL)
    link = soup.find('a', {'title': re.compile('^Spain')})['href']
    phone_link = PHONE_BASE_URL + link

    phone_number = link.split('-')[0][-9:]

    return phone_link, phone_number


def break_captcha(driver, API_KEY, site_key, url):
    s = requests.Session()
    # here we post site key to 2captcha to get captcha ID (and we parse it here too)
    captcha_id = s.post(
        "http://2captcha.com/in.php?key={}&method=userrecaptcha&googlekey={}&pageurl={}".format(API_KEY, site_key,
                                                                                                url)).text.split(
        '|')[1]
    # then we parse gresponse from 2captcha response
    recaptcha_answer = s.get("http://2captcha.com/res.php?key={}&action=get&id={}".format(API_KEY, captcha_id)).text
    logging.info("solving ref captcha...")

    while 'CAPCHA_NOT_READY' in recaptcha_answer:
        sleep(5)
        recaptcha_answer = s.get(
            "http://2captcha.com/res.php?key={}&action=get&id={}".format(API_KEY, captcha_id)).text
        print(recaptcha_answer)
    recaptcha_answer = recaptcha_answer.split('|')[1]

    driver.execute_script(
        "document.querySelector('#g-recaptcha-response').innerHTML = '{}'".format(recaptcha_answer))


def make_appointment(client, config):
    logging.info("Load User: " + client['nie'])

    API_KEY = config['DEFAULT']['API_KEY']
    phone_link, phone_number = get_available_phone()
    email = config['DEFAULT']['EMAIL']
    driver_path = config['DEFAULT']['DRIVER']

    logging.info("Get Available Phone: " + phone_number)

    city = client['city']
    procedure = client['request']  # 4010 Huella 4036 recogida
    nie = client['nie']
    name = client['name']
    country = client['nationality']
    expire_date = client['expire_date']
    office_filter = client['office_filter']

    driver = webdriver.Chrome(executable_path=driver_path)
    driver.get("https://sede.administracionespublicas.gob.es/icpplustie/citar?locale=es")

    # Step 1 : Find city
    select = Select(driver.find_element_by_css_selector("select#form"))
    select.select_by_visible_text(city)

    wait()
    # Then click
    acceptElement = driver.find_element_by_xpath("//*[@id='btnAceptar']")
    driver.execute_script("arguments[0].click();", acceptElement)

    wait()
    # Step 2 : Find tramite
    try:
        select = Select(driver.find_element_by_css_selector("#tramiteGrupo\[1\]"))
        select.select_by_value(procedure)
    except NoSuchElementException:
        select = Select(driver.find_element_by_css_selector("#tramiteGrupo\[0\]"))
        select.select_by_value(procedure)

    wait()
    acceptElement = driver.find_element_by_xpath("//*[@id='btnAceptar']")
    driver.execute_script("arguments[0].click();", acceptElement)

    wait()
    enterElem = driver.find_element_by_xpath("//*[@id='btnEntrar']")
    driver.execute_script("arguments[0].click();", enterElem)

    wait()
    # Step 3: Fill the form
    driver.find_element_by_css_selector("#txtIdCitado").send_keys(nie)
    wait()
    driver.find_element_by_css_selector("#txtDesCitado").send_keys(name)
    wait()

    if procedure == '4010':
        driver.find_element_by_css_selector("#txtFecha").send_keys(expire_date)
        wait()
        select = Select(driver.find_element_by_css_selector("#txtPaisNac"))
        select.select_by_visible_text(country)

    wait()

    url = driver.current_url
    # Check if exceed time limit
    while exists(driver, '#citadoForm') and exists(driver, '#html_element'):
        site_key = driver.find_element_by_css_selector('#html_element').get_attribute('data-sitekey')
        break_captcha(driver, API_KEY, site_key, url)
        wait()
        driver.execute_script("document.getElementById('citadoForm').submit();")

    while exists(driver, '#btnEnviar'):
        wait()
        driver.find_element_by_css_selector('#btnEnviar').click()
        wait()
        while exists(driver, '#citadoForm') and exists(driver, '#html_element'):
            site_key = driver.find_element_by_css_selector('#html_element').get_attribute('data-sitekey')
            break_captcha(driver, API_KEY, site_key, url)
            wait()
            driver.execute_script("document.getElementById('citadoForm').submit();")

    wait()
    # Check if has
    try:
        msg = driver.find_element_by_css_selector(
            '#mainWindow > div > div > section > div.mf-main--content.ac-custom-content > form > div.mf-main--content.ac-custom-content > p')
        logging.warning(msg.text.split('\n')[0])
        driver.quit()
        return None
    except NoSuchElementException:
        pass

    # Select Office
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "idSede")))
    office_select = driver.find_element_by_css_selector('#idSede')
    options = [(x.get_attribute('value'), unidecode(x.text.lower())) for x in office_select.find_elements_by_tag_name("option")]
    options = sorted(options, key=lambda x: x[1])
    print(options)
    logging.info(str(options))

    #options = [x for x in options if x[0] != '14'] # remove mallorca

    valid_code = options[0][0]

    if office_filter != '':
        cond = office_filter.split()
        candidates = [x[0] for x in options if x[0] in cond]
        if len(candidates) > 0:
            valid_code = candidates[0]
        else:
            logging.warning("Selected Office is not available")
            driver.quit()
            return None

    Select(office_select).select_by_value(valid_code)

    driver.find_element_by_css_selector('#btnSiguiente').click()
    wait()

    logging.info('Filling contact data')

    # Fill my data
    driver.find_element_by_css_selector('#txtTelefonoCitado').send_keys(phone_number)
    wait()
    driver.find_element_by_css_selector('#emailUNO').send_keys(email)
    wait()
    driver.find_element_by_css_selector('#emailDOS').send_keys(email)

    wait()
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    wait()
    driver.find_element_by_css_selector('#btnSiguiente').click()
    try:
        msg = driver.find_element_by_css_selector('#mensajeInfo > p.mf-msg__info > span').text
        #logging.warning(msg)
        logging.warning(msg.split('\n')[0])
        driver.quit()

        if 'máximo de citas diarias por solicitante' in msg:
            cache_file = os.path.join(CURRENT_DIRECTORY, 'cache.txt')
            today = str(datetime.datetime.now().date())
            with open(cache_file, 'w') as file:
                file.write(today)

        return None
    except NoSuchElementException:
        pass

    wait()

    if exists(driver, '#btnSiguiente'):
        time = driver.find_element_by_css_selector('#cita_1').text
        time = re.findall(r' (.*\d)', time)
        date = time[1] # 26/11/2020
        hour = time[2] # 09:50

        if exists(driver, '#cita1'):
            driver.find_element_by_css_selector('#cita1').click()
        wait()

        driver.execute_script('document.procedimientos.submit();')
    else:
        totals_rows = driver.find_elements_by_xpath('//*[@id="VistaMapa_Datatable"]/tbody/tr')
        total_rows_length = len(totals_rows)
        for i in range(total_rows_length):
            site = '//*[@id="VistaMapa_Datatable"]/tbody/tr[' + str(i + 1) + "]/td[3]/span"
            cell = driver.find_element_by_xpath(site)
            if 'LIBRE' in cell.text:
                hueco_id = cell.get_attribute('id').replace('HUECO', '')
                driver.execute_script('document.getElementById("txtIdCita").value=' + hueco_id + ';')
                driver.execute_script('document.procedimientos.submit();')
                break

    wait()
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    wait()
    driver.find_element_by_css_selector('#chkTotal').click()
    driver.find_element_by_css_selector('#enviarCorreo').click()
    logging.info("SMS verification")


    playsound(os.path.join(CURRENT_DIRECTORY, 'sound.mp3'))
    #while True:
    #    sleep(100)


    code_list = []
    while len(code_list) == 0:
        last_tab = len(driver.window_handles)
        driver.execute_script("window.open('{}')".format(phone_link))
        driver.switch_to.window(driver.window_handles[last_tab])
        wait()
        code_list = get_latest_code(driver)

    logging.info("Receive code " + str(code_list))
    driver.switch_to.window(driver.window_handles[0])
    wait()
    while exists(driver, '#btnConfirmar') and len(code_list) > 0:
        code = code_list.pop()
        logging.info("Sending the code " + str(code))
        driver.find_element_by_css_selector('#txtCodigoVerificacion').send_keys(code)
        wait()
        driver.find_element_by_css_selector('#btnConfirmar').click()
        wait()
        wait()
    logging.info("Verification passed")

    res = driver.find_element_by_css_selector('#justificanteFinal').text + " "
    res += driver.find_element_by_css_selector('#mainWindow > div > div > section > div.mf-main--content.ac-custom-content > form > div:nth-child(6) > fieldset > div:nth-child(2) > span.mf-psdinput.mf-input__m.select2-container').text + " "
    res += driver.find_element_by_css_selector('#mainWindow > div > div > section > div.mf-main--content.ac-custom-content > form > div:nth-child(6) > fieldset > div:nth-child(3) > span.mf-psdinput').text + " "
    res += driver.find_element_by_css_selector('#mainWindow > div > div > section > div.mf-main--content.ac-custom-content > form > div:nth-child(6) > fieldset > div:nth-child(4) > span.mf-psdinput').text

    logging.info("Appointment made : " + res)
    driver.quit()

    return res


if __name__ == '__main__':
    logging.info("{0:*^50}".format(" Start "))
    config = configparser.ConfigParser()
    config.read(os.path.join(CURRENT_DIRECTORY, 'config.ini'))

    input_file = os.path.join(CURRENT_DIRECTORY, 'clients.csv')
    logging.info("Load Client File")
    with open(input_file, mode='r') as f:
        reader = csv.DictReader(f)
        clients = [row for row in reader]
    logging.info(str(len(clients)) + " clients detected")

    for i, c in enumerate(clients):
        if c['is_done'] == 'TRUE':
            continue
        #try:
        appointment = make_appointment(c, config)
        if appointment is not None:
            clients[i]['result'] = appointment
            clients[i]['is_done'] = 'TRUE'
            keys = clients[0].keys()
            with open(input_file, 'w', newline='') as output_file:
                dict_writer = csv.DictWriter(output_file, keys)
                dict_writer.writeheader()
                dict_writer.writerows(clients)

        #except Exception as e:
        #    logging.error(e)
    logging.info("{0:*^50}".format(" End "))

